"""Sessions use cases; dependencies are supplied by the composition root."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from estudo.errors import DomainError
from estudo.repositories import sessions as store
from estudo.services import selection


def timer_state(app, session: dict) -> dict:
    if session.get("paused_remaining") is not None:
        seconds = max(0, int(session["paused_remaining"]))
        paused = True
    elif session.get("deadline_at"):
        try:
            deadline = datetime.fromisoformat(session["deadline_at"])
            seconds = max(0, int((deadline - app.utc_now()).total_seconds()))
        except (TypeError, ValueError):
            seconds = app.STEP_MINUTES[int(session.get("current_step", 0))] * 60
        paused = False
    else:
        seconds = app.STEP_MINUTES[int(session.get("current_step", 0))] * 60
        paused = False
    return {"remaining_seconds": seconds, "paused": paused, "deadline_at": session.get("deadline_at")}


def session_public(app, session: sqlite3.Row | dict) -> dict:
    d = dict(session)
    d["payload"] = app.json_load(d.get("payload"), {})
    d["timer"] = app.timer_state(d)
    return d


def answer_snapshot(
    app, occurrence_id: str, response: str, stage: str, help_used: bool = False, session_id: str | None = None
) -> dict:
    item = app.content_question(occurrence_id)
    if item is None:
        raise ValueError("Questão não encontrada na base de conteúdo.")
    answer = app.clean_text(response, "resposta", 4000)
    options = {str(a.get("rotulo", "")).strip().upper() for a in item.get("alternatives", [])}
    normalized = answer.strip().upper()
    if options and normalized not in options:
        raise ValueError("Escolha uma alternativa disponível.")
    source = app.associated_snapshot(occurrence_id)
    extraction = item.get("status_extracao")
    auto_grade = (
        item["reference_status"]["correctable"]
        and extraction == "extraido"
        and (source["state"] == "concordante")
        and (source["situation"] == "valido")
        and source["has_definitive"]
        and bool(source["answer"])
    )
    correct = int(normalized == str(source["answer"]).strip().upper()) if auto_grade else None
    public_associated = [
        {
            "answer": source_answer.get("resposta_publicada"),
            "situation": source_answer.get("situacao_item"),
            "nature": source_answer.get("natureza_gabarito"),
            "pages": app.json_load(source_answer.get("paginas_json"), []),
            "document_id": source_answer.get("documento_id"),
            "document_title": source_answer.get("document_title"),
        }
        for source_answer in source["associated"]
    ]
    snap = {
        "reference_answer": source["answer"],
        "situation": source["situation"],
        "state": source["state"],
        "has_definitive": source["has_definitive"],
        "extraction": extraction,
        "auto_graded": bool(auto_grade),
        "associated_answers": public_associated,
        "responded_at": app.iso(app.utc_now()),
    }
    attempt_id = app.new_id("attempt")
    with app.study_db() as con:
        if session_id:
            session = store.session(con, (session_id,))
            if session is None or session["status"] != "active":
                raise ValueError("Esta sessão não está ativa.")
            linked = store.linked_question(con, (session["lesson_id"], occurrence_id))
            if linked is None:
                raise ValueError("A questão precisa estar vinculada à aula para entrar na sessão.")
        store.insert_attempt(
            con,
            (
                attempt_id,
                session_id,
                stage,
                occurrence_id,
                answer,
                int(help_used),
                app.safe_json(snap),
                correct,
                app.iso(app.utc_now()),
            ),
        )
        con.commit()
    return {
        "attempt_id": attempt_id,
        "stage": stage,
        "occurrence_id": occurrence_id,
        "answer": answer,
        "correct": bool(correct) if correct is not None else None,
        "help_used": bool(help_used),
        "snapshot": snap,
        "question": app.question_for_client(app.content_question(occurrence_id, include_answer=True), True),
    }


def complete_session(app, session_id: str, body: dict):
    cards = body.get("cards", [])
    difficulties = body.get("difficulties", [])
    if not isinstance(cards, list) or len(cards) > 100:
        raise DomainError("Lista de cartões inválida.")
    if not isinstance(difficulties, list) or len(difficulties) > 30:
        raise DomainError("Lista de dificuldades inválida.")
    cleaned_cards = []
    for card in cards:
        if not isinstance(card, dict) or not card.get("selected"):
            continue
        front = app.clean_text(card.get("front"), "pergunta do cartão", 1200)
        back = app.clean_text(card.get("back"), "resposta do cartão", 2400)
        difficulty = app.clean_text(card.get("difficulty", ""), "dificuldade", 300, required=False)
        cleaned_cards.append((front, back, difficulty))
    clean_difficulties = [app.clean_text(d, "dificuldade", 500) for d in difficulties]
    now = app.utc_now()
    first_review_due = (datetime.now(app.LOCAL_TZ).date() + timedelta(days=1)).isoformat()
    with app.study_db() as con:
        store.begin_write(con)
        session = store.session(con, (session_id,))
        if session is None:
            raise DomainError("Sessão não encontrada.", 404)
        if session["status"] == "completed":
            return app.session_public(session)
        topic_id = store.lesson_topic(con, (session["lesson_id"],))[0]
        for front, back, difficulty in cleaned_cards:
            store.insert_card(
                con, (app.new_id("card"), topic_id, session_id, front, back, difficulty, first_review_due, app.iso(now))
            )
        for text in clean_difficulties:
            store.insert_difficulty(
                con, (app.new_id("difficulty"), session["lesson_id"], session_id, text, app.iso(now))
            )
        store.complete_lesson(con, (app.iso(now), session["lesson_id"]))
        store.complete_session(con, (app.iso(now), app.iso(now), session_id))
        con.commit()
        result = store.session(con, (session_id,))
    return app.session_public(result)


def review_card(app, card_id: str, body: dict):
    rating = body.get("rating")
    if rating not in ("errei", "dificil", "facil"):
        raise DomainError("Escolha Errei, Difícil ou Fácil.")
    now_local = datetime.now(app.LOCAL_TZ)
    today = now_local.date()
    with app.study_db() as con:
        card = store.active_card(con, (card_id,))
        if card is None:
            raise DomainError("Cartão não encontrado.", 404)
        before = int(card["interval_days"])
        if rating == "errei":
            after = 1
        elif rating == "dificil":
            after = before
        else:
            after = {1: 3, 3: 7, 7: 7}.get(before, 1)
        due = (today + timedelta(days=after)).isoformat()
        reviewed = app.iso(now_local)
        store.update_card(con, (after, due, card_id))
        store.insert_review(con, (app.new_id("review"), card_id, rating, before, after, due, reviewed))
        con.commit()
        updated = dict(store.card(con, (card_id,)))
    return {"card": updated, "rating": rating, "interval_before": before, "interval_after": after, "due_date": due}


def due_cards(app):
    day = datetime.now(app.LOCAL_TZ).date().isoformat()
    with app.study_db() as con:
        cards = [dict(r) for r in store.due_cards(con, (day,))]
    return {"items": cards, "today": day}


def attempt_history(app):
    with app.study_db() as con:
        rows = [dict(r) for r in store.attempt_history(con)]
    for r in rows:
        r["reference_snapshot"] = app.json_load(r["reference_snapshot"], {})
    return {"items": rows}


def start_session(app, lesson_id):
    with app.study_db() as con:
        store.begin_write(con)
        if store.lesson_exists(con, (lesson_id,)) is None:
            raise DomainError("Aula não encontrada.", 404)
        active = store.active_for_lesson(con, (lesson_id,))
        if active:
            return (app.session_public(active), False)
        session_id = app.new_id("session")
        now = app.utc_now()
        deadline = now + timedelta(minutes=app.STEP_MINUTES[0])
        with app.content_db() as content:
            initial_payload = selection.session_pool(con, content, lesson_id)
        previous = store.previous_payload(con, (lesson_id,))
        if previous:
            previous_payload = app.json_load(previous["payload"], {})
            if isinstance(previous_payload, dict) and isinstance(previous_payload.get("boardScene"), dict):
                initial_payload["boardScene"] = previous_payload["boardScene"]
        store.insert_session(
            con, (session_id, lesson_id, app.iso(deadline), app.safe_json(initial_payload), app.iso(now), app.iso(now))
        )
        con.commit()
        row = store.session(con, (session_id,))
    return (app.session_public(row), True)


def change_step(app, session_id, body):
    step = body.get("step")
    if type(step) is not int or not 0 <= step < len(app.STEPS):
        raise DomainError("Etapa inválida.")
    with app.study_db() as con:
        row = store.active_session(con, (session_id,))
        if row is None:
            raise DomainError("Sessão ativa não encontrada.", 404)
        now = app.utc_now()
        store.change_step(
            con, (step, app.iso(now + timedelta(minutes=app.STEP_MINUTES[step])), app.iso(now), session_id)
        )
        con.commit()
        updated = store.session(con, (session_id,))
    return app.session_public(updated)


def toggle_pause(app, session_id):
    with app.study_db() as con:
        row = store.active_session(con, (session_id,))
        if row is None:
            raise DomainError("Sessão ativa não encontrada.", 404)
        if row["paused_remaining"] is None:
            remaining = (
                max(0, int((datetime.fromisoformat(row["deadline_at"]) - app.utc_now()).total_seconds()))
                if row["deadline_at"]
                else 0
            )
            store.pause(con, (remaining, app.iso(app.utc_now()), session_id))
        else:
            remaining = max(0, int(row["paused_remaining"]))
            store.resume(
                con, (app.iso(app.utc_now() + timedelta(seconds=remaining)), app.iso(app.utc_now()), session_id)
            )
        con.commit()
        updated = store.session(con, (session_id,))
    return app.session_public(updated)


def save_state(app, session_id, body):
    payload = body.get("payload")
    if not isinstance(payload, dict):
        raise DomainError("Estado da sessão inválido.")
    encoded = app.safe_json(payload, 20000000)
    now = app.iso(app.utc_now())
    with app.study_db() as con:
        cur = store.save_state(con, (encoded, now, session_id))
        if not cur.rowcount:
            raise DomainError("Sessão ativa não encontrada.", 404)
        con.commit()
        updated = store.session(con, (session_id,))
    return app.session_public(updated)
