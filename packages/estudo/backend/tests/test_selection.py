"""Practice selection keeps content distinct and uses history across occurrences."""

import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from concurso_contracts.catalog.criar_demo import criar
from estudo.db.connections import open_catalog, open_study
from estudo.db.migrations import migrate
from estudo.services.selection import session_pool


class SelectionTests(unittest.TestCase):
    def test_duplicate_content_discursive_and_prior_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog_path = root / "catalog.sqlite"
            criar(catalog_path)
            import sqlite3

            with closing(sqlite3.connect(catalog_path)) as con, con:
                con.execute("UPDATE ocorrencias SET questao_id='q1' WHERE ocorrencia_id='o2'")
                con.execute("UPDATE questoes SET formato='discursiva' WHERE questao_id='q4'")
                con.execute("UPDATE gabaritos SET situacao_item='anulado' WHERE gabarito_registro_id='g3'")
            with open_study(root / "study.sqlite") as study, open_catalog(catalog_path) as catalog:
                migrate(study)
                study.execute("INSERT INTO subjects VALUES('s','Disciplina','old')")
                study.execute("INSERT INTO topics VALUES('t','s','Tópico',0,'old')")
                study.execute("INSERT INTO lessons(lesson_id,topic_id,title,created_at) VALUES('l','t','Aula','old')")
                study.executemany("INSERT INTO lesson_questions VALUES('l',?,?)", [(f"o{i}", i) for i in range(1, 21)])
                study.executemany(
                    "INSERT INTO attempts(attempt_id,stage,occurrence_id,answer,reference_snapshot,correct,created_at) "
                    "VALUES(?,'free',?,'A','{}',?,?)",
                    [("right", "o2", 1, "2030-01-01"), ("wrong", "o5", 0, "2030-01-02")],
                )
                pool = session_pool(study, catalog, "l", size=50)["questionPool"]
                content_ids = dict(catalog.execute("SELECT ocorrencia_id,questao_id FROM ocorrencias"))
                self.assertEqual(len(pool), len({content_ids[oid] for oid in pool}))
                self.assertNotIn("o4", pool)
                self.assertEqual(pool[-1], "o3")
                self.assertLess(pool.index("o6"), pool.index("o5"))
                self.assertLess(pool.index("o5"), pool.index("o1"))
                self.assertEqual(session_pool(study, catalog, "l")["questionPool"], pool[:12])
