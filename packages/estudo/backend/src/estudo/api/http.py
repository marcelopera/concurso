"""HTTP adapter and explicit route table for the local API."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlsplit

from estudo.errors import DomainError
from estudo.services import catalog, lessons, profiles, sessions
from estudo.services import plans as roadmap

ROUTES = (
    ("GET", re.compile("/api/health"), "get_health"),
    ("GET", re.compile("/api/bootstrap"), "get_bootstrap"),
    ("GET", re.compile("/api/catalog"), "get_catalog"),
    ("GET", re.compile("/api/exams"), "get_exams"),
    ("GET", re.compile("/api/exams/questions"), "get_exam_questions"),
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

    def __init__(self, address, app):
        self.app = app
        self.quiet = os.environ.get("ESTUDO_QUIET") == "1"
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    @property
    def app(self):
        return self.server.app

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
            profiles.database(self.app.settings.study_db, profile_id)
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
        if not self.app.settings.dist_root.is_dir():
            return self._error("A interface ainda não foi compilada. Execute pnpm run build.", 503)
        requested = unquote(path.lstrip("/")) or "index.html"
        try:
            target = (self.app.settings.dist_root / requested).resolve(strict=True)
            root = self.app.settings.dist_root.resolve()
            if not target.is_relative_to(root) or not target.is_file():
                raise FileNotFoundError
        except (OSError, ValueError, RuntimeError):
            target = self.app.settings.dist_root / "index.html"
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
        return self._json(catalog.health(self.app))

    def get_bootstrap(self, params, match, body):
        return self._json(self.app.bootstrap())

    def get_catalog(self, params, match, body):
        search = (params.get("search", [""])[0] or "").strip()
        bank = (params.get("bank", [""])[0] or "").strip()
        discipline = (params.get("discipline", [""])[0] or "").strip()
        eligible_only = (params.get("eligible_only", ["1"])[0] or "1").lower() not in ("0", "false", "no")
        page = max(1, min(100000, int(params.get("page", ["1"])[0])))
        return self._json(self.app.question_page(search, bank, discipline, page, eligible_only))

    def get_exams(self, params, match, body):
        return self._json({"items": catalog.exams(self.app)})

    def get_exam_questions(self, params, match, body):
        exam_id = (params.get("id", [""])[0] or "").strip()
        questions = catalog.exam_questions(self.app, exam_id)
        if questions is None:
            return self._error("Prova não encontrada.", 404)
        return self._json({"items": questions})

    def get_library(self, params, match, body):
        return self._json({"items": self.app.library_docs((params.get("search", [""])[0] or "").strip())})

    def get_library_file(self, params, match, body):
        doc_id = (params.get("document_id", [""])[0] or "").strip()
        path = catalog.library_file(self.app, doc_id)
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
        return self._json(sessions.due_cards(self.app))

    def get_attempts_history(self, params, match, body):
        return self._json(sessions.attempt_history(self.app))

    def get_lessons_id(self, params, match, body):
        lesson = self.app.get_lesson(match.group(1))
        if lesson is None:
            return self._error("Aula não encontrada.", 404)
        return self._json(lesson)

    def post_profiles(self, params, match, body):
        return self._json(profiles.create(self.app.settings.study_db, body.get("name")), 201)

    def post_roadmap_reset(self, params, match, body):
        return self._json(roadmap.reset(self.app, body))

    def post_topics(self, params, match, body):
        return self._json(lessons.create_topic(self.app, body), 201)

    def post_lessons(self, params, match, body):
        return self._json(lessons.create_lesson(self.app, body), 201)

    def post_lessons_id_sessions(self, params, match, body):
        result, created = sessions.start_session(self.app, match.group(1))
        return self._json(result, 201 if created else 200)

    def post_lessons_id_materials(self, params, match, body):
        return self._json(lessons.add_lesson_material(self.app, match.group(1), body), 201)

    def post_sessions_id_step(self, params, match, body):
        return self._json(sessions.change_step(self.app, match.group(1), body))

    def post_sessions_id_pause(self, params, match, body):
        return self._json(sessions.toggle_pause(self.app, match.group(1)))

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
        return self._json(roadmap.save_activity(self.app, match.group(1), body))

    def put_lessons_id(self, params, match, body):
        return self._json(lessons.update_lesson(self.app, match.group(1), body))

    def put_lessons_id_questions(self, params, match, body):
        return self._json(lessons.set_questions(self.app, match.group(1), body))

    def put_sessions_id_state(self, params, match, body):
        return self._json(sessions.save_state(self.app, match.group(1), body))

    def delete_materials_id(self, params, match, body):
        return self._json(lessons.delete_material(self.app, match.group(1)))
