"""Public synthetic regressions for evidence-based lesson mapping."""

from __future__ import annotations

import contextlib
import gc
import hashlib
import io
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from mapping_fixtures import create_mapping_catalog

from estudo.app import Application
from estudo.mapping import __main__ as map_questions
from estudo.mapping.rules import normalize
from estudo.repositories import question_links
from estudo.services import plans as roadmap
from estudo.services import selection
from estudo.services.sessions import answer_snapshot

ROOT = Path(__file__).resolve().parents[4]
PLAN_FILE = ROOT / "plans" / "apofp-2026" / "roadmap.json"


class SyntheticMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_mapping_paths = (
            map_questions.CONTENT,
            map_questions.STUDY,
            map_questions.PLAN,
            map_questions.OUTPUT,
            map_questions.OVERRIDES,
        )
        cls.original_roadmap_plan = roadmap.PLAN_FILE
        roadmap.PLAN_FILE = PLAN_FILE
        cls.temp = tempfile.TemporaryDirectory(prefix="concurso-mapping-synthetic-")
        cls.root = Path(cls.temp.name)
        cls.catalog = cls.root / "catalog.sqlite"
        cls.fixture_cases = create_mapping_catalog(cls.catalog)
        cls.app = Application()
        cls.study = cls.root / "study.sqlite"
        cls.app.settings.study_db = cls.study
        cls.app.settings.content_db = cls.catalog
        cls.app.settings.plan_file = PLAN_FILE

        map_questions.CONTENT = cls.catalog
        map_questions.STUDY = cls.study
        map_questions.PLAN = PLAN_FILE
        map_questions.OUTPUT = cls.root / "mapping-output"
        map_questions.OVERRIDES = map_questions.OUTPUT / "revisoes.json"

        cls.app.init_db()
        with contextlib.redirect_stdout(io.StringIO()):
            roadmap.install(cls.study)
        cls._seed_existing_history()

        cls.questions, cls.links, cls.report = map_questions.build()
        cls.by_id = {question["ocorrencia_id"]: question for question in cls.questions}
        map_questions.apply_links(cls.links, cls.report, cls.study)
        cls.catalog_hash = hashlib.sha256(cls.catalog.read_bytes()).hexdigest()

        cls.http = cls.app.http_server(("127.0.0.1", 0))
        cls.http.quiet = True
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.http.server_port}"

    @classmethod
    def _seed_existing_history(cls):
        with cls.app.study_db() as con:
            con.execute("INSERT INTO subjects VALUES('manual-subject','Pessoal','before')")
            con.execute("INSERT INTO topics VALUES('manual-topic','manual-subject','Tópico',0,'before')")
            con.execute(
                "INSERT INTO lessons(lesson_id,topic_id,title,completed_at,created_at) "
                "VALUES('manual-lesson','manual-topic','Aula pessoal','preservado','before')"
            )
            con.execute("UPDATE lessons SET completed_at='preservado' WHERE lesson_id='apofp26_por_02'")
            con.execute("INSERT INTO lesson_questions VALUES('manual-lesson','o3',0)")
            con.execute("INSERT INTO lesson_questions VALUES('apofp26_mat_08','o3',0)")
            con.execute(
                "INSERT INTO study_sessions VALUES('manual-session','manual-lesson','completed',0,NULL,NULL,'{}',"
                "'started','updated','completed')"
            )
            con.execute(
                "INSERT INTO attempts VALUES('manual-attempt','manual-session','practice','o3','A',0,'{}',1,'before')"
            )
            con.execute(
                "INSERT INTO cards VALUES('manual-card','manual-topic','manual-session','Frente','Verso','',1,"
                "'2099-01-02',1,'before')"
            )
            con.execute(
                "INSERT INTO card_reviews VALUES('manual-review','manual-card','facil',1,3,'2099-01-04','before')"
            )

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()
        (
            map_questions.CONTENT,
            map_questions.STUDY,
            map_questions.PLAN,
            map_questions.OUTPUT,
            map_questions.OVERRIDES,
        ) = cls.original_mapping_paths
        roadmap.PLAN_FILE = cls.original_roadmap_plan
        if hashlib.sha256(cls.catalog.read_bytes()).hexdigest() != cls.catalog_hash:
            raise AssertionError("The synthetic content catalog was modified by mapping or API requests.")
        gc.collect()
        cls.temp.cleanup()

    def request(self, path, method="GET", body=None):
        request = Request(
            self.url + path,
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"Origin": self.url, "Content-Type": "application/json"},
        )
        with urlopen(request, timeout=15) as response:
            return json.load(response)

    def test_every_synthetic_occurrence_is_audited_with_localizable_evidence(self):
        audit = [
            json.loads(line)
            for line in (map_questions.OUTPUT / "auditoria-toda-base.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(audit), len(self.questions))
        self.assertEqual(len({question["ocorrencia_id"] for question in self.questions}), len(audit))
        self.assertEqual(self.report["linked_occurrences"] + self.report["unlinked_occurrences"], len(audit))
        self.assertEqual(len({(link["lesson_id"], link["occurrence_id"]) for link in self.links}), len(self.links))
        self.assertEqual(set(self.report["by_bank"]), {"Banca Exemplo A", "Banca Exemplo B"})
        for link in self.links:
            question = self.by_id[link["occurrence_id"]]
            self.assertTrue(link["syllabus_excerpt"])
            for evidence in link["evidence"]:
                raw = (
                    question["enunciado_original"]
                    if evidence["field"] == "enunciado_original"
                    else " ".join(answer["texto_original"] for answer in question["alternatives"])
                )
                self.assertIn(normalize(evidence["text"]), normalize(raw))

        output = io.StringIO()
        original = (
            map_questions.CONTENT,
            map_questions.STUDY,
            map_questions.PLAN,
            map_questions.OUTPUT,
            map_questions.OVERRIDES,
        )
        try:
            with contextlib.redirect_stdout(output):
                map_questions.main(
                    [
                        "--plan",
                        str(PLAN_FILE),
                        "--catalog",
                        str(self.catalog),
                        "--database",
                        str(self.study),
                        "--output",
                        str(self.root / "dry-run"),
                    ]
                )
        finally:
            (
                map_questions.CONTENT,
                map_questions.STUDY,
                map_questions.PLAN,
                map_questions.OUTPUT,
                map_questions.OVERRIDES,
            ) = original
        self.assertIn('"total_occurrences"', output.getvalue())
        self.assertTrue((self.root / "dry-run" / "relatorio.json").exists())

    def test_incidental_terms_do_not_cross_topics_and_foreign_text_is_excluded(self):
        by_occurrence = {
            occurrence: {link["lesson_id"] for link in self.links if link["occurrence_id"] == occurrence}
            for occurrence in self.fixture_cases
        }
        self.assertEqual(by_occurrence["o2"], {"apofp26_por_02"})
        self.assertNotIn("apofp26_da_05", by_occurrence["o2"])
        self.assertEqual(by_occurrence["o3"], set())
        self.assertEqual(by_occurrence["o4"], {"apofp26_da_05"})
        self.assertEqual(by_occurrence["o5"], {"apofp26_mat_02"})
        self.assertEqual(len(by_occurrence["o1"]), 1)

    def test_import_is_idempotent_atomic_and_preserves_manual_data_and_history(self):
        again = map_questions.apply_links(self.links, self.report, self.study)
        self.assertEqual(again["added"], 0)
        synced = map_questions.apply_links(self.links[:-1], self.report, self.study)
        self.assertEqual(synced["removed_obsolete_generated"], 1)
        with self.app.study_db() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM lesson_questions").fetchone()[0], len(self.links) + 1)
            self.assertEqual(
                con.execute("SELECT completed_at FROM lessons WHERE lesson_id='manual-lesson'").fetchone()[0],
                "preservado",
            )
            self.assertEqual(
                con.execute("SELECT completed_at FROM lessons WHERE lesson_id='apofp26_por_02'").fetchone()[0],
                "preservado",
            )
            self.assertEqual(
                con.execute(
                    "SELECT position FROM lesson_questions WHERE lesson_id='apofp26_mat_08' AND occurrence_id='o3'"
                ).fetchone()[0],
                0,
            )
            self.assertEqual(con.execute("SELECT attempt_id FROM attempts").fetchone()[0], "manual-attempt")
            self.assertEqual(con.execute("SELECT review_id FROM card_reviews").fetchone()[0], "manual-review")
            self.assertEqual(con.execute("SELECT count(*) FROM cards").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT count(*) FROM study_sessions").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT count(*) FROM question_mapping_runs").fetchone()[0], 3)

        broken = [dict(self.links[0]), dict(self.links[1], lesson_id="nonexistent-lesson")]
        with self.assertRaises(sqlite3.IntegrityError):
            map_questions.apply_links(broken, self.report, self.study)
        with self.app.study_db() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM question_mapping_runs").fetchone()[0], 3)
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_large_lesson_api_keeps_provenance_and_hides_reference_answers(self):
        lesson = self.request("/api/lessons/apofp26_por_02")
        occurrence_ids = lesson["occurrence_ids"]
        self.assertGreater(len(occurrence_ids), 100)
        self.assertEqual(len(occurrence_ids), len(lesson["questions"]))
        for question in lesson["questions"]:
            self.assertTrue(question["mapping"]["evidence"])
            self.assertNotIn("reference_answer", question)
            self.assertNotIn("resposta_referencia", question)
            self.assertNotIn("answer", question["mapping"])

        saved = self.request(
            "/api/lessons/apofp26_por_02/questions",
            "PUT",
            {"occurrence_ids": list(reversed(occurrence_ids))},
        )
        self.assertEqual(saved["occurrence_ids"], list(reversed(occurrence_ids)))
        self.assertTrue(all(question["mapping"] for question in saved["questions"]))
        self.request("/api/lessons/apofp26_por_02/questions", "PUT", {"occurrence_ids": occurrence_ids})

    def test_session_selection_uses_distinct_content_history_and_rotation(self):
        with self.app.study_db() as study, self.app.content_db() as content:
            first = selection.session_pool(study, content, "apofp26_por_02")
            self.assertEqual(len(first["questionPool"]), 12)
            items = question_links.content_items(content, first["questionPool"])
            self.assertEqual(len({question["questao_id"] for question in items}), 12)
            self.assertNotIn(first["pretestOccurrenceId"], first["practiceOccurrenceIds"])
            self.assertNotIn(first["recallOccurrenceId"], first["practiceOccurrenceIds"])

        question = self.app.content_question(first["pretestOccurrenceId"], include_answer=True)
        outcome = answer_snapshot(
            self.app,
            first["pretestOccurrenceId"],
            question["resposta_referencia"],
            "free",
        )
        self.assertTrue(outcome["correct"])
        with self.app.study_db() as study, self.app.content_db() as content:
            second = selection.session_pool(study, content, "apofp26_por_02")
        self.assertNotEqual(first["pretestOccurrenceId"], second["pretestOccurrenceId"])
        self.assertNotIn(first["pretestOccurrenceId"], second["questionPool"])

        session = self.request("/api/lessons/apofp26_por_02/sessions", "POST", {})
        self.assertEqual(len(session["payload"]["questionPool"]), 12)
        resumed = self.request("/api/lessons/apofp26_por_02/sessions", "POST", {})
        self.assertEqual(resumed["payload"]["questionPool"], session["payload"]["questionPool"])
        boot = self.request("/api/bootstrap")
        mapping = boot["roadmap"]["question_mapping"]
        self.assertEqual(mapping["total_occurrences"], len(self.questions))
        self.assertEqual(mapping["current_links"], len(self.links))
        self.assertEqual(mapping["current_lessons_with_questions"], self.report["lessons_with_questions"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
