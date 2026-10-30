"""Version and structural contract for catalogs consumed by the application."""

import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path

CATALOG_VERSION = 1
SCHEMA_FILE = Path(__file__).with_name("esquema.sql")


@lru_cache(maxsize=1)
def expected_columns() -> dict[str, set[str]]:
    """Derive requirements from the same schema used to build the demo."""
    with closing(sqlite3.connect(":memory:")) as reference:
        reference.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        names = [
            r[0]
            for r in reference.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE '%_fts%'"
            )
        ]
        return {name: {r[1] for r in reference.execute(f'PRAGMA table_info("{name}")')} for name in names}


def validate_catalog(con: sqlite3.Connection) -> None:
    """Accept compatible legacy catalogs without ever modifying their data."""
    version = con.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, CATALOG_VERSION):
        raise RuntimeError(
            f"Catálogo versão {version} não é compatível com esta aplicação (esperada: {CATALOG_VERSION})."
        )
    try:
        for name, required in expected_columns().items():
            actual = {r[1] for r in con.execute(f'PRAGMA table_info("{name}")')}
            missing = required - actual
            if missing:
                raise RuntimeError(f"Catálogo incompatível: {name} não contém as colunas {', '.join(sorted(missing))}.")
        if version:
            rows = con.execute("SELECT versao FROM schema_meta").fetchall()
            if len(rows) != 1 or rows[0][0] != version:
                raise RuntimeError("Catálogo incompatível: schema_meta diverge de PRAGMA user_version.")
    except sqlite3.Error as exc:
        raise RuntimeError("Catálogo incompatível: estrutura ou metadados inválidos.") from exc
