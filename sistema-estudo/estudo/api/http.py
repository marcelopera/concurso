"""HTTP adapter and explicit route table for the local API."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlsplit

import profiles
import question_links
import roadmap
from estudo.errors import DomainError
from estudo.services import sessions

ROUTES = (
    ("GET", re.compile("/api/health"), "get_health"),
    ("GET", re.compile("/api/bootstrap"), "get_bootstrap"),
    ("GET", re.compile("/api/catalog"), "get_catalog"),
    ("GET", re.compile("/api/library"), "get_library"),
    ("GET", re.compile("/api/library/file"), "get_library_file"),
    ("GET", re.compile("/api/cards/due"), "get_cards_due"),
    ("GET", re.compile("/api/attempts/history"), "get_attempts_history"),
    ("GET", re.compile("/api/lessons/([A-Za-z0-9_-]+)"), "get_lessons_id"),
    ("POST", re.compile("/api/profiles"), "post_profiles"),
    ("POST", re.compile("/api/roadmap/reset"), "post_roadmap_reset"),
    ("POST", re.compile("/api/topics"), "post_topics"),
    ("POST", re.compile("/api/lessons"), "post_lessons"),
    ("POST", re.compile("/api/lessons/([A-Za-z0-9_-]+)/sessions"), "post_lessons_id_sessions"),
    ("POST", re.compile("/api/lessons/([A-Za-z0-9_-]+)/materials"), "post_lessons_id_materials"),
    ("POST", re.compile("/api/sessions/([A-Za-z0-9_-]+)/step"), "post_sessions_id_step"),
    ("POST", re.compile("/api/sessions/([A-Za-z0-9_-]+)/pause"), "post_sessions_id_pause"),
    ("POST", re.compile("/api/sessions/([A-Za-z0-9_-]+)/answer"), "post_sessions_id_answer"),
    ("POST", re.compile("/api/sessions/([A-Za-z0-9_-]+)/complete"), "post_sessions_id_complete"),
    ("POST", re.compile("/api/attempts"), "post_attempts"),
    ("POST", re.compile("/api/cards/([A-Za-z0-9_-]+)/review"), "post_cards_id_review"),
    ("PUT", re.compile("/api/roadmap/activities/([A-Za-z0-9_-]+)"), "put_roadmap_activities_id"),
    ("PUT", re.compile("/api/lessons/([A-Za-z0-9_-]+)"), "put_lessons_id"),
    ("PUT", re.compile("/api/lessons/([A-Za-z0-9_-]+)/questions"), "put_lessons_id_questions"),
    ("PUT", re.compile("/api/sessions/([A-Za-z0-9_-]+)/state"), "put_sessions_id_state"),
    ("DELETE", re.compile("/api/materials/([A-Za-z0-9_-]+)"), "delete_materials_id"),
)


class StudyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    quiet = os.environ.get("ESTUDO_QUIET") == "1"


class Handler(BaseHTTPRequestHandler):
    app = None
    server_version = "EstudoLocal/1.0"
    sys_version = ""

    def handle_one_request(self):
        token = profiles.current.set("principal")
        try:
            super().handle_one_request()
        finally:
            profiles.current.reset(token)

    def log_message(self, fmt, *args):
        if not self.server.quiet:
            sys.stdout.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    def _headers(self, status: int, content_type: str, length: int | None = None, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store" if content_type.startswith("application/json") else "no-cache")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: blob:; font-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; worker-src 'self' blob:; frame-src 'self'; object-src 'self'; base-uri 'self'; form-action 'self'",
        )
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
        allowed_hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        host = self.headers.get("Host", "").lower()
        if host not in allowed_hosts:
            self._error("A API aceita apenas o endereço local do aplicativo.", 403)
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {
            f"http://127.0.0.1:{self.server.server_port}",
            f"http://localhost:{self.server.server_port}",
        }:
            self._error("Origem não autorizada.", 403)
            return False
        profile_id = self.headers.get("X-Study-Profile", "principal")
        try:
            profiles.database(self.app.STUDY_DB, profile_id)
        except ValueError as exc:
            self._error(str(exc), 404)
            return False
        profiles.current.set(profile_id)
        return True

    def _body(self) -> dict:
        size = int(self.headers.get("Content-Length", "0"))
        if size < 0 or size > self.app.MAX_BODY:
            raise ValueError("A solicitação excede o limite permitido.")
        raw = self.rfile.read(size)
        try:
            value = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("JSON inválido.")
        if not isinstance(value, dict):
            raise ValueError("O corpo da solicitação deve ser um objeto JSON.")
        return value

    def _static(self, path: str):
        if not self.app.DIST_ROOT.is_dir():
            return self._error("A interface ainda não foi compilada. Execute pnpm run build.", 503)
        requested = unquote(path.lstrip("/")) or "index.html"
        try:
            target = (self.app.DIST_ROOT / requested).resolve(strict=True)
            root = self.app.DIST_ROOT.resolve()
            if not target.is_relative_to(root) or not target.is_file():
                raise FileNotFoundError
        except (OSError, ValueError, RuntimeError):
            target = self.app.DIST_ROOT / "index.html"
            if not target.is_file():
                return self._error("Arquivo não encontrado.", 404)
        data = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        self._headers(200, content_type, len(data))
        self.wfile.write(data)

    def _dispatch(self):
        try:
            parsed = urlsplit(self.path)
            if not parsed.path.startswith("/api/"):
                if self.command == "GET":
                    return self._static(parsed.path)
                return self._error("Rota não encontrada.", 404)
            if not self._check_local_origin():
                return
            allowed = set()
            for verb, pattern, name in ROUTES:
                match = pattern.fullmatch(parsed.path)
                if match is None:
                    continue
                allowed.add(verb)
                if verb == self.command:
                    body = self._body() if verb in ("POST", "PUT") else {}
                    return getattr(self, name)(parse_qs(parsed.query), match, body)
            if allowed:
                raw = json.dumps({"error": "Método não permitido."}).encode("utf-8")
                self._headers(405, "application/json; charset=utf-8", len(raw), {"Allow": ", ".join(sorted(allowed))})
                return self.wfile.write(raw)
            return self._error("Rota não encontrada.", 404)
        except DomainError as exc:
            return self._error(str(exc), exc.status)
        except ValueError as exc:
            return self._error(str(exc), 400)
        except sqlite3.IntegrityError:
            return self._error("Não foi possível salvar devido a um conflito de dados.", 409)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            self.log_error("Erro interno: %r", exc)
            return self._error("Erro interno do servidor.", 500)

    do_GET = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_DELETE = _dispatch

    def get_health(self, params, match, body):
        with self.app.content_db() as con:
            count = con.execute("SELECT count(*) FROM ocorrencias").fetchone()[0]
        return self._json({"ok": True, "content_occurrences": count})

    def get_bootstrap(self, params, match, body):
        return self._json(self.app.bootstrap())

    def get_catalog(self, params, match, body):
        search = (params.get("search", [""])[0] or "").strip()
        bank = (params.get("bank", [""])[0] or "").strip()
        discipline = (params.get("discipline", [""])[0] or "").strip()
        eligible_only = (params.get("eligible_only", ["1"])[0] or "1").lower() not in ("0", "false", "no")
        page = max(1, min(100000, int(params.get("page", ["1"])[0])))
        return self._json(self.app.question_page(search, bank, discipline, page, eligible_only))

    def get_library(self, params, match, body):
        return self._json({"items": self.app.library_docs((params.get("search", [""])[0] or "").strip())})

    def get_library_file(self, params, match, body):
        doc_id = (params.get("document_id", [""])[0] or "").strip()
        with self.app.content_db() as con:
            row = con.execute("SELECT arquivo_local,nome FROM documentos WHERE documento_id=?", (doc_id,)).fetchone()
        path = self.app.safe_library_file(row["arquivo_local"] if row else None)
        if path is None:
            return self._error("PDF não encontrado na biblioteca local.", 404)
        size = path.stat().st_size
        start, end = (0, size - 1)
        range_header = self.headers.get("Range")
        if range_header:
            match = re.fullmatch("bytes=(\\d*)-(\\d*)", range_header.strip())
            if not match or not any(match.groups()) or size == 0:
                self._headers(416, "application/pdf", 0, {"Content-Range": f"bytes */{size}"})
                return
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last), end) if last else end
            else:
                suffix = int(last)
                start = max(0, size - suffix)
            if start >= size or start > end:
                self._headers(416, "application/pdf", 0, {"Content-Range": f"bytes */{size}"})
                return
        length = max(0, end - start + 1)
        headers = {"Content-Disposition": "inline; filename*=UTF-8''" + quote(path.name), "Accept-Ranges": "bytes"}
        if range_header:
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        self._headers(206 if range_header else 200, "application/pdf", length, headers)
        with path.open("rb") as source:
            source.seek(start)
            remaining = length
            while remaining:
                chunk = source.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)
        return

    def get_cards_due(self, params, match, body):
        day = datetime.now(self.app.LOCAL_TZ).date().isoformat()
        with self.app.study_db() as con:
            cards = [
                dict(r)
                for r in con.execute(
                    "SELECT c.*,t.title AS topic_title,s.name AS subject_name FROM cards c JOIN topics t USING(topic_id) JOIN subjects s USING(subject_id) WHERE c.active=1 AND c.due_date<=? ORDER BY c.due_date,c.created_at LIMIT 80",
                    (day,),
                )
            ]
        return self._json({"items": cards, "today": day})

    def get_attempts_history(self, params, match, body):
        with self.app.study_db() as con:
            rows = [
                dict(r)
                for r in con.execute(
                    "SELECT attempt_id,stage,occurrence_id,answer,help_used,reference_snapshot,correct,created_at FROM attempts WHERE session_id IS NULL ORDER BY created_at DESC LIMIT 100"
                )
            ]
        for r in rows:
            r["reference_snapshot"] = self.app.json_load(r["reference_snapshot"], {})
        return self._json({"items": rows})

    def get_lessons_id(self, params, match, body):
        lesson = self.app.get_lesson(match.group(1))
        if lesson is None:
            return self._error("Aula não encontrada.", 404)
        return self._json(lesson)

    def post_profiles(self, params, match, body):
        return self._json(profiles.create(self.app.STUDY_DB, body.get("name")), 201)

    def post_roadmap_reset(self, params, match, body):
        if body.get("confirm") != profiles.current.get():
            return self._error("Confirme o perfil para resetar o roadmap.")
        with self.app.study_db() as con:
            result = profiles.reset_roadmap(con, profiles.database(self.app.STUDY_DB, profiles.current.get()))
            con.commit()
        return self._json(result)

    def post_topics(self, params, match, body):
        subject_name = self.app.clean_text(body.get("subject"), "disciplina", 100)
        title = self.app.clean_text(body.get("title"), "tópico", 180)
        with self.app.study_db() as con:
            subject = con.execute(
                "SELECT subject_id FROM subjects WHERE name=? COLLATE NOCASE", (subject_name,)
            ).fetchone()
            subject_id = subject[0] if subject else self.app.new_id("subject")
            now = self.app.iso(self.app.utc_now())
            if not subject:
                con.execute(
                    "INSERT INTO subjects(subject_id,name,created_at) VALUES(?,?,?)", (subject_id, subject_name, now)
                )
            topic_id = self.app.new_id("topic")
            pos = con.execute(
                "SELECT coalesce(max(position),-1)+1 FROM topics WHERE subject_id=?", (subject_id,)
            ).fetchone()[0]
            con.execute(
                "INSERT INTO topics(topic_id,subject_id,title,position,created_at) VALUES(?,?,?,?,?)",
                (topic_id, subject_id, title, pos, now),
            )
            con.commit()
        return self._json({"id": topic_id, "subject_id": subject_id, "title": title}, 201)

    def post_lessons(self, params, match, body):
        topic_id = self.app.clean_text(body.get("topic_id"), "tópico", 100)
        title = self.app.clean_text(body.get("title"), "aula", 180)
        with self.app.study_db() as con:
            if con.execute("SELECT 1 FROM topics WHERE topic_id=?", (topic_id,)).fetchone() is None:
                return self._error("Tópico não encontrado.", 404)
            lesson_id = self.app.new_id("lesson")
            con.execute(
                "INSERT INTO lessons(lesson_id,topic_id,title,created_at) VALUES(?,?,?,?)",
                (lesson_id, topic_id, title, self.app.iso(self.app.utc_now())),
            )
            con.commit()
        return self._json({"id": lesson_id, "title": title}, 201)

    def post_lessons_id_sessions(self, params, match, body):
        lesson_id = match.group(1)
        with self.app.study_db() as con:
            con.execute("BEGIN IMMEDIATE")
            if con.execute("SELECT 1 FROM lessons WHERE lesson_id=?", (lesson_id,)).fetchone() is None:
                return self._error("Aula não encontrada.", 404)
            active = con.execute(
                "SELECT * FROM study_sessions WHERE status='active' AND lesson_id=? ORDER BY updated_at DESC LIMIT 1",
                (lesson_id,),
            ).fetchone()
            if active:
                return self._json(self.app.session_public(active))
            session_id = self.app.new_id("session")
            now = self.app.utc_now()
            deadline = now + timedelta(minutes=self.app.STEP_MINUTES[0])
            with self.app.content_db() as content:
                initial_payload = question_links.session_pool(con, content, lesson_id)
            previous = con.execute(
                "SELECT payload FROM study_sessions WHERE lesson_id=? AND status='completed' "
                "ORDER BY completed_at DESC, rowid DESC LIMIT 1",
                (lesson_id,),
            ).fetchone()
            if previous:
                previous_payload = self.app.json_load(previous["payload"], {})
                if isinstance(previous_payload, dict) and isinstance(previous_payload.get("boardScene"), dict):
                    initial_payload["boardScene"] = previous_payload["boardScene"]
            con.execute(
                "INSERT INTO study_sessions(session_id,lesson_id,status,current_step,deadline_at,payload,started_at,updated_at) VALUES(?,?,'active',0,?,?,?,?)",
                (
                    session_id,
                    lesson_id,
                    self.app.iso(deadline),
                    self.app.safe_json(initial_payload),
                    self.app.iso(now),
                    self.app.iso(now),
                ),
            )
            con.commit()
            row = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (session_id,)).fetchone()
        return self._json(self.app.session_public(row), 201)

    def post_lessons_id_materials(self, params, match, body):
        path = urlsplit(self.path).path
        return self._json(self.app.add_lesson_material(path, body), 201)

    def post_sessions_id_step(self, params, match, body):
        step = body.get("step")
        if type(step) is not int or not 0 <= step < len(self.app.STEPS):
            return self._error("Etapa inválida.")
        with self.app.study_db() as con:
            row = con.execute(
                "SELECT * FROM study_sessions WHERE session_id=? AND status='active'", (match.group(1),)
            ).fetchone()
            if row is None:
                return self._error("Sessão ativa não encontrada.", 404)
            now = self.app.utc_now()
            con.execute(
                "UPDATE study_sessions SET current_step=?,deadline_at=?,paused_remaining=NULL,updated_at=? WHERE session_id=?",
                (
                    step,
                    self.app.iso(now + timedelta(minutes=self.app.STEP_MINUTES[step])),
                    self.app.iso(now),
                    match.group(1),
                ),
            )
            con.commit()
            updated = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (match.group(1),)).fetchone()
        return self._json(self.app.session_public(updated))

    def post_sessions_id_pause(self, params, match, body):
        with self.app.study_db() as con:
            row = con.execute(
                "SELECT * FROM study_sessions WHERE session_id=? AND status='active'", (match.group(1),)
            ).fetchone()
            if row is None:
                return self._error("Sessão ativa não encontrada.", 404)
            if row["paused_remaining"] is None:
                remaining = (
                    max(0, int((datetime.fromisoformat(row["deadline_at"]) - self.app.utc_now()).total_seconds()))
                    if row["deadline_at"]
                    else 0
                )
                con.execute(
                    "UPDATE study_sessions SET deadline_at=NULL,paused_remaining=?,updated_at=? WHERE session_id=?",
                    (remaining, self.app.iso(self.app.utc_now()), match.group(1)),
                )
            else:
                remaining = max(0, int(row["paused_remaining"]))
                con.execute(
                    "UPDATE study_sessions SET deadline_at=?,paused_remaining=NULL,updated_at=? WHERE session_id=?",
                    (
                        self.app.iso(self.app.utc_now() + timedelta(seconds=remaining)),
                        self.app.iso(self.app.utc_now()),
                        match.group(1),
                    ),
                )
            con.commit()
            updated = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (match.group(1),)).fetchone()
        return self._json(self.app.session_public(updated))

    def post_sessions_id_answer(self, params, match, body):
        stage = body.get("stage")
        if stage not in ("recall", "pretest", "practice"):
            return self._error("Etapa de resposta inválida.")
        result = self.app.answer_snapshot(
            self.app.clean_text(body.get("occurrence_id"), "questão", 100),
            self.app.clean_text(body.get("answer"), "resposta", 4000),
            stage,
            bool(body.get("help_used", False)),
            match.group(1),
        )
        return self._json(result, 201)

    def post_sessions_id_complete(self, params, match, body):
        return self._json(sessions.complete_session(self.app, match.group(1), body))

    def post_attempts(self, params, match, body):
        result = self.app.answer_snapshot(
            self.app.clean_text(body.get("occurrence_id"), "questão", 100),
            self.app.clean_text(body.get("answer"), "resposta", 4000),
            "free",
            bool(body.get("help_used", False)),
        )
        return self._json(result, 201)

    def post_cards_id_review(self, params, match, body):
        return self._json(sessions.review_card(self.app, match.group(1), body))

    def put_roadmap_activities_id(self, params, match, body):
        with self.app.study_db() as con:
            result = roadmap.update_activity(con, match.group(1), body)
            con.commit()
        return self._json(result)

    def put_lessons_id(self, params, match, body):
        lesson_id = match.group(1)
        title = self.app.clean_text(body.get("title"), "aula", 180)
        reference = body.get("reference_scene", ...)
        encoded = None if reference is None else self.app.safe_json(reference, 8000000) if reference is not ... else ...
        with self.app.study_db() as con:
            if encoded is ...:
                cur = con.execute("UPDATE lessons SET title=? WHERE lesson_id=?", (title, lesson_id))
            else:
                cur = con.execute(
                    "UPDATE lessons SET title=?,reference_scene=? WHERE lesson_id=?", (title, encoded, lesson_id)
                )
            if not cur.rowcount:
                return self._error("Aula não encontrada.", 404)
            con.commit()
        return self._json(self.app.get_lesson(lesson_id))

    def put_lessons_id_questions(self, params, match, body):
        lesson_id = match.group(1)
        ids = body.get("occurrence_ids")
        if not isinstance(ids, list) or len(ids) > 3000:
            return self._error("Selecione até 3000 questões.")
        ids = list(dict.fromkeys((self.app.clean_text(x, "questão", 100) for x in ids)))
        with self.app.content_db() as content:
            valid_ids = {q["ocorrencia_id"] for q in question_links.content_items(content, ids)}
        if len(valid_ids) != len(ids):
            return self._error("Uma ou mais questões não foram encontradas na base.", 404)
        with self.app.study_db() as con:
            if con.execute("SELECT 1 FROM lessons WHERE lesson_id=?", (lesson_id,)).fetchone() is None:
                return self._error("Aula não encontrada.", 404)
            old_ids = {
                r[0] for r in con.execute("SELECT occurrence_id FROM lesson_questions WHERE lesson_id=?", (lesson_id,))
            }
            con.executemany(
                "DELETE FROM lesson_questions WHERE lesson_id=? AND occurrence_id=?",
                [(lesson_id, occ) for occ in old_ids - set(ids)],
            )
            con.executemany(
                "INSERT INTO lesson_questions(lesson_id,occurrence_id,position) VALUES(?,?,?) ON CONFLICT(lesson_id,occurrence_id) DO UPDATE SET position=excluded.position",
                [(lesson_id, occ, i) for i, occ in enumerate(ids)],
            )
            con.commit()
        return self._json(self.app.get_lesson(lesson_id))

    def put_sessions_id_state(self, params, match, body):
        payload = body.get("payload")
        if not isinstance(payload, dict):
            return self._error("Estado da sessão inválido.")
        encoded = self.app.safe_json(payload, 20000000)
        now = self.app.iso(self.app.utc_now())
        with self.app.study_db() as con:
            cur = con.execute(
                "UPDATE study_sessions SET payload=?,updated_at=? WHERE session_id=? AND status='active'",
                (encoded, now, match.group(1)),
            )
            if not cur.rowcount:
                return self._error("Sessão ativa não encontrada.", 404)
            con.commit()
            updated = con.execute("SELECT * FROM study_sessions WHERE session_id=?", (match.group(1),)).fetchone()
        return self._json(self.app.session_public(updated))

    def delete_materials_id(self, params, match, body):
        with self.app.study_db() as con:
            cur = con.execute("DELETE FROM materials WHERE material_id=?", (match.group(1),))
            con.commit()
        if not cur.rowcount:
            return self._error("Material não encontrado.", 404)
        return self._json({"ok": True})
