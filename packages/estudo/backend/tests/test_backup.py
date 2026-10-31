import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from estudo.db.backup import copy_database


class BackupTests(unittest.TestCase):
    def test_backup_restore_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            source, backup, restored = [Path(tmp) / name for name in ("source.db", "backup.db", "restored.db")]
            with closing(sqlite3.connect(source)) as con, con:
                con.execute("CREATE TABLE progress(value TEXT)")
                con.execute("INSERT INTO progress VALUES ('preservado')")
            copy_database(source, backup)
            copy_database(backup, restored)
            with closing(sqlite3.connect(restored)) as con:
                self.assertEqual(con.execute("SELECT value FROM progress").fetchone()[0], "preservado")
            with self.assertRaises(ValueError):
                copy_database(backup, source)
