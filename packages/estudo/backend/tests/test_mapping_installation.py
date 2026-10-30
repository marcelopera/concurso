"""Exercise mapping a catalog copied into an existing installation."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from estudo.app import Application
from estudo.services import plans as roadmap

server = Application()
from concurso_contracts.catalog.criar_demo import criar


class MappingInstallationTests(unittest.TestCase):
    def test_private_catalog_mapping_preserves_manual_links_and_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog, study = root / "conteudo.sqlite", root / "estudo.sqlite"
            criar(catalog)
            with closing(sqlite3.connect(catalog)) as con, con:
                con.execute("UPDATE schema_meta SET origem='teste privado'")
                con.execute(
                    "UPDATE questoes SET enunciado_original='Calcule juros simples de uma aplicação.' WHERE questao_id IN ('q1', 'q2')"
                )
            original = server.settings.study_db, server.settings.content_db
            try:
                server.settings.study_db, server.settings.content_db = study, catalog
                server.init_db()
                roadmap.install(study)
                with server.study_db() as con:
                    con.execute("UPDATE lessons SET completed_at='preservado' WHERE lesson_id='apofp26_mat_01'")
                    con.execute("INSERT INTO lesson_questions VALUES('apofp26_mat_01','o1',0)")
                env = dict(
                    os.environ,
                    ESTUDO_DB=str(study),
                    ESTUDO_CONTENT_DB=str(catalog),
                    ESTUDO_PLAN_FILE=str(roadmap.PLAN_FILE),
                )

                def apply():
                    return subprocess.run(
                        [sys.executable, "-m", "estudo.mapping", "--apply"],
                        cwd=APP,
                        env=env,
                        capture_output=True,
                        text=True,
                        check=True,
                    )

                apply()
                lesson = server.get_lesson("apofp26_mat_01")
                self.assertEqual({q["occurrence_id"] for q in lesson["questions"]}, {"o1", "o2"})
                self.assertIsNone(next(q for q in lesson["questions"] if q["occurrence_id"] == "o1")["mapping"])
                self.assertTrue(
                    next(q for q in lesson["questions"] if q["occurrence_id"] == "o2")["mapping"]["evidence"]
                )
                self.assertEqual(lesson["completed_at"], "preservado")
                self.assertTrue(list(root.glob("estudo-antes-vinculacao-*.sqlite")))
                self.assertEqual(
                    json.loads((root / "vinculacao" / "relatorio.json").read_text())["linked_occurrences"], 2
                )
                with closing(sqlite3.connect(catalog)) as con, con:
                    con.execute(
                        "UPDATE questoes SET enunciado_original='Sem correspondência temática.' WHERE questao_id IN ('q1', 'q2')"
                    )
                apply()
                lesson = server.get_lesson("apofp26_mat_01")
                self.assertEqual(lesson["occurrence_ids"], ["o1"])
                self.assertEqual(lesson["completed_at"], "preservado")
            finally:
                server.settings.study_db, server.settings.content_db = original

    def test_demo_apply_cannot_remove_existing_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = root / "demo.sqlite"
            criar(catalog)
            result = subprocess.run(
                [sys.executable, "-m", "estudo.mapping", "--apply"],
                cwd=APP,
                env=dict(os.environ, ESTUDO_DB=str(root / "study.sqlite"), ESTUDO_CONTENT_DB=str(catalog)),
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("catálogo de demonstração", result.stderr)
            self.assertFalse((root / "study.sqlite").exists())
