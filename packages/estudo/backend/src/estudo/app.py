"""Composition root: an explicit application instance for each HTTP server or CLI."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock

from estudo.config import LOCAL_TZ, MAX_BODY, STEPS, Settings
from estudo.db.connections import open_catalog, open_study
from estudo.db.migrations import migrate
from estudo.domain import clean_text, iso, json_load, new_id, row_dict, safe_json, utc_now
from estudo.services import catalog, lessons, profiles, sessions


class Application:
    """Own runtime dependencies without binding services to a Python module."""

    STEPS = STEPS
    STEP_MINUTES = [step["minutes"] for step in STEPS]
    LOCAL_TZ = LOCAL_TZ
    MAX_BODY = MAX_BODY
    utc_now = staticmethod(utc_now)
    iso = staticmethod(iso)
    new_id = staticmethod(new_id)
    row_dict = staticmethod(row_dict)
    json_load = staticmethod(json_load)
    safe_json = staticmethod(safe_json)
    clean_text = staticmethod(clean_text)

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self._catalog_lock = Lock()

    def study_db(self) -> sqlite3.Connection:
        return open_study(profiles.database(self.settings.study_db, profiles.current.get()))

    def content_db(self) -> sqlite3.Connection:
        path = self.settings.content_db
        if path == self.settings.demo_content_db and not path.exists():
            from concurso_contracts.catalog.criar_demo import criar

            with self._catalog_lock:
                if not path.exists():
                    criar(path)
        return open_catalog(path)

    def init_db(self) -> None:
        with self.study_db() as con:
            migrate(con)

    def initialize(self) -> None:
        self.init_db()
        for profile in profiles.list_profiles(self.settings.study_db):
            token = profiles.current.set(profile["id"])
            try:
                self.init_db()
            finally:
                profiles.current.reset(token)
        self.content_db().close()

    def http_server(self, address):
        from estudo.api.http import StudyServer

        return StudyServer(address, self)

    def safe_library_file(self, path_value: str | None) -> Path | None:
        return catalog.safe_library_file(self, path_value)

    def content_question(self, occurrence_id: str, include_answer: bool = False) -> dict | None:
        return catalog.content_question(self, occurrence_id, include_answer)

    def question_for_client(self, item: dict, include_answer: bool = False) -> dict:
        return catalog.question_for_client(self, item, include_answer)

    def question_page(
        self, search: str, bank: str, discipline: str, page: int, eligible_only: bool = True, limit: int = 24
    ) -> dict:
        return catalog.question_page(self, search, bank, discipline, page, eligible_only, limit)

    def library_docs(self, search: str = "") -> list[dict]:
        return catalog.library_docs(self, search)

    def associated_snapshot(self, occurrence_id: str) -> dict:
        return catalog.associated_snapshot(self, occurrence_id)

    def get_lesson(self, lesson_id: str) -> dict | None:
        return lessons.get_lesson(self, lesson_id)

    def bootstrap(self) -> dict:
        return lessons.bootstrap(self)

    def add_lesson_material(self, lesson_id: str, body: dict):
        return lessons.add_lesson_material(self, lesson_id, body)

    def timer_state(self, session: dict) -> dict:
        return sessions.timer_state(self, session)

    def session_public(self, session: sqlite3.Row | dict) -> dict:
        return sessions.session_public(self, session)

    def answer_snapshot(
        self, occurrence_id: str, response: str, stage: str, help_used: bool = False, session_id: str | None = None
    ) -> dict:
        return sessions.answer_snapshot(self, occurrence_id, response, stage, help_used, session_id)
