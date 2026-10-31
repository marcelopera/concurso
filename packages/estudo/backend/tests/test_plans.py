import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from estudo.db.connections import open_study
from estudo.db.migrations import migrate
from estudo.services import plans as roadmap


class PlanPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.database = self.root / "study.sqlite"
        with open_study(self.database) as con:
            migrate(con)
        self.plan = {
            "id": "custom-plan",
            "title": "Meu plano",
            "area": "Estudos",
            "strategy": "Revisar os conteúdos.",
            "daily_minutes": 60,
            "exam_date": "2030-02-01",
            "coverage_deadline": "2030-01-02",
            "subjects": [
                {
                    "subject_id": "custom-subject",
                    "name": "Minha disciplina",
                    "lessons": [
                        {
                            "lesson_id": "custom-lesson",
                            "topic_id": "custom-topic",
                            "topic": "Meu tópico",
                            "title": "Minha aula",
                            "exam": "P1",
                            "scheduled_date": "2030-01-01",
                            "minutes": 60,
                        }
                    ],
                }
            ],
            "days": [{"date": "2030-01-01", "phase": "Estudo", "lessons": ["custom-lesson"], "activities": []}],
            "coverage": {"lessons": 1},
        }
        self.file = self.root / "plan.json"

    def install(self):
        self.file.write_text(json.dumps(self.plan), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            roadmap.install(self.database, self.file)

    def test_external_plan_is_idempotent_and_preserves_completion(self):
        self.install()
        with open_study(self.database) as con:
            con.execute("UPDATE lessons SET completed_at='preserved' WHERE lesson_id='custom-lesson'")
        self.install()
        with open_study(self.database) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM lessons").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT completed_at FROM lessons").fetchone()[0], "preserved")
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
            public = roadmap.public_plan(con, "2030-01-01")
            self.assertEqual(public["title"], "Meu plano")
            self.assertEqual(public["stats"]["completed"], 1)
        self.assertTrue(list(self.root.glob("estudo-antes-roadmap-*.sqlite")))

    def test_invalid_plan_and_changed_configuration_do_not_modify_progress(self):
        self.install()
        original = self.database.read_bytes()
        self.plan["coverage"]["lessons"] = 2
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(self.database.read_bytes(), original)
        self.plan["coverage"]["lessons"] = 1
        self.plan["title"] = "Changed configuration"
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(self.database.read_bytes(), original)

    def test_changed_lesson_metadata_requires_a_new_plan_id(self):
        self.install()
        original = self.database.read_bytes()
        self.plan["subjects"][0]["lessons"][0]["title"] = "Outro conteúdo"
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(self.database.read_bytes(), original)

    def test_failed_import_rolls_back_all_partial_inserts(self):
        with open_study(self.database) as con:
            con.execute("INSERT INTO subjects VALUES('old','Pessoal','old')")
            con.execute("INSERT INTO topics VALUES('old','old','Tópico',0,'old')")
            con.execute(
                "INSERT INTO lessons(lesson_id,topic_id,title,created_at) VALUES('custom-lesson','old','Preservar','old')"
            )
        with self.assertRaises(ValueError):
            self.install()
        with open_study(self.database) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM study_plans").fetchone()[0], 0)
            self.assertEqual(con.execute("SELECT count(*) FROM subjects").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT title FROM lessons").fetchone()[0], "Preservar")
