"""Read-only catalog and profile-scoped progress connections."""

import sqlite3
from pathlib import Path

from catalogo.contrato import validate_catalog


class ClosingConnection(sqlite3.Connection):
    """Commit or roll back and close when leaving a with block."""

    def __exit__(self, exc_type, exc, traceback):
        try:
            return super().__exit__(exc_type, exc, traceback)
        finally:
            self.close()


def open_study(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=15, factory=ClosingConnection)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 15000")
    return con


def open_catalog(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise RuntimeError(f"Banco de conteúdo não encontrado: {path}")
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10, factory=ClosingConnection)
    try:
        validate_catalog(con)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA query_only = ON")
        return con
    except Exception:
        con.close()
        raise
