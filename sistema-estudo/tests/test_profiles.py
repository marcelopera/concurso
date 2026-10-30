"""Profile isolation and scoped reset through the real HTTP API, on temporary data."""

import contextlib
import gc
import io
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import roadmap
import server


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.original_db, self.original_port = server.STUDY_DB, server.PORT
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        server.STUDY_DB = Path(self.temp.name) / "study.sqlite"
        server.init_db()
        with contextlib.redirect_stdout(io.StringIO()):
            roadmap.install(server.STUDY_DB)
        self.http = server.StudyServer(("127.0.0.1", 0), server.Handler)
        server.PORT = self.http.server_address[1]
        self.url = "http://127.0.0.1:" + str(server.PORT)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        server.STUDY_DB, server.PORT = self.original_db, self.original_port
        gc.collect()
        self.temp.cleanup()

    def request(self, path="/api/bootstrap", method="GET", body=None, profile="principal"):
        req = Request(
            self.url + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json", "Origin": self.url, "X-Study-Profile": profile},
        )
        with urlopen(req) as response:
            return json.load(response)

    def test_existing_progress_and_independent_persistent_profiles(self):
        with server.study_db() as con:
            con.execute("UPDATE lessons SET completed_at='old' WHERE lesson_id='apofp26_afo_01'")
        original = self.request()
        activity = original["roadmap"]["days"][0]["activities"][0]["id"]
        self.request("/api/roadmap/activities/" + activity, "PUT", {"completed": True})
        new = self.request("/api/profiles", "POST", {"name": "Meu estudo"})
        fresh = self.request(profile=new["id"])
        self.assertEqual(fresh["totals"]["completed"], 0)
        self.assertEqual(fresh["roadmap"]["stats"]["completed_activities"], 0)
        self.assertEqual(fresh["roadmap"]["stats"]["lessons"], 94)
        session = self.request("/api/lessons/apofp26_afo_01/sessions", "POST", {}, new["id"])
        self.request(
            "/api/sessions/" + session["session_id"] + "/state",
            "PUT",
            {"payload": {"recallText": "Minha anotação"}},
            new["id"],
        )
        self.assertEqual(self.request(profile=new["id"])["active_session"]["payload"]["recallText"], "Minha anotação")
        self.request(
            "/api/sessions/" + session["session_id"] + "/complete", "POST", {"cards": [], "difficulties": []}, new["id"]
        )
        server.init_db()
        with ThreadPoolExecutor(max_workers=4) as pool:
            states = list(pool.map(lambda p: self.request(profile=p), ["principal", new["id"]] * 4))
        for i, state in enumerate(states):
            self.assertEqual(state["profile"]["id"], "principal" if i % 2 == 0 else new["id"])
            self.assertEqual(state["totals"]["completed"], 1)
            self.assertEqual(state["roadmap"]["stats"]["completed_activities"], 1 if i % 2 == 0 else 0)

    def test_reset_only_current_roadmap_and_backup(self):
        plan = self.request()["roadmap"]
        activity = plan["days"][0]["activities"][0]["id"]
        session = self.request("/api/lessons/apofp26_afo_01/sessions", "POST", {})
        sid = session["session_id"]
        self.request(
            "/api/sessions/" + sid + "/complete",
            "POST",
            {"cards": [{"selected": True, "front": "Pergunta", "back": "Resposta"}], "difficulties": ["Dúvida"]},
        )
        self.request("/api/roadmap/activities/" + activity, "PUT", {"completed": True, "note": "Nota"})
        with server.study_db() as con:
            con.execute("INSERT INTO subjects VALUES('personal','Pessoal','old')")
            con.execute("INSERT INTO topics VALUES('personal-topic','personal','Tópico',0,'old')")
            con.execute(
                "INSERT INTO lessons(lesson_id,topic_id,title,completed_at,created_at) VALUES('personal-lesson','personal-topic','Minha aula','done','old')"
            )
            con.execute("INSERT INTO attempts VALUES('free',NULL,'free','q','A',0,'{}',1,'old')")
            con.execute("INSERT INTO attempts VALUES('in-session',?,'practice','q','A',0,'{}',1,'old')", (sid,))
            card = con.execute("SELECT card_id FROM cards").fetchone()[0]
            con.execute("INSERT INTO card_reviews VALUES('r',?,'facil',1,3,'2026-11-01','old')", (card,))
        other = self.request("/api/profiles", "POST", {"name": "Outro"})
        self.request("/api/roadmap/activities/" + activity, "PUT", {"completed": True}, other["id"])
        result = self.request("/api/roadmap/reset", "POST", {"confirm": "principal"})
        reset = self.request()
        self.assertEqual(reset["roadmap"]["stats"]["completed"], 0)
        self.assertEqual(reset["roadmap"]["stats"]["completed_activities"], 0)
        self.assertEqual(reset["totals"]["completed"], 1)  # personal lesson retained
        self.assertEqual(self.request(profile=other["id"])["roadmap"]["stats"]["completed_activities"], 1)
        with server.study_db() as con:
            for table in ("study_sessions", "cards", "card_reviews", "lesson_difficulties"):
                self.assertEqual(con.execute("SELECT count(*) FROM " + table).fetchone()[0], 0)
            self.assertEqual(con.execute("SELECT attempt_id FROM attempts").fetchone()[0], "free")
            self.assertEqual(con.execute("SELECT count(*) FROM materials").fetchone()[0], 94)
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
        with contextlib.closing(sqlite3.connect(server.STUDY_DB.parent / result["backup"])) as backup:
            self.assertEqual(backup.execute("SELECT count(*) FROM study_sessions").fetchone()[0], 1)
            self.assertEqual(backup.execute("SELECT count(*) FROM cards").fetchone()[0], 1)
        # Reset a non-default database too; it must leave Principal unchanged.
        self.request("/api/roadmap/reset", "POST", {"confirm": other["id"]}, other["id"])
        self.assertEqual(self.request(profile=other["id"])["roadmap"]["stats"]["completed_activities"], 0)
        self.assertEqual(self.request()["totals"]["completed"], 1)

    def test_validation_and_unknown_profiles(self):
        for name in ("", " " * 3, "A" * 61, None):
            with self.assertRaises(HTTPError) as error:
                self.request("/api/profiles", "POST", {"name": name})
            self.assertEqual(error.exception.code, 400)
        self.request("/api/profiles", "POST", {"name": "Ana"})
        with self.assertRaises(HTTPError):
            self.request("/api/profiles", "POST", {"name": " ana "})
        with self.assertRaises(HTTPError) as error:
            self.request(profile="../../study")
        self.assertEqual(error.exception.code, 404)
        with self.assertRaises(HTTPError) as error:
            self.request("/api/roadmap/reset", "POST", {"confirm": "someone-else"})
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(len(self.request()["profiles"]), 2)


if __name__ == "__main__":
    unittest.main()
