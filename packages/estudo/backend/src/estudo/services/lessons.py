"""Lessons use cases; dependencies are supplied by the composition root."""

from __future__ import annotations

from datetime import datetime

from estudo.errors import DomainError
from estudo.repositories import lessons as store
from estudo.repositories import question_links
from estudo.services import plans as roadmap
from estudo.services import profiles


def get_lesson(app, lesson_id: str) -> dict | None:
    with app.study_db() as con:
        row = store.lesson(con, (lesson_id,))
        if row is None:
            return None
        lesson = dict(row)
        lesson["roadmap"] = roadmap.lesson_metadata(con, lesson_id)
        lesson["reference_scene"] = app.json_load(lesson["reference_scene"])
        lesson["occurrence_ids"] = [r[0] for r in store.question_ids(con, (lesson_id,))]
        lesson["materials"] = [dict(r) for r in store.materials(con, (lesson_id,))]
        mappings = question_links.lesson_mappings(con, lesson_id)
    with app.content_db() as con:
        questions = question_links.content_items(con, lesson["occurrence_ids"])
    lesson["questions"] = []
    for q in questions:
        q["mapping"] = mappings.get(q["ocorrencia_id"])
        lesson["questions"].append(app.question_for_client(q))
    for material in lesson["materials"]:
        if material["document_id"]:
            material["open_url"] = f"/api/library/file?document_id={material['document_id']}"
        else:
            material["open_url"] = material["url"]
    return lesson


def bootstrap(app) -> dict:
    with app.study_db() as con:
        plan = roadmap.public_plan(con, datetime.now(app.LOCAL_TZ).date().isoformat())
        if plan:
            plan["question_mapping"] = question_links.summary(con)
        question_counts = question_links.counts(con)
        subjects = []
        for s in store.subjects(con):
            subject = {"id": s["subject_id"], "name": s["name"], "topics": []}
            for t in store.topics(con, (s["subject_id"],)):
                lessons = [dict(lesson) for lesson in store.lessons(con, (t["topic_id"],))]
                for lesson in lessons:
                    lesson["question_count"] = question_counts.get(lesson["id"], 0)
                subject["topics"].append({"id": t["topic_id"], "title": t["title"], "lessons": lessons})
            subjects.append(subject)
        active_sessions = []
        for active in store.active_sessions(con):
            session = dict(active)
            session["payload"] = app.json_load(session["payload"], {})
            session["timer"] = app.timer_state(session)
            active_sessions.append(session)
    totals = {
        "lessons": sum((len(t["lessons"]) for s in subjects for t in s["topics"])),
        "completed": sum(
            (1 for s in subjects for t in s["topics"] for lesson in t["lessons"] if lesson["completed_at"])
        ),
    }
    available = profiles.list_profiles(app.settings.study_db)
    return {
        "subjects": subjects,
        "totals": totals,
        "active_session": active_sessions[0] if active_sessions else None,
        "active_sessions": active_sessions,
        "roadmap": plan,
        "steps": app.STEPS,
        "profiles": available,
        "profile": next((p for p in available if p["id"] == profiles.current.get())),
    }


def add_lesson_material(app, lesson_id: str, body: dict):
    title = app.clean_text(body.get("title"), "nome do material", 180)
    url = body.get("url")
    doc_id = body.get("document_id")
    if bool(url) == bool(doc_id):
        raise ValueError("Adicione um link ou selecione um PDF da biblioteca.")
    if url:
        from urllib.parse import urlparse

        url = app.clean_text(url, "link", 2000)
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Use um endereço HTTP ou HTTPS válido.")
    else:
        doc_id = app.clean_text(doc_id, "PDF", 100)
        with app.content_db() as source:
            doc = store.document(source, (doc_id,))
        if not doc or app.safe_library_file(doc["arquivo_local"]) is None:
            raise ValueError("O PDF não está disponível dentro da biblioteca local.")
    with app.study_db() as con:
        if store.lesson_exists(con, (lesson_id,)) is None:
            raise ValueError("Aula não encontrada.")
        pos = store.next_material_position(con, (lesson_id,))[0]
        material_id = app.new_id("material")
        store.insert_material(con, (material_id, lesson_id, title, url, doc_id, pos, app.iso(app.utc_now())))
        con.commit()
    return app.get_lesson(lesson_id)


def create_topic(app, body):
    subject_name = app.clean_text(body.get("subject"), "disciplina", 100)
    title = app.clean_text(body.get("title"), "tópico", 180)
    with app.study_db() as con:
        subject = store.subject_by_name(con, (subject_name,))
        subject_id = subject[0] if subject else app.new_id("subject")
        now = app.iso(app.utc_now())
        if not subject:
            store.insert_subject(con, (subject_id, subject_name, now))
        topic_id = app.new_id("topic")
        pos = store.next_topic_position(con, (subject_id,))[0]
        store.insert_topic(con, (topic_id, subject_id, title, pos, now))
        con.commit()
    return {"id": topic_id, "subject_id": subject_id, "title": title}


def create_lesson(app, body):
    topic_id = app.clean_text(body.get("topic_id"), "tópico", 100)
    title = app.clean_text(body.get("title"), "aula", 180)
    with app.study_db() as con:
        if store.topic_exists(con, (topic_id,)) is None:
            raise DomainError("Tópico não encontrado.", 404)
        lesson_id = app.new_id("lesson")
        store.insert_lesson(con, (lesson_id, topic_id, title, app.iso(app.utc_now())))
        con.commit()
    return {"id": lesson_id, "title": title}


def update_lesson(app, lesson_id, body):
    title = app.clean_text(body.get("title"), "aula", 180)
    reference = body.get("reference_scene", ...)
    encoded = None if reference is None else app.safe_json(reference, 8000000) if reference is not ... else ...
    with app.study_db() as con:
        if encoded is ...:
            cur = store.update_title(con, (title, lesson_id))
        else:
            cur = store.update_reference(con, (title, encoded, lesson_id))
        if not cur.rowcount:
            raise DomainError("Aula não encontrada.", 404)
        con.commit()
    return app.get_lesson(lesson_id)


def set_questions(app, lesson_id, body):
    ids = body.get("occurrence_ids")
    if not isinstance(ids, list) or len(ids) > 3000:
        raise DomainError("Selecione até 3000 questões.")
    ids = list(dict.fromkeys((app.clean_text(x, "questão", 100) for x in ids)))
    with app.content_db() as content:
        valid_ids = {q["ocorrencia_id"] for q in question_links.content_items(content, ids)}
    if len(valid_ids) != len(ids):
        raise DomainError("Uma ou mais questões não foram encontradas na base.", 404)
    with app.study_db() as con:
        if store.lesson_exists(con, (lesson_id,)) is None:
            raise DomainError("Aula não encontrada.", 404)
        old_ids = {r[0] for r in store.question_ids_record(con, (lesson_id,))}
        store.remove_questions(con, [(lesson_id, occ) for occ in old_ids - set(ids)])
        store.save_questions(con, [(lesson_id, occ, i) for i, occ in enumerate(ids)])
        con.commit()
    return app.get_lesson(lesson_id)


def delete_material(app, material_id):
    with app.study_db() as con:
        cur = store.delete_material(con, (material_id,))
        con.commit()
    if not cur.rowcount:
        raise DomainError("Material não encontrado.", 404)
    return {"ok": True}
