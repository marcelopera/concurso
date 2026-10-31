import sqlite3
import tempfile
import unittest
from pathlib import Path

from estudo.app import Application

server = Application()
from concurso_contracts.catalog.criar_demo import criar


class DemoTests(unittest.TestCase):
    def test_catalog_is_self_contained_and_correctable(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            catalog = Path(tmp) / "catalog.sqlite"
            criar(catalog)
            with sqlite3.connect(catalog) as con:
                self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 2)
                self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
            con.close()
            original = server.settings.content_db
            try:
                server.settings.content_db = catalog
                page = server.question_page("", "", "", 1)
                self.assertEqual(page["total"], 20)
                self.assertEqual(len(page["banks"]), 2)
                item = server.content_question(page["items"][0]["occurrence_id"], include_answer=True)
                self.assertEqual(item["resposta_referencia"], "A")
                self.assertTrue(item["reference_status"]["correctable"])
                with self.assertRaises(FileExistsError):
                    criar(catalog)
            finally:
                server.settings.content_db = original
