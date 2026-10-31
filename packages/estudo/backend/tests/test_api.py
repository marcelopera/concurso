"""Business and HTTP regressions using only synthetic, temporary data."""

import hashlib
import json
import shutil
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from estudo.app import Application

server = Application()
from concurso_contracts.catalog.criar_demo import criar


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.original = server.settings.study_db, server.settings.content_db
        server.settings.study_db, server.settings.content_db = self.root / "study.sqlite", self.root / "catalog.sqlite"
        criar(server.settings.content_db)
        self.catalog_hash = hashlib.sha256(server.settings.content_db.read_bytes()).hexdigest()
        server.init_db()
        with server.study_db() as con:
            con.execute("INSERT INTO subjects VALUES('subject','Disciplina','old')")
            con.execute("INSERT INTO topics VALUES('topic','subject','Tópico',0,'old')")
            con.execute(
                "INSERT INTO lessons(lesson_id,topic_id,title,created_at) VALUES('lesson','topic','Aula','old')"
            )
            con.executemany("INSERT INTO lesson_questions VALUES('lesson',?,?)", [("o1", 0), ("o2", 1), ("o3", 2)])
        self.http = server.http_server(("127.0.0.1", 0))
        self.http.quiet = True
        self.url = f"http://127.0.0.1:{self.http.server_port}"
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.assertEqual(hashlib.sha256(server.settings.content_db.read_bytes()).hexdigest(), self.catalog_hash)
        server.settings.study_db, server.settings.content_db = self.original
        self.tmp.cleanup()

    def request(self, path, method="GET", body=None, headers=None, raw=None):
        data = raw if raw is not None else json.dumps(body).encode() if body is not None else None
        request = Request(
            self.url + path,
            method=method,
            data=data,
            headers={"Origin": self.url, "Content-Type": "application/json", **(headers or {})},
        )
        try:
            response = urlopen(request)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, json.load(response), response.headers

    def start(self):
        status, result, _ = self.request("/api/lessons/lesson/sessions", "POST", {})
        self.assertEqual(status, 201)
        return result["session_id"]

    def test_catalog_hides_answers_and_attempts_store_immutable_snapshots(self):
        status, page, _ = self.request("/api/catalog")
        self.assertEqual(status, 200)
        self.assertNotIn("reference_answer", page["items"][0])
        self.assertNotIn("resposta_referencia", page["items"][0])
        for answer, correct in [("A", True), ("B", False)]:
            status, result, _ = self.request("/api/attempts", "POST", {"occurrence_id": "o1", "answer": answer})
            self.assertEqual(status, 201)
            self.assertIs(result["correct"], correct)
            self.assertEqual(result["snapshot"]["reference_answer"], "A")
        _, history, _ = self.request("/api/attempts/history")
        self.assertEqual(len(history["items"]), 2)
        self.assertTrue(all(item["reference_snapshot"]["auto_graded"] for item in history["items"]))

    def test_exams_list_and_questions_hide_answers(self):
        status, data, _ = self.request("/api/exams")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["items"]), 20)
        exam = next(item for item in data["items"] if item["id"] == "p1")
        self.assertEqual(exam["question_count"], 1)
        status, questions, _ = self.request("/api/exams/questions?id=p1")
        self.assertEqual(status, 200)
        self.assertEqual([item["occurrence_id"] for item in questions["items"]], ["o1"])
        self.assertNotIn("reference_answer", questions["items"][0])
        self.assertNotIn("source_answers", questions["items"][0])
        self.assertEqual(self.request("/api/exams/questions?id=unknown")[0], 404)

    def test_uncorrectable_question_does_not_get_a_grade(self):
        # A read-only adapter supplies an unreviewed extraction without changing the catalog.
        original = server.content_question

        def unreviewed(*args, **kwargs):
            item = original(*args, **kwargs)
            item["status_extracao"] = "precisa_revisao"
            item["reference_status"]["correctable"] = False
            return item

        with patch.object(server, "content_question", side_effect=unreviewed):
            status, result, _ = self.request("/api/attempts", "POST", {"occurrence_id": "o1", "answer": "A"})
        self.assertEqual(status, 201)
        self.assertIsNone(result["correct"])
        self.assertFalse(result["snapshot"]["auto_graded"])

    def test_session_state_pause_and_link_validation(self):
        session = self.start()
        prefix = "/api/sessions/" + session
        status, _, _ = self.request(
            prefix + "/answer", "POST", {"stage": "practice", "occurrence_id": "o4", "answer": "A"}
        )
        self.assertEqual(status, 400)
        status, saved, _ = self.request(prefix + "/state", "PUT", {"payload": {"recallText": "Persistente"}})
        self.assertEqual(status, 200)
        self.assertEqual(saved["payload"]["recallText"], "Persistente")
        _, paused, _ = self.request(prefix + "/pause", "POST", {})
        self.assertTrue(paused["timer"]["paused"])
        _, resumed, _ = self.request(prefix + "/pause", "POST", {})
        self.assertFalse(resumed["timer"]["paused"])
        self.assertEqual(self.request(prefix + "/step", "POST", {"step": 100})[0], 400)
        self.assertEqual(self.request(prefix + "/step", "POST", {"step": True})[0], 400)

    def test_multiple_lessons_keep_independent_pending_sessions(self):
        first = self.start()
        self.request(f"/api/sessions/{first}/state", "PUT", {"payload": {"recallText": "Primeira aula"}})
        self.request(f"/api/sessions/{first}/step", "POST", {"step": 2})
        status, lesson, _ = self.request("/api/lessons", "POST", {"topic_id": "topic", "title": "Outra aula"})
        self.assertEqual(status, 201)
        path = f"/api/lessons/{lesson['id']}/sessions"
        status, second, _ = self.request(path, "POST", {})
        self.assertEqual(status, 201)
        self.assertNotEqual(first, second["session_id"])
        self.request(f"/api/sessions/{second['session_id']}/state", "PUT", {"payload": {"recallText": "Segunda aula"}})

        status, resumed, _ = self.request("/api/lessons/lesson/sessions", "POST", {})
        self.assertEqual(status, 200)
        self.assertEqual(resumed["session_id"], first)
        self.assertEqual(resumed["current_step"], 2)
        self.assertEqual(resumed["payload"]["recallText"], "Primeira aula")
        _, bootstrap, _ = self.request("/api/bootstrap")
        sessions = {item["session_id"]: item for item in bootstrap["active_sessions"]}
        self.assertEqual(set(sessions), {first, second["session_id"]})
        self.assertEqual(sessions[second["session_id"]]["payload"]["recallText"], "Segunda aula")

        self.request(f"/api/sessions/{first}/complete", "POST", {})
        _, bootstrap, _ = self.request("/api/bootstrap")
        self.assertEqual([item["session_id"] for item in bootstrap["active_sessions"]], [second["session_id"]])
        self.assertEqual(self.request(path, "POST", {})[1]["session_id"], second["session_id"])

    def test_completion_is_idempotent_and_reviews_follow_the_schedule(self):
        session = self.start()
        body = {"cards": [{"selected": True, "front": "Pergunta", "back": "Resposta"}], "difficulties": ["Dúvida"]}
        for _ in range(2):
            self.assertEqual(self.request("/api/sessions/" + session + "/complete", "POST", body)[0], 200)
        with server.study_db() as con:
            cards = con.execute("SELECT * FROM cards").fetchall()
            self.assertEqual(len(cards), 1)
            self.assertEqual(con.execute("SELECT count(*) FROM lesson_difficulties").fetchone()[0], 1)
            card_id = cards[0]["card_id"]
        for rating, interval in [("facil", 3), ("facil", 7), ("dificil", 7), ("errei", 1)]:
            status, result, _ = self.request("/api/cards/" + card_id + "/review", "POST", {"rating": rating})
            self.assertEqual(status, 200)
            self.assertEqual(result["interval_after"], interval)
            self.assertEqual(
                result["due_date"], (datetime.now(server.LOCAL_TZ).date() + timedelta(days=interval)).isoformat()
            )
        with server.study_db() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM card_reviews").fetchone()[0], 4)

    def test_new_session_restores_latest_completed_lesson_board(self):
        session = self.start()
        scene = {"elements": [{"id": "drawing", "type": "rectangle"}], "appState": {}, "files": {}}
        payload = {"boardScene": scene, "recallText": "Não copiar outras respostas"}
        self.assertEqual(self.request(f"/api/sessions/{session}/state", "PUT", {"payload": payload})[0], 200)
        _, resumed, _ = self.request("/api/lessons/lesson/sessions", "POST", {})
        self.assertEqual(resumed["payload"]["boardScene"], scene)
        self.assertEqual(self.request(f"/api/sessions/{session}/complete", "POST", {})[0], 200)

        status, reopened, _ = self.request("/api/lessons/lesson/sessions", "POST", {})
        self.assertEqual(status, 201)
        self.assertEqual(reopened["payload"]["boardScene"], scene)
        self.assertNotIn("recallText", reopened["payload"])

        empty = {"elements": [], "appState": {}, "files": {}}
        new_id = reopened["session_id"]
        self.request(f"/api/sessions/{new_id}/state", "PUT", {"payload": {"boardScene": empty}})
        self.request(f"/api/sessions/{new_id}/complete", "POST", {})
        _, reopened_again, _ = self.request("/api/lessons/lesson/sessions", "POST", {})
        self.assertEqual(reopened_again["payload"]["boardScene"], empty)

    def test_errors_are_consistent_and_unknown_api_paths_are_not_html(self):
        self.assertEqual(self.request("/api/missing")[0], 404)
        status, _, headers = self.request("/api/catalog", "DELETE")
        self.assertEqual(status, 405)
        self.assertEqual(headers["Allow"], "GET")
        self.assertEqual(self.request("/api/catalog?page=abc")[0], 400)
        self.assertEqual(self.request("/api/topics", "POST", raw=b"[]")[0], 400)
        self.assertEqual(self.request("/api/topics", "POST", raw=b"{")[0], 400)
        self.assertEqual(self.request("/api/bootstrap", headers={"Origin": "https://untrusted.invalid"})[0], 403)
        for profile_id in ("../outside", "..\\outside", "a" * 32):
            self.assertEqual(self.request("/api/bootstrap", headers={"X-Study-Profile": profile_id})[0], 404)
        with patch.object(server, "content_db", side_effect=sqlite3.OperationalError("private database details")):
            for path, method, body in [
                ("/api/health", "GET", None),
                ("/api/attempts", "POST", {"occurrence_id": "o1", "answer": "A"}),
            ]:
                status, result, _ = self.request(path, method, body)
                self.assertEqual(status, 500)
                self.assertEqual(result, {"error": "Erro interno do servidor."})

    def test_catalog_rejects_future_broken_and_inconsistent_schemas(self):
        from estudo.db.connections import open_catalog

        for case in ("future", "missing", "metadata", "metadata_missing", "source_hash", "execution_metadata"):
            destination = self.root / (case + ".sqlite")
            criar(destination)
            with closing(sqlite3.connect(destination)) as con, con:
                if case == "future":
                    con.execute("PRAGMA user_version=99")
                elif case == "missing":
                    con.execute("ALTER TABLE alternativas RENAME COLUMN rotulo TO broken")
                else:
                    if case == "metadata":
                        con.execute("UPDATE schema_meta SET versao=1")
                    elif case == "metadata_missing":
                        con.execute("DROP TABLE schema_meta")
                        con.execute("CREATE TABLE schema_meta(versao INTEGER NOT NULL)")
                        con.execute("INSERT INTO schema_meta VALUES(2)")
                    elif case == "source_hash":
                        con.execute("UPDATE schema_meta SET hash_fontes=?", ("0" * 64,))
                    else:
                        con.execute("UPDATE execucoes SET metadados_json='{}'")
            with self.assertRaises(RuntimeError):
                open_catalog(destination)
        with self.assertRaises(sqlite3.OperationalError):
            with open_catalog(server.settings.content_db) as con:
                con.execute("DELETE FROM questoes")

    def test_legacy_catalog_versions_open_read_only(self):
        from estudo.db.connections import open_catalog

        for version in (0, 1):
            destination = self.root / f"legacy-v{version}.sqlite"
            shutil.copyfile(server.settings.content_db, destination)
            with closing(sqlite3.connect(destination)) as con, con:
                con.execute("DROP TABLE schema_meta")
                if version == 1:
                    con.execute("CREATE TABLE schema_meta(versao INTEGER NOT NULL)")
                    con.execute("INSERT INTO schema_meta VALUES(1)")
                con.execute(f"PRAGMA user_version={version}")
            before = destination.read_bytes()
            with open_catalog(destination) as con:
                self.assertEqual(con.execute("SELECT count(*) FROM questoes").fetchone()[0], 20)
                with self.assertRaises(sqlite3.OperationalError):
                    con.execute("DELETE FROM questoes")
            self.assertEqual(destination.read_bytes(), before)
