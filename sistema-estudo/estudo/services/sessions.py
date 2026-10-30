"""Sessions use cases; dependencies are supplied by the composition root."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from estudo.errors import DomainError


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
            session = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (session_id,)).fetchone()
            if session is None or session["status"] != "active":
                raise ValueError("Esta sessão não está ativa.")
            linked = con.execute(
                "SELECT 1 FROM lesson_questions WHERE lesson_id=? AND occurrence_id=?",
                (session["lesson_id"], occurrence_id),
            ).fetchone()
            if linked is None:
                raise ValueError("A questão precisa estar vinculada à aula para entrar na sessão.")
        con.execute(
            "INSERT INTO attempts(attempt_id,session_id,stage,occurrence_id,answer,help_used,reference_snapshot,correct,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
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
        con.execute("BEGIN IMMEDIATE")
        session = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (session_id,)).fetchone()
        if session is None:
            raise DomainError("Sessão não encontrada.", 404)
        if session["status"] == "completed":
            return app.session_public(session)
        topic_id = con.execute("SELECT topic_id FROM lessons WHERE lesson_id=?", (session["lesson_id"],)).fetchone()[0]
        for front, back, difficulty in cleaned_cards:
            con.execute(
                "INSERT INTO cards(card_id,topic_id,source_session_id,front,back,difficulty,interval_days,due_date,created_at) VALUES(?,?,?,?,?,?,1,?,?)",
                (app.new_id("card"), topic_id, session_id, front, back, difficulty, first_review_due, app.iso(now)),
            )
        for text in clean_difficulties:
            con.execute(
                "INSERT INTO lesson_difficulties(difficulty_id,lesson_id,session_id,text,created_at) VALUES(?,?,?,?,?)",
                (app.new_id("difficulty"), session["lesson_id"], session_id, text, app.iso(now)),
            )
        con.execute(
            "UPDATE lessons SET completed_at=coalesce(completed_at,?) WHERE lesson_id=?",
            (app.iso(now), session["lesson_id"]),
        )
        con.execute(
            "UPDATE study_sessions SET status='completed',completed_at=?,updated_at=?,current_step=5,deadline_at=NULL,paused_remaining=0 WHERE session_id=?",
            (app.iso(now), app.iso(now), session_id),
        )
        con.commit()
        result = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (session_id,)).fetchone()
    return app.session_public(result)


def review_card(app, card_id: str, body: dict):
    rating = body.get("rating")
    if rating not in ("errei", "dificil", "facil"):
        raise DomainError("Escolha Errei, Difícil ou Fácil.")
    now_local = datetime.now(app.LOCAL_TZ)
    today = now_local.date()
    with app.study_db() as con:
        card = con.execute("SELECT * FROM cards WHERE card_id=? AND active=1", (card_id,)).fetchone()
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
        con.execute("UPDATE cards SET interval_days=?,due_date=? WHERE card_id=?", (after, due, card_id))
        con.execute(
            "INSERT INTO card_reviews(review_id,card_id,rating,interval_before,interval_after,due_after,reviewed_at) VALUES(?,?,?,?,?,?,?)",
            (app.new_id("review"), card_id, rating, before, after, due, reviewed),
        )
        con.commit()
        updated = dict(con.execute("SELECT * FROM cards WHERE card_id=?", (card_id,)).fetchone())
    return {"card": updated, "rating": rating, "interval_before": before, "interval_after": after, "due_date": due}
