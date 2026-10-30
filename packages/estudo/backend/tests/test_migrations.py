import sqlite3
import tempfile
import unittest
from pathlib import Path

from estudo.db.migrations import migrate


class MigrationTests(unittest.TestCase):
    def test_numbered_upgrade_and_failure_are_atomic(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            directory = Path(tmp)
            (directory / "001_init.sql").write_text("CREATE TABLE data (value TEXT);\n", encoding="utf-8")
            with sqlite3.connect(":memory:") as con:
                migrate(con, directory)
                con.execute("INSERT INTO data VALUES ('preservado')")
                con.commit()
                (directory / "002_upgrade.sql").write_text(
                    "ALTER TABLE data ADD COLUMN extra TEXT;\nINVALID SQL;\n", encoding="utf-8"
                )
                with self.assertRaises(sqlite3.Error):
                    migrate(con, directory)
                self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 1)
                self.assertEqual([r[1] for r in con.execute("PRAGMA table_info(data)")], ["value"])
                self.assertEqual(con.execute("SELECT value FROM data").fetchone()[0], "preservado")
                (directory / "002_upgrade.sql").write_text(
                    "ALTER TABLE data ADD COLUMN extra TEXT;\n", encoding="utf-8"
                )
                migrate(con, directory)
                migrate(con, directory)
                self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], 2)
                self.assertEqual(con.execute("SELECT value FROM data").fetchone()[0], "preservado")
                self.assertEqual(
                    con.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall(), [(1,), (2,)]
                )
