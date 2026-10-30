import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import roadmap
from estudo.db.connections import open_study
from estudo.db.migrations import migrate


class PlanPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.database = self.root / "study.sqlite"
        with open_study(self.database) as con:
            migrate(con)
        self.plan = copy.deepcopy(json.loads(roadmap.PLAN_FILE.read_text(encoding="utf-8")))
        self.plan["id"] = "custom-plan"
        subject = self.plan["subjects"][0]
        subject["subject_id"], subject["name"] = "custom-subject", "Minha disciplina"
        unit = subject["lessons"][0]
        unit["lesson_id"], unit["topic_id"] = "custom-lesson", "custom-topic"
        subject["lessons"] = [unit]
        self.plan["subjects"] = [subject]
        day = self.plan["days"][0]
        day["lessons"], day["review_lesson_ids"] = ["custom-lesson"], []
        self.plan["days"] = [day]
        self.plan["coverage"]["lessons"] = 1
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
