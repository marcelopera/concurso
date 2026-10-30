"""Lessons use cases; dependencies are supplied by the composition root."""

from __future__ import annotations

import re
from datetime import datetime

import profiles
import question_links
import roadmap


def get_lesson(app, lesson_id: str) -> dict | None:
    with app.study_db() as con:
        row = con.execute(
            "SELECT l.*, t.title AS topic_title, s.name AS subject_name FROM lessons l JOIN topics t USING(topic_id) JOIN subjects s USING(subject_id) WHERE lesson_id=?",
            (lesson_id,),
        ).fetchone()
        if row is None:
            return None
        lesson = dict(row)
        lesson["roadmap"] = roadmap.lesson_metadata(con, lesson_id)
        lesson["reference_scene"] = app.json_load(lesson["reference_scene"])
        lesson["occurrence_ids"] = [
            r[0]
            for r in con.execute(
                "SELECT occurrence_id FROM lesson_questions WHERE lesson_id=? ORDER BY position, occurrence_id",
                (lesson_id,),
            )
        ]
        lesson["materials"] = [
            dict(r)
            for r in con.execute(
                "SELECT * FROM materials WHERE lesson_id=? ORDER BY position, created_at", (lesson_id,)
            )
        ]
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
        for s in con.execute("SELECT * FROM subjects ORDER BY name"):
            subject = {"id": s["subject_id"], "name": s["name"], "topics": []}
            for t in con.execute("SELECT * FROM topics WHERE subject_id=? ORDER BY position,title", (s["subject_id"],)):
                lessons = [
                    dict(lesson)
                    for lesson in con.execute(
                        "SELECT lesson_id AS id,title,completed_at,created_at FROM lessons WHERE topic_id=? ORDER BY created_at, lesson_id",
                        (t["topic_id"],),
                    )
                ]
                for lesson in lessons:
                    lesson["question_count"] = question_counts.get(lesson["id"], 0)
                subject["topics"].append({"id": t["topic_id"], "title": t["title"], "lessons": lessons})
            subjects.append(subject)
        active_sessions = []
        for active in con.execute(
            "SELECT ss.*,l.title AS lesson_title,l.topic_id,t.title AS topic_title,s.name AS subject_name FROM study_sessions ss JOIN lessons l USING(lesson_id) JOIN topics t USING(topic_id) JOIN subjects s USING(subject_id) WHERE ss.status='active' ORDER BY ss.updated_at DESC, ss.session_id DESC"
        ):
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
    available = profiles.list_profiles(app.STUDY_DB)
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


def add_lesson_material(app, path: str, body: dict):
    match = re.fullmatch("/api/lessons/([A-Za-z0-9_-]+)/materials", path)
    if not match:
        return None
    lesson_id = match.group(1)
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
            doc = source.execute("SELECT arquivo_local FROM documentos WHERE documento_id=?", (doc_id,)).fetchone()
        if not doc or app.safe_library_file(doc["arquivo_local"]) is None:
            raise ValueError("O PDF não está disponível dentro da biblioteca local.")
    with app.study_db() as con:
        if con.execute("SELECT 1 FROM lessons WHERE lesson_id=?", (lesson_id,)).fetchone() is None:
            raise ValueError("Aula não encontrada.")
        pos = con.execute(
            "SELECT coalesce(max(position),-1)+1 FROM materials WHERE lesson_id=?", (lesson_id,)
        ).fetchone()[0]
        material_id = app.new_id("material")
        con.execute(
            "INSERT INTO materials(material_id,lesson_id,title,url,document_id,position,created_at) VALUES(?,?,?,?,?,?,?)",
            (material_id, lesson_id, title, url, doc_id, pos, app.iso(app.utc_now())),
        )
        con.commit()
    return app.get_lesson(lesson_id)
