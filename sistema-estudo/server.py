from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import profiles
from estudo.api.http import Handler as BaseHandler
from estudo.api.http import StudyServer
from estudo.config import (
    CONTENT_DB,
    DEMO_CONTENT_DB,
    PORT,
    STEPS,
    STUDY_DB,
)
from estudo.config import (
    DIST_ROOT as DIST_ROOT,
)
from estudo.config import (
    LIBRARY_ROOT as LIBRARY_ROOT,
)
from estudo.config import (
    LOCAL_TZ as LOCAL_TZ,
)
from estudo.config import (
    MAX_BODY as MAX_BODY,
)
from estudo.db.connections import open_catalog, open_study
from estudo.db.migrations import migrate
from estudo.services import catalog, lessons, sessions

STEP_MINUTES = [step["minutes"] for step in STEPS]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds") if value else None


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def study_db() -> sqlite3.Connection:
    return open_study(profiles.database(STUDY_DB, profiles.current.get()))


def content_db() -> sqlite3.Connection:
    if CONTENT_DB == DEMO_CONTENT_DB.resolve() and not CONTENT_DB.exists():
        from catalogo.criar_demo import criar

        criar(CONTENT_DB)
    return open_catalog(CONTENT_DB)


def init_db() -> None:
    with study_db() as con:
        migrate(con)


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


def main():
    parser = argparse.ArgumentParser(description="Aplicativo local de estudo")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--host", default="127.0.0.1", help="Endereço de escuta (padrão: 127.0.0.1)")
    args = parser.parse_args()
    if not (1 <= args.port <= 65535):
        raise SystemExit("A porta deve estar entre 1 e 65535.")
    init_db()
    for profile in profiles.list_profiles(STUDY_DB):
        if profile["id"] == "principal":
            continue
        token = profiles.current.set(profile["id"])
        try:
            init_db()
        finally:
            profiles.current.reset(token)
    try:
        content_db().close()
    except Exception as exc:
        raise SystemExit(f"Não foi possível abrir o banco de conteúdo em modo somente leitura: {exc}")
    server = StudyServer((args.host, args.port), Handler)
    print(f"Sistema de estudo disponível em http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def safe_library_file(path_value: str | None) -> Path | None:
    return catalog.safe_library_file(_app, path_value)


def content_question(occurrence_id: str, include_answer: bool = False) -> dict | None:
    return catalog.content_question(_app, occurrence_id, include_answer)


def question_for_client(item: dict, include_answer: bool = False) -> dict:
    return catalog.question_for_client(_app, item, include_answer)


def question_page(
    search: str, bank: str, discipline: str, page: int, eligible_only: bool = True, limit: int = 24
) -> dict:
    return catalog.question_page(_app, search, bank, discipline, page, eligible_only, limit)


def library_docs(search: str = "") -> list[dict]:
    return catalog.library_docs(_app, search)


def associated_snapshot(occurrence_id: str) -> dict:
    return catalog.associated_snapshot(_app, occurrence_id)


def get_lesson(lesson_id: str) -> dict | None:
    return lessons.get_lesson(_app, lesson_id)


def bootstrap() -> dict:
    return lessons.bootstrap(_app)


def add_lesson_material(path: str, body: dict):
    return lessons.add_lesson_material(_app, path, body)


def timer_state(session: dict) -> dict:
    return sessions.timer_state(_app, session)


def session_public(session: sqlite3.Row | dict) -> dict:
    return sessions.session_public(_app, session)


def answer_snapshot(
    occurrence_id: str, response: str, stage: str, help_used: bool = False, session_id: str | None = None
) -> dict:
    return sessions.answer_snapshot(_app, occurrence_id, response, stage, help_used, session_id)


_app = sys.modules[__name__]


class Handler(BaseHandler):
    """Bind HTTP handlers to the application dependencies."""

    app = _app


if __name__ == "__main__":
    main()
