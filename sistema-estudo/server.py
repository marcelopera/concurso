from __future__ import annotations

import json
import mimetypes
import os
import re
import sqlite3
import sys
import threading
import uuid
import argparse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from zoneinfo import ZoneInfo
import roadmap
import question_links
import profiles


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
CONTENT_DB = REPO_ROOT / "base-questoes" / "dados" / "conteudo.sqlite"
LIBRARY_ROOT = (REPO_ROOT / "biblioteca-concursos").resolve()
DATA_DIR = APP_ROOT / "dados"
STUDY_DB = Path(os.environ.get("ESTUDO_DB", str(DATA_DIR / "estudo.sqlite"))).resolve()
DIST_ROOT = APP_ROOT / "dist"
LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
PORT = int(os.environ.get("ESTUDO_PORT", "8765"))
MAX_BODY = 22 * 1024 * 1024
STEP_MINUTES = [10, 5, 20, 10, 15, 3]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds") if value else None


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def study_db() -> sqlite3.Connection:
    STUDY_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(profiles.database(STUDY_DB, profiles.current.get()), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 15000")
    return con


def content_db() -> sqlite3.Connection:
    if not CONTENT_DB.is_file():
        raise RuntimeError(f"Banco de conteúdo não encontrado: {CONTENT_DB}")
    uri = f"file:{CONTENT_DB.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    return con


def init_db() -> None:
    with study_db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id TEXT PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS topics (
                topic_id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(subject_id, title)
            );
            CREATE TABLE IF NOT EXISTS lessons (
                lesson_id TEXT PRIMARY KEY,
                topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                completed_at TEXT,
                reference_scene TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lesson_questions (
                lesson_id TEXT NOT NULL REFERENCES lessons(lesson_id) ON DELETE CASCADE,
                occurrence_id TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(lesson_id, occurrence_id)
            );
            CREATE TABLE IF NOT EXISTS materials (
                material_id TEXT PRIMARY KEY,
                lesson_id TEXT NOT NULL REFERENCES lessons(lesson_id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                url TEXT,
                document_id TEXT,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                CHECK ((url IS NOT NULL AND document_id IS NULL) OR
                       (url IS NULL AND document_id IS NOT NULL))
            );
            CREATE TABLE IF NOT EXISTS study_sessions (
                session_id TEXT PRIMARY KEY,
                lesson_id TEXT NOT NULL REFERENCES lessons(lesson_id) ON DELETE CASCADE,
                status TEXT NOT NULL CHECK(status IN ('active','completed')),
                current_step INTEGER NOT NULL DEFAULT 0 CHECK(current_step BETWEEN 0 AND 5),
                deadline_at TEXT,
                paused_remaining INTEGER,
                payload TEXT NOT NULL DEFAULT '{}',
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS ix_sessions_status ON study_sessions(status, updated_at);
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES study_sessions(session_id) ON DELETE SET NULL,
                stage TEXT NOT NULL,
                occurrence_id TEXT NOT NULL,
                answer TEXT NOT NULL,
                help_used INTEGER NOT NULL DEFAULT 0,
                reference_snapshot TEXT NOT NULL,
                correct INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_attempts_created ON attempts(created_at DESC);
            CREATE TABLE IF NOT EXISTS cards (
                card_id TEXT PRIMARY KEY,
                topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
                source_session_id TEXT REFERENCES study_sessions(session_id) ON DELETE SET NULL,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                difficulty TEXT NOT NULL DEFAULT '',
                interval_days INTEGER NOT NULL DEFAULT 1 CHECK(interval_days IN (1,3,7)),
                due_date TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_cards_due ON cards(active, due_date);
            CREATE TABLE IF NOT EXISTS card_reviews (
                review_id TEXT PRIMARY KEY,
                card_id TEXT NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
                rating TEXT NOT NULL CHECK(rating IN ('errei','dificil','facil')),
                interval_before INTEGER NOT NULL,
                interval_after INTEGER NOT NULL,
                due_after TEXT NOT NULL,
                reviewed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lesson_difficulties (
                difficulty_id TEXT PRIMARY KEY,
                lesson_id TEXT NOT NULL REFERENCES lessons(lesson_id) ON DELETE CASCADE,
                session_id TEXT NOT NULL REFERENCES study_sessions(session_id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        roadmap.init_schema(con)
        question_links.init_schema(con)


def row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def json_load(value: str | None, fallback=None):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def safe_json(value, max_chars: int = 20_000_000) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(encoded) > max_chars:
        raise ValueError("O conteúdo salvo é grande demais.")
    return encoded


def clean_text(value, name: str, maximum: int = 500, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Informe {name}.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"Informe {name}.")
    if len(value) > maximum:
        raise ValueError(f"{name.capitalize()} deve ter até {maximum} caracteres.")
    return value


def safe_library_file(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    try:
        target = Path(path_value).resolve(strict=True)
        if not target.is_file() or not target.is_relative_to(LIBRARY_ROOT):
            return None
        if target.suffix.lower() != ".pdf":
            return None
        return target
    except (OSError, RuntimeError, ValueError):
        return None


def content_question(occurrence_id: str, include_answer: bool = False) -> dict | None:
    with content_db() as con:
        row = con.execute(
            """
            SELECT v.*, o.documento_id AS source_document_id,
                   r.resposta_referencia, r.situacao_referencia,
                   r.estado AS reference_state,
                   r.possui_publicacao_definitiva AS has_definitive,
                   CASE WHEN r.estado='concordante'
                          AND r.situacao_referencia='valido'
                          AND r.possui_publicacao_definitiva=1
                          AND v.status_extracao='extraido'
                        THEN 1 ELSE 0 END AS can_grade
            FROM vw_questoes v
            JOIN ocorrencias o USING(ocorrencia_id)
            LEFT JOIN vw_gabaritos_referencia r USING(ocorrencia_id)
            WHERE v.ocorrencia_id=?
            """,
            (occurrence_id,),
        ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["contexts"] = [r[0] for r in con.execute(
            "SELECT c.texto_original FROM questao_contexto qc "
            "JOIN contextos c USING(contexto_id) WHERE qc.questao_id=? ORDER BY qc.ordem",
            (item["questao_id"],),
        )]
        alternatives = [dict(r) for r in con.execute(
            "SELECT rotulo, texto_original FROM alternativas WHERE questao_id=? ORDER BY ordem, alternativa_id",
            (item["questao_id"],),
        )]
        if item["formato"] == "certo_errado" and not alternatives:
            alternatives = [{"rotulo": "C", "texto_original": "Certo"},
                            {"rotulo": "E", "texto_original": "Errado"}]
        item["alternatives"] = alternatives
        item["reference_status"] = {
            "state": item.pop("reference_state") or "sem referência consolidada",
            "situation": item.pop("situacao_referencia"),
            "has_definitive": bool(item.pop("has_definitive") or 0),
            "extraction": item.get("status_extracao"),
            "correctable": bool(item.pop("can_grade")),
        }
        if not include_answer:
            item.pop("resposta_referencia", None)
        else:
            item["source_answers"] = [dict(r) for r in con.execute(
                """
                SELECT g.resposta_publicada, g.situacao_item, g.natureza_gabarito,
                       g.paginas_json, g.documento_id, d.titulo AS document_title
                FROM vw_gabaritos_associados g
                LEFT JOIN documentos d USING(documento_id)
                WHERE g.ocorrencia_id=? ORDER BY g.natureza_gabarito, g.documento_id
                """,
                (occurrence_id,),
            )]
        return item


def question_for_client(item: dict, include_answer: bool = False) -> dict:
    # Never expose the reference during the quiz. The answer only enters this
    # object after the server has recorded an attempt.
    out = {
        "occurrence_id": item["ocorrencia_id"],
        "question_id": item["questao_id"],
        "format": item.get("formato"),
        "stem": item.get("enunciado_original"),
        "search_text": item.get("texto_para_busca"),
        "contexts": item.get("contexts", []),
        "alternatives": [{"label": a.get("rotulo"), "text": a.get("texto_original")}
                         for a in item.get("alternatives", [])],
        "bank": item.get("banca"),
        "contest": item.get("concurso"),
        "exam_title": item.get("titulo"),
        "number": item.get("numero_original"),
        "block": item.get("bloco_original"),
        "discipline": item.get("disciplina_original"),
        "pages": json_load(item.get("paginas_json"), []),
        "source_document_id": item.get("source_document_id"),
        "status_extraction": item.get("status_extracao"),
        "reference_status": item.get("reference_status"),
        "mapping": item.get("mapping"),
    }
    if include_answer:
        out["reference_answer"] = item.get("resposta_referencia")
        out["source_answers"] = [{
            "answer": source.get("resposta_publicada"),
            "situation": source.get("situacao_item"),
            "nature": source.get("natureza_gabarito"),
            "pages": json_load(source.get("paginas_json"), []),
            "document_id": source.get("documento_id"),
            "document_title": source.get("document_title"),
        } for source in item.get("source_answers", [])]
    return out


def question_page(search: str, bank: str, discipline: str, page: int,
                  eligible_only: bool = True, limit: int = 24) -> dict:
    where = ["1=1"]
    args: list = []
    eligible = "(r.estado='concordante' AND r.situacao_referencia='valido' AND r.possui_publicacao_definitiva=1 AND v.status_extracao='extraido')"
    if eligible_only:
        where.append(eligible)
    if bank:
        where.append("v.banca=?")
        args.append(bank)
    if discipline:
        where.append("v.disciplina_original=?")
        args.append(discipline)
    if search:
        needle = f"%{search[:160]}%"
        where.append("(v.enunciado_original LIKE ? OR v.texto_para_busca LIKE ? OR v.banca LIKE ? "
                     "OR v.titulo LIKE ? OR v.concurso LIKE ? OR v.numero_original LIKE ? "
                     "OR v.disciplina_original LIKE ? OR v.bloco_original LIKE ?)")
        args.extend([needle] * 8)
    cond = " AND ".join(where)
    offset = (page - 1) * limit
    with content_db() as con:
        total = con.execute(
            "SELECT count(*) FROM vw_questoes v LEFT JOIN vw_gabaritos_referencia r USING(ocorrencia_id) WHERE " + cond, args
        ).fetchone()[0]
        rows = con.execute(
            """
            SELECT v.*, o.documento_id AS source_document_id,
                   r.resposta_referencia, r.situacao_referencia,
                   r.estado AS reference_state,
                   r.possui_publicacao_definitiva AS has_definitive,
                   CASE WHEN r.estado='concordante'
                          AND r.situacao_referencia='valido'
                          AND r.possui_publicacao_definitiva=1
                          AND v.status_extracao='extraido'
                        THEN 1 ELSE 0 END AS can_grade
            FROM vw_questoes v
            JOIN ocorrencias o USING(ocorrencia_id)
            LEFT JOIN vw_gabaritos_referencia r USING(ocorrencia_id)
            WHERE """ + cond +
            " ORDER BY v.banca, v.concurso, v.titulo, v.numero_original, v.ocorrencia_id LIMIT ? OFFSET ?",
            [*args, limit, offset],
        ).fetchall()
        question_ids = list({r["questao_id"] for r in rows})
        alt_map: dict[str, list] = {q: [] for q in question_ids}
        context_map: dict[str, list] = {q: [] for q in question_ids}
        if question_ids:
            marks = ",".join("?" for _ in question_ids)
            for r in con.execute(
                f"SELECT questao_id,rotulo,texto_original FROM alternativas WHERE questao_id IN ({marks}) ORDER BY ordem",
                question_ids,
            ):
                alt_map[r["questao_id"]].append({"rotulo": r["rotulo"], "texto_original": r["texto_original"]})
            for r in con.execute(
                f"SELECT qc.questao_id,c.texto_original FROM questao_contexto qc JOIN contextos c USING(contexto_id) WHERE qc.questao_id IN ({marks}) ORDER BY qc.ordem",
                question_ids,
            ):
                context_map[r["questao_id"]].append(r["texto_original"])
        items = []
        for row in rows:
            item = dict(row)
            item["alternatives"] = alt_map[item["questao_id"]]
            if item["formato"] == "certo_errado" and not item["alternatives"]:
                item["alternatives"] = [{"rotulo": "C", "texto_original": "Certo"},
                                        {"rotulo": "E", "texto_original": "Errado"}]
            item["contexts"] = context_map[item["questao_id"]]
            item["reference_status"] = {
                "state": item.pop("reference_state") or "sem referência consolidada",
                "situation": item.pop("situacao_referencia"),
                "has_definitive": bool(item.pop("has_definitive") or 0),
                "extraction": item.get("status_extracao"),
                "correctable": bool(item.pop("can_grade")),
            }
            item.pop("resposta_referencia", None)
            items.append(question_for_client(item))
        option_join = " JOIN ocorrencias o USING(ocorrencia_id) LEFT JOIN vw_gabaritos_referencia r USING(ocorrencia_id) "
        option_filter = f" AND {eligible}" if eligible_only else ""
        banks = [r[0] for r in con.execute(
            "SELECT DISTINCT v.banca FROM vw_questoes v" + option_join +
            "WHERE v.banca IS NOT NULL AND v.banca<>''" + option_filter + " ORDER BY v.banca")]
        disciplines = [r[0] for r in con.execute(
            "SELECT DISTINCT v.disciplina_original FROM vw_questoes v" + option_join +
            "WHERE v.disciplina_original IS NOT NULL AND v.disciplina_original<>''" + option_filter +
            " ORDER BY v.disciplina_original")]
    return {"items": items, "total": total, "page": page, "limit": limit,
            "pages": max(1, (total + limit - 1) // limit), "banks": banks, "disciplines": disciplines}


def get_lesson(lesson_id: str) -> dict | None:
    with study_db() as con:
        row = con.execute(
            "SELECT l.*, t.title AS topic_title, s.name AS subject_name "
            "FROM lessons l JOIN topics t USING(topic_id) JOIN subjects s USING(subject_id) WHERE lesson_id=?",
            (lesson_id,),
        ).fetchone()
        if row is None:
            return None
        lesson = dict(row)
        lesson["roadmap"] = roadmap.lesson_metadata(con, lesson_id)
        lesson["reference_scene"] = json_load(lesson["reference_scene"])
        lesson["occurrence_ids"] = [r[0] for r in con.execute(
            "SELECT occurrence_id FROM lesson_questions WHERE lesson_id=? ORDER BY position, occurrence_id",
            (lesson_id,),
        )]
        lesson["materials"] = [dict(r) for r in con.execute(
            "SELECT * FROM materials WHERE lesson_id=? ORDER BY position, created_at", (lesson_id,)
        )]
        mappings = question_links.lesson_mappings(con, lesson_id)
    with content_db() as con:
        questions = question_links.content_items(con, lesson["occurrence_ids"])
    lesson["questions"] = []
    for q in questions:
        q["mapping"] = mappings.get(q["ocorrencia_id"])
        lesson["questions"].append(question_for_client(q))
    for material in lesson["materials"]:
        if material["document_id"]:
            material["open_url"] = f"/api/library/file?document_id={material['document_id']}"
        else:
            material["open_url"] = material["url"]
    return lesson


def bootstrap() -> dict:
    with study_db() as con:
        plan = roadmap.public_plan(con, datetime.now(LOCAL_TZ).date().isoformat())
        if plan:
            plan["question_mapping"] = question_links.summary(con)
        question_counts = question_links.counts(con)
        subjects = []
        for s in con.execute("SELECT * FROM subjects ORDER BY name"):
            subject = {"id": s["subject_id"], "name": s["name"], "topics": []}
            for t in con.execute("SELECT * FROM topics WHERE subject_id=? ORDER BY position,title", (s["subject_id"],)):
                lessons = [dict(l) for l in con.execute(
                    "SELECT lesson_id AS id,title,completed_at,created_at FROM lessons WHERE topic_id=? ORDER BY created_at, lesson_id",
                    (t["topic_id"],),
                )]
                for lesson in lessons:
                    lesson["question_count"] = question_counts.get(lesson["id"], 0)
                subject["topics"].append({"id": t["topic_id"], "title": t["title"], "lessons": lessons})
            subjects.append(subject)
        active = con.execute(
            "SELECT ss.*,l.title AS lesson_title,l.topic_id,t.title AS topic_title,s.name AS subject_name "
            "FROM study_sessions ss JOIN lessons l USING(lesson_id) JOIN topics t USING(topic_id) "
            "JOIN subjects s USING(subject_id) WHERE ss.status='active' ORDER BY ss.updated_at DESC LIMIT 1"
        ).fetchone()
        active_session = None
        if active:
            active_session = dict(active)
            active_session["payload"] = json_load(active_session["payload"], {})
            active_session["timer"] = timer_state(active_session)
    totals = {"lessons": sum(len(t["lessons"]) for s in subjects for t in s["topics"]),
              "completed": sum(1 for s in subjects for t in s["topics"] for l in t["lessons"] if l["completed_at"])}
    available = profiles.list_profiles(STUDY_DB)
    return {"subjects": subjects, "totals": totals, "active_session": active_session, "roadmap": plan,
            "profiles": available, "profile": next(p for p in available if p['id'] == profiles.current.get())}


def timer_state(session: dict) -> dict:
    if session.get("paused_remaining") is not None:
        seconds = max(0, int(session["paused_remaining"]))
        paused = True
    elif session.get("deadline_at"):
        try:
            deadline = datetime.fromisoformat(session["deadline_at"])
            seconds = max(0, int((deadline - utc_now()).total_seconds()))
        except (TypeError, ValueError):
            seconds = STEP_MINUTES[int(session.get("current_step", 0))] * 60
        paused = False
    else:
        seconds = STEP_MINUTES[int(session.get("current_step", 0))] * 60
        paused = False
    return {"remaining_seconds": seconds, "paused": paused, "deadline_at": session.get("deadline_at")}


def session_public(session: sqlite3.Row | dict) -> dict:
    d = dict(session)
    d["payload"] = json_load(d.get("payload"), {})
    d["timer"] = timer_state(d)
    return d


def associated_snapshot(occurrence_id: str) -> dict:
    with content_db() as con:
        row = con.execute(
            """SELECT resposta_referencia,situacao_referencia,estado,possui_publicacao_definitiva
               FROM vw_gabaritos_referencia WHERE ocorrencia_id=?""",
            (occurrence_id,),
        ).fetchone()
        # The associated view is the authority for the source answer records.
        answers = [dict(r) for r in con.execute(
            """SELECT g.resposta_publicada,g.situacao_item,g.natureza_gabarito,
                      g.paginas_json,g.documento_id,d.titulo AS document_title
               FROM vw_gabaritos_associados g LEFT JOIN documentos d USING(documento_id)
               WHERE g.ocorrencia_id=? ORDER BY g.natureza_gabarito,g.documento_id""",
            (occurrence_id,),
        )]
    if row is None:
        return {"answer": None, "situation": None, "state": "sem referência consolidada",
                "has_definitive": False, "associated": answers}
    return {"answer": row["resposta_referencia"], "situation": row["situacao_referencia"],
            "state": row["estado"], "has_definitive": bool(row["possui_publicacao_definitiva"]),
            "associated": answers}


def answer_snapshot(occurrence_id: str, response: str, stage: str,
                    help_used: bool = False, session_id: str | None = None) -> dict:
    item = content_question(occurrence_id)
    if item is None:
        raise ValueError("Questão não encontrada na base de conteúdo.")
    answer = clean_text(response, "resposta", 4000)
    options = {str(a.get("rotulo", "")).strip().upper() for a in item.get("alternatives", [])}
    normalized = answer.strip().upper()
    if options and normalized not in options:
        raise ValueError("Escolha uma alternativa disponível.")
    source = associated_snapshot(occurrence_id)
    extraction = item.get("status_extracao")
    auto_grade = (item["reference_status"]["correctable"] and extraction == "extraido"
                  and source["state"] == "concordante" and source["situation"] == "valido"
                  and source["has_definitive"] and bool(source["answer"]))
    correct = (int(normalized == str(source["answer"]).strip().upper()) if auto_grade else None)
    public_associated = [{
        "answer": source_answer.get("resposta_publicada"),
        "situation": source_answer.get("situacao_item"),
        "nature": source_answer.get("natureza_gabarito"),
        "pages": json_load(source_answer.get("paginas_json"), []),
        "document_id": source_answer.get("documento_id"),
        "document_title": source_answer.get("document_title"),
    } for source_answer in source["associated"]]
    snap = {
        "reference_answer": source["answer"],
        "situation": source["situation"],
        "state": source["state"],
        "has_definitive": source["has_definitive"],
        "extraction": extraction,
        "auto_graded": bool(auto_grade),
        "associated_answers": public_associated,
        "responded_at": iso(utc_now()),
    }
    attempt_id = new_id("attempt")
    with study_db() as con:
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
            "INSERT INTO attempts(attempt_id,session_id,stage,occurrence_id,answer,help_used,reference_snapshot,correct,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (attempt_id, session_id, stage, occurrence_id, answer, int(help_used),
             safe_json(snap), correct, iso(utc_now())),
        )
        con.commit()
    return {"attempt_id": attempt_id, "stage": stage, "occurrence_id": occurrence_id,
            "answer": answer, "correct": (bool(correct) if correct is not None else None),
            "help_used": bool(help_used), "snapshot": snap,
            "question": question_for_client(content_question(occurrence_id, include_answer=True), True)}


def library_docs(search: str = "") -> list[dict]:
    with content_db() as con:
        rows = con.execute(
            "SELECT documento_id,tipo,banca,concurso,titulo,nome,arquivo_local,paginas "
            "FROM documentos WHERE lower(arquivo_local) LIKE '%.pdf' "
            "ORDER BY concurso,banca,tipo,nome"
        ).fetchall()
    needle = search.strip().casefold()
    result = []
    for r in rows:
        path = safe_library_file(r["arquivo_local"])
        if path is None:
            continue
        data = dict(r)
        data["label"] = " · ".join(x for x in [data.get("concurso"), data.get("banca"), data.get("nome") or data.get("titulo")] if x)
        if needle and needle not in " ".join(str(x or "") for x in data.values()).casefold():
            continue
        data.pop("arquivo_local", None)
        result.append(data)
    return result[:160]


class StudyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = "EstudoLocal/1.0"
    sys_version = ""

    def handle_one_request(self):
        token = profiles.current.set('principal')
        try:
            super().handle_one_request()
        finally:
            profiles.current.reset(token)

    def log_message(self, fmt, *args):
        sys.stdout.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    def _headers(self, status: int, content_type: str, length: int | None = None,
                 extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store" if content_type.startswith("application/json") else "no-cache")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data: blob:; font-src 'self' data:; "
                         "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; worker-src 'self' blob:; "
                         "frame-src 'self'; object-src 'self'; base-uri 'self'; form-action 'self'")
        if length is not None:
            self.send_header("Content-Length", str(length))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def _json(self, data, status: int = 200):
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(raw))
        self.wfile.write(raw)

    def _error(self, message: str, status: int = 400):
        self._json({"error": message}, status)

    def _check_local_origin(self) -> bool:
        allowed_hosts = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
        host = self.headers.get("Host", "").lower()
        if host not in allowed_hosts:
            self._error("A API aceita apenas o endereço local do aplicativo.", 403)
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}:
            self._error("Origem não autorizada.", 403)
            return False
        profile_id = self.headers.get('X-Study-Profile', 'principal')
        try:
            profiles.database(STUDY_DB, profile_id)
        except ValueError as exc:
            self._error(str(exc), 404)
            return False
        profiles.current.set(profile_id)
        return True

    def _body(self) -> dict:
        size = int(self.headers.get("Content-Length", "0"))
        if size < 0 or size > MAX_BODY:
            raise ValueError("A solicitação excede o limite permitido.")
        raw = self.rfile.read(size)
        try:
            value = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("JSON inválido.")
        if not isinstance(value, dict):
            raise ValueError("O corpo da solicitação deve ser um objeto JSON.")
        return value

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/api/") and not self._check_local_origin():
            return
        params = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/health":
                with content_db() as con:
                    count = con.execute("SELECT count(*) FROM ocorrencias").fetchone()[0]
                return self._json({"ok": True, "content_occurrences": count})
            if parsed.path == "/api/bootstrap":
                return self._json(bootstrap())
            if parsed.path == "/api/catalog":
                search = (params.get("search", [""])[0] or "").strip()
                bank = (params.get("bank", [""])[0] or "").strip()
                discipline = (params.get("discipline", [""])[0] or "").strip()
                eligible_only = (params.get("eligible_only", ["1"])[0] or "1").lower() not in ("0", "false", "no")
                page = max(1, min(100000, int(params.get("page", ["1"])[0])))
                return self._json(question_page(search, bank, discipline, page, eligible_only))
            if parsed.path == "/api/library":
                return self._json({"items": library_docs((params.get("search", [""])[0] or "").strip())})
            if parsed.path == "/api/library/file":
                doc_id = (params.get("document_id", [""])[0] or "").strip()
                with content_db() as con:
                    row = con.execute("SELECT arquivo_local,nome FROM documentos WHERE documento_id=?", (doc_id,)).fetchone()
                path = safe_library_file(row["arquivo_local"] if row else None)
                if path is None:
                    return self._error("PDF não encontrado na biblioteca local.", 404)
                data = path.read_bytes()
                name = path.name.replace('"', "")
                self._headers(200, "application/pdf", len(data), {
                    "Content-Disposition": f'inline; filename="{name}"',
                    "Accept-Ranges": "none",
                })
                self.wfile.write(data)
                return
            if parsed.path == "/api/cards/due":
                day = datetime.now(LOCAL_TZ).date().isoformat()
                with study_db() as con:
                    cards = [dict(r) for r in con.execute(
                        "SELECT c.*,t.title AS topic_title,s.name AS subject_name FROM cards c "
                        "JOIN topics t USING(topic_id) JOIN subjects s USING(subject_id) "
                        "WHERE c.active=1 AND c.due_date<=? ORDER BY c.due_date,c.created_at LIMIT 80", (day,)
                    )]
                return self._json({"items": cards, "today": day})
            if parsed.path == "/api/attempts/history":
                with study_db() as con:
                    rows = [dict(r) for r in con.execute(
                        "SELECT attempt_id,stage,occurrence_id,answer,help_used,reference_snapshot,correct,created_at "
                        "FROM attempts WHERE session_id IS NULL ORDER BY created_at DESC LIMIT 100")]
                for r in rows:
                    r["reference_snapshot"] = json_load(r["reference_snapshot"], {})
                return self._json({"items": rows})
            match = re.fullmatch(r"/api/lessons/([A-Za-z0-9_-]+)", parsed.path)
            if match:
                lesson = get_lesson(match.group(1))
                if lesson is None:
                    return self._error("Aula não encontrada.", 404)
                return self._json(lesson)
        except (ValueError, sqlite3.Error, OSError, RuntimeError) as exc:
            return self._error(str(exc), 500)
        return self._static(parsed.path)

    def do_POST(self):
        if self.path.startswith("/api/") and not self._check_local_origin():
            return
        try:
            body = self._body()
            path = urlsplit(self.path).path
            if path == '/api/profiles':
                return self._json(profiles.create(STUDY_DB, body.get('name')), 201)
            if path == '/api/roadmap/reset':
                if body.get('confirm') != profiles.current.get():
                    return self._error('Confirme o perfil para resetar o roadmap.')
                with study_db() as con:
                    result = profiles.reset_roadmap(con, profiles.database(STUDY_DB, profiles.current.get()))
                    con.commit()
                return self._json(result)
            if path == "/api/topics":
                subject_name = clean_text(body.get("subject"), "disciplina", 100)
                title = clean_text(body.get("title"), "tópico", 180)
                with study_db() as con:
                    subject = con.execute("SELECT subject_id FROM subjects WHERE name=? COLLATE NOCASE", (subject_name,)).fetchone()
                    subject_id = subject[0] if subject else new_id("subject")
                    now = iso(utc_now())
                    if not subject:
                        con.execute("INSERT INTO subjects(subject_id,name,created_at) VALUES(?,?,?)", (subject_id, subject_name, now))
                    topic_id = new_id("topic")
                    pos = con.execute("SELECT coalesce(max(position),-1)+1 FROM topics WHERE subject_id=?", (subject_id,)).fetchone()[0]
                    con.execute("INSERT INTO topics(topic_id,subject_id,title,position,created_at) VALUES(?,?,?,?,?)",
                                (topic_id, subject_id, title, pos, now))
                    con.commit()
                return self._json({"id": topic_id, "subject_id": subject_id, "title": title}, 201)
            if path == "/api/lessons":
                topic_id = clean_text(body.get("topic_id"), "tópico", 100)
                title = clean_text(body.get("title"), "aula", 180)
                with study_db() as con:
                    if con.execute("SELECT 1 FROM topics WHERE topic_id=?", (topic_id,)).fetchone() is None:
                        return self._error("Tópico não encontrado.", 404)
                    lesson_id = new_id("lesson")
                    con.execute("INSERT INTO lessons(lesson_id,topic_id,title,created_at) VALUES(?,?,?,?)",
                                (lesson_id, topic_id, title, iso(utc_now())))
                    con.commit()
                return self._json({"id": lesson_id, "title": title}, 201)
            match = re.fullmatch(r"/api/lessons/([A-Za-z0-9_-]+)/sessions", path)
            if match:
                lesson_id = match.group(1)
                with study_db() as con:
                    if con.execute("SELECT 1 FROM lessons WHERE lesson_id=?", (lesson_id,)).fetchone() is None:
                        return self._error("Aula não encontrada.", 404)
                    active = con.execute("SELECT * FROM study_sessions WHERE status='active' ORDER BY updated_at DESC LIMIT 1").fetchone()
                    if active:
                        if active["lesson_id"] != lesson_id:
                            return self._error("Há outra sessão em andamento. Retome ou conclua essa sessão primeiro.", 409)
                        return self._json(session_public(active))
                    session_id = new_id("session")
                    now = utc_now()
                    deadline = now + timedelta(minutes=STEP_MINUTES[0])
                    with content_db() as content:
                        initial_payload = question_links.session_pool(con, content, lesson_id)
                    con.execute(
                        "INSERT INTO study_sessions(session_id,lesson_id,status,current_step,deadline_at,payload,started_at,updated_at) "
                        "VALUES(?,?,'active',0,?,?,?,?)",
                        (session_id, lesson_id, iso(deadline), safe_json(initial_payload), iso(now), iso(now)),
                    )
                    con.commit()
                    row = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (session_id,)).fetchone()
                return self._json(session_public(row), 201)
            match = re.fullmatch(r"/api/lessons/([A-Za-z0-9_-]+)/materials", path)
            if match:
                return self._json(add_lesson_material(path, body), 201)
            match = re.fullmatch(r"/api/sessions/([A-Za-z0-9_-]+)/step", path)
            if match:
                step = body.get("step")
                if not isinstance(step, int) or step < 0 or step > 5:
                    return self._error("Etapa inválida.")
                with study_db() as con:
                    row = con.execute("SELECT * FROM study_sessions WHERE session_id=? AND status='active'", (match.group(1),)).fetchone()
                    if row is None:
                        return self._error("Sessão ativa não encontrada.", 404)
                    now = utc_now()
                    con.execute("UPDATE study_sessions SET current_step=?,deadline_at=?,paused_remaining=NULL,updated_at=? WHERE session_id=?",
                                (step, iso(now + timedelta(minutes=STEP_MINUTES[step])), iso(now), match.group(1)))
                    con.commit()
                    updated = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (match.group(1),)).fetchone()
                return self._json(session_public(updated))
            match = re.fullmatch(r"/api/sessions/([A-Za-z0-9_-]+)/pause", path)
            if match:
                with study_db() as con:
                    row = con.execute("SELECT * FROM study_sessions WHERE session_id=? AND status='active'", (match.group(1),)).fetchone()
                    if row is None:
                        return self._error("Sessão ativa não encontrada.", 404)
                    if row["paused_remaining"] is None:
                        remaining = max(0, int((datetime.fromisoformat(row["deadline_at"]) - utc_now()).total_seconds())) if row["deadline_at"] else 0
                        con.execute("UPDATE study_sessions SET deadline_at=NULL,paused_remaining=?,updated_at=? WHERE session_id=?",
                                    (remaining, iso(utc_now()), match.group(1)))
                    else:
                        remaining = max(0, int(row["paused_remaining"]))
                        con.execute("UPDATE study_sessions SET deadline_at=?,paused_remaining=NULL,updated_at=? WHERE session_id=?",
                                    (iso(utc_now() + timedelta(seconds=remaining)), iso(utc_now()), match.group(1)))
                    con.commit()
                    updated = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (match.group(1),)).fetchone()
                return self._json(session_public(updated))
            match = re.fullmatch(r"/api/sessions/([A-Za-z0-9_-]+)/answer", path)
            if match:
                stage = body.get("stage")
                if stage not in ("recall", "pretest", "practice"):
                    return self._error("Etapa de resposta inválida.")
                result = answer_snapshot(
                    clean_text(body.get("occurrence_id"), "questão", 100),
                    clean_text(body.get("answer"), "resposta", 4000), stage,
                    bool(body.get("help_used", False)), match.group(1),
                )
                return self._json(result, 201)
            match = re.fullmatch(r"/api/sessions/([A-Za-z0-9_-]+)/complete", path)
            if match:
                return self._complete_session(match.group(1), body)
            if path == "/api/attempts":
                result = answer_snapshot(
                    clean_text(body.get("occurrence_id"), "questão", 100),
                    clean_text(body.get("answer"), "resposta", 4000), "free",
                    bool(body.get("help_used", False)),
                )
                return self._json(result, 201)
            match = re.fullmatch(r"/api/cards/([A-Za-z0-9_-]+)/review", path)
            if match:
                return self._review_card(match.group(1), body)
        except ValueError as exc:
            return self._error(str(exc), 400)
        except sqlite3.IntegrityError as exc:
            return self._error(f"Não foi possível salvar: {exc}", 409)
        except (sqlite3.Error, OSError, RuntimeError, TypeError) as exc:
            return self._error(str(exc), 500)
        return self._error("Rota não encontrada.", 404)

    def do_PUT(self):
        if self.path.startswith("/api/") and not self._check_local_origin():
            return
        try:
            body = self._body()
            path = urlsplit(self.path).path
            activity_match = re.fullmatch(r"/api/roadmap/activities/([A-Za-z0-9_-]+)", path)
            if activity_match:
                with study_db() as con:
                    result = roadmap.update_activity(con, activity_match.group(1), body)
                    con.commit()
                return self._json(result)
            match = re.fullmatch(r"/api/lessons/([A-Za-z0-9_-]+)", path)
            if match:
                lesson_id = match.group(1)
                title = clean_text(body.get("title"), "aula", 180)
                reference = body.get("reference_scene", ...)
                encoded = None if reference is None else (safe_json(reference, 8_000_000) if reference is not ... else ...)
                with study_db() as con:
                    if encoded is ...:
                        cur = con.execute("UPDATE lessons SET title=? WHERE lesson_id=?", (title, lesson_id))
                    else:
                        cur = con.execute("UPDATE lessons SET title=?,reference_scene=? WHERE lesson_id=?",
                                          (title, encoded, lesson_id))
                    if not cur.rowcount:
                        return self._error("Aula não encontrada.", 404)
                    con.commit()
                return self._json(get_lesson(lesson_id))
            match = re.fullmatch(r"/api/lessons/([A-Za-z0-9_-]+)/questions", path)
            if match:
                lesson_id = match.group(1)
                ids = body.get("occurrence_ids")
                if not isinstance(ids, list) or len(ids) > 3000:
                    return self._error("Selecione até 3000 questões.")
                ids = list(dict.fromkeys(clean_text(x, "questão", 100) for x in ids))
                with content_db() as content:
                    valid_ids = {q["ocorrencia_id"] for q in question_links.content_items(content, ids)}
                if len(valid_ids) != len(ids):
                    return self._error("Uma ou mais questões não foram encontradas na base.", 404)
                with study_db() as con:
                    if con.execute("SELECT 1 FROM lessons WHERE lesson_id=?", (lesson_id,)).fetchone() is None:
                        return self._error("Aula não encontrada.", 404)
                    # Keep provenance for selections that remain; remove only the
                    # links the user actually deselected (metadata cascades).
                    old_ids = {r[0] for r in con.execute("SELECT occurrence_id FROM lesson_questions WHERE lesson_id=?", (lesson_id,))}
                    con.executemany("DELETE FROM lesson_questions WHERE lesson_id=? AND occurrence_id=?",
                                    [(lesson_id, occ) for occ in old_ids - set(ids)])
                    con.executemany("INSERT INTO lesson_questions(lesson_id,occurrence_id,position) VALUES(?,?,?) "
                                    "ON CONFLICT(lesson_id,occurrence_id) DO UPDATE SET position=excluded.position",
                                    [(lesson_id, occ, i) for i, occ in enumerate(ids)])
                    con.commit()
                return self._json(get_lesson(lesson_id))
            match = re.fullmatch(r"/api/sessions/([A-Za-z0-9_-]+)/state", path)
            if match:
                payload = body.get("payload")
                if not isinstance(payload, dict):
                    return self._error("Estado da sessão inválido.")
                encoded = safe_json(payload, 20_000_000)
                now = iso(utc_now())
                with study_db() as con:
                    cur = con.execute("UPDATE study_sessions SET payload=?,updated_at=? WHERE session_id=? AND status='active'",
                                      (encoded, now, match.group(1)))
                    if not cur.rowcount:
                        return self._error("Sessão ativa não encontrada.", 404)
                    con.commit()
                    updated = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (match.group(1),)).fetchone()
                return self._json(session_public(updated))
        except ValueError as exc:
            return self._error(str(exc), 400)
        except sqlite3.IntegrityError as exc:
            return self._error(f"Não foi possível salvar: {exc}", 409)
        except (sqlite3.Error, OSError, RuntimeError, TypeError) as exc:
            return self._error(str(exc), 500)
        return self._error("Rota não encontrada.", 404)

    def do_DELETE(self):
        if self.path.startswith("/api/") and not self._check_local_origin():
            return
        path = urlsplit(self.path).path
        match = re.fullmatch(r"/api/materials/([A-Za-z0-9_-]+)", path)
        if not match:
            return self._error("Rota não encontrada.", 404)
        try:
            with study_db() as con:
                cur = con.execute("DELETE FROM materials WHERE material_id=?", (match.group(1),))
                con.commit()
            if not cur.rowcount:
                return self._error("Material não encontrado.", 404)
            return self._json({"ok": True})
        except sqlite3.Error as exc:
            return self._error(str(exc), 500)

    def _complete_session(self, session_id: str, body: dict):
        cards = body.get("cards", [])
        difficulties = body.get("difficulties", [])
        if not isinstance(cards, list) or len(cards) > 100:
            return self._error("Lista de cartões inválida.")
        if not isinstance(difficulties, list) or len(difficulties) > 30:
            return self._error("Lista de dificuldades inválida.")
        cleaned_cards = []
        for card in cards:
            if not isinstance(card, dict) or not card.get("selected"):
                continue
            front = clean_text(card.get("front"), "pergunta do cartão", 1200)
            back = clean_text(card.get("back"), "resposta do cartão", 2400)
            difficulty = clean_text(card.get("difficulty", ""), "dificuldade", 300, required=False)
            cleaned_cards.append((front, back, difficulty))
        clean_difficulties = [clean_text(d, "dificuldade", 500) for d in difficulties]
        now = utc_now()
        first_review_due = (datetime.now(LOCAL_TZ).date() + timedelta(days=1)).isoformat()
        with study_db() as con:
            con.execute("BEGIN IMMEDIATE")
            session = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (session_id,)).fetchone()
            if session is None:
                return self._error("Sessão não encontrada.", 404)
            if session["status"] == "completed":
                return self._json(session_public(session))
            topic_id = con.execute("SELECT topic_id FROM lessons WHERE lesson_id=?", (session["lesson_id"],)).fetchone()[0]
            for front, back, difficulty in cleaned_cards:
                con.execute(
                    "INSERT INTO cards(card_id,topic_id,source_session_id,front,back,difficulty,interval_days,due_date,created_at) "
                    "VALUES(?,?,?,?,?,?,1,?,?)",
                    (new_id("card"), topic_id, session_id, front, back, difficulty, first_review_due, iso(now)),
                )
            for text in clean_difficulties:
                con.execute("INSERT INTO lesson_difficulties(difficulty_id,lesson_id,session_id,text,created_at) VALUES(?,?,?,?,?)",
                            (new_id("difficulty"), session["lesson_id"], session_id, text, iso(now)))
            con.execute("UPDATE lessons SET completed_at=coalesce(completed_at,?) WHERE lesson_id=?",
                        (iso(now), session["lesson_id"]))
            con.execute("UPDATE study_sessions SET status='completed',completed_at=?,updated_at=?,current_step=5,deadline_at=NULL,paused_remaining=0 WHERE session_id=?",
                        (iso(now), iso(now), session_id))
            con.commit()
            result = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (session_id,)).fetchone()
        return self._json(session_public(result))

    def _review_card(self, card_id: str, body: dict):
        rating = body.get("rating")
        if rating not in ("errei", "dificil", "facil"):
            return self._error("Escolha Errei, Difícil ou Fácil.")
        now_local = datetime.now(LOCAL_TZ)
        today = now_local.date()
        with study_db() as con:
            card = con.execute("SELECT * FROM cards WHERE card_id=? AND active=1", (card_id,)).fetchone()
            if card is None:
                return self._error("Cartão não encontrado.", 404)
            before = int(card["interval_days"])
            if rating == "errei":
                after = 1
            elif rating == "dificil":
                after = before
            else:
                after = {1: 3, 3: 7, 7: 7}.get(before, 1)
            due = (today + timedelta(days=after)).isoformat()
            reviewed = iso(now_local)
            con.execute("UPDATE cards SET interval_days=?,due_date=? WHERE card_id=?", (after, due, card_id))
            con.execute("INSERT INTO card_reviews(review_id,card_id,rating,interval_before,interval_after,due_after,reviewed_at) VALUES(?,?,?,?,?,?,?)",
                        (new_id("review"), card_id, rating, before, after, due, reviewed))
            con.commit()
            updated = dict(con.execute("SELECT * FROM cards WHERE card_id=?", (card_id,)).fetchone())
        return self._json({"card": updated, "rating": rating, "interval_before": before,
                           "interval_after": after, "due_date": due})

    def _static(self, path: str):
        if not DIST_ROOT.is_dir():
            return self._error("A interface ainda não foi compilada. Execute npm run build.", 503)
        requested = unquote(path.lstrip("/")) or "index.html"
        try:
            target = (DIST_ROOT / requested).resolve(strict=True)
            root = DIST_ROOT.resolve()
            if not target.is_relative_to(root) or not target.is_file():
                raise FileNotFoundError
        except (OSError, ValueError, RuntimeError):
            target = DIST_ROOT / "index.html"
            if not target.is_file():
                return self._error("Arquivo não encontrado.", 404)
        data = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        self._headers(200, content_type, len(data))
        self.wfile.write(data)


def add_lesson_material(path: str, body: dict):
    match = re.fullmatch(r"/api/lessons/([A-Za-z0-9_-]+)/materials", path)
    if not match:
        return None
    lesson_id = match.group(1)
    title = clean_text(body.get("title"), "nome do material", 180)
    url = body.get("url")
    doc_id = body.get("document_id")
    if bool(url) == bool(doc_id):
        raise ValueError("Adicione um link ou selecione um PDF da biblioteca.")
    if url:
        from urllib.parse import urlparse
        url = clean_text(url, "link", 2000)
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Use um endereço HTTP ou HTTPS válido.")
    else:
        doc_id = clean_text(doc_id, "PDF", 100)
        with content_db() as source:
            doc = source.execute("SELECT arquivo_local FROM documentos WHERE documento_id=?", (doc_id,)).fetchone()
        if not doc or safe_library_file(doc["arquivo_local"]) is None:
            raise ValueError("O PDF não está disponível dentro da biblioteca local.")
    with study_db() as con:
        if con.execute("SELECT 1 FROM lessons WHERE lesson_id=?", (lesson_id,)).fetchone() is None:
            raise ValueError("Aula não encontrada.")
        pos = con.execute("SELECT coalesce(max(position),-1)+1 FROM materials WHERE lesson_id=?", (lesson_id,)).fetchone()[0]
        material_id = new_id("material")
        con.execute("INSERT INTO materials(material_id,lesson_id,title,url,document_id,position,created_at) VALUES(?,?,?,?,?,?,?)",
                    (material_id, lesson_id, title, url, doc_id, pos, iso(utc_now())))
        con.commit()
    return get_lesson(lesson_id)


def main():
    global PORT
    parser = argparse.ArgumentParser(description="Aplicativo local de estudo")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--host", default="127.0.0.1", help="Endereço de escuta (padrão: 127.0.0.1)")
    args = parser.parse_args()
    if not (1 <= args.port <= 65535):
        raise SystemExit("A porta deve estar entre 1 e 65535.")
    PORT = args.port
    init_db()
    try:
        content_db().close()
    except Exception as exc:
        raise SystemExit(f"Não foi possível abrir o banco de conteúdo em modo somente leitura: {exc}")
    server = StudyServer((args.host, PORT), Handler)
    print(f"Sistema de estudo disponível em http://127.0.0.1:{PORT}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
