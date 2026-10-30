"""Apply numbered SQLite migrations atomically, including legacy databases."""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def migrate(con: sqlite3.Connection, directory: Path | None = None) -> None:
    directory = directory or Path(__file__).parent
    files = sorted(directory.glob('[0-9][0-9][0-9]_*.sql'))
    versions = [int(path.name[:3]) for path in files]
    if not versions or versions != list(range(1, len(versions) + 1)):
        raise RuntimeError('As migrações do banco devem ser numeradas consecutivamente a partir de 001.')

    # The lock covers both the version check and all pending migrations.
    con.execute('BEGIN IMMEDIATE')
    try:
        current = con.execute('PRAGMA user_version').fetchone()[0]
        if current > versions[-1]:
            raise RuntimeError(f'Banco de progresso versão {current} é mais recente que esta aplicação.')
        con.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)')
        for version, path in zip(versions, files):
            if version <= current:
                continue
            statement = ''
            for line in path.read_text(encoding='utf-8').splitlines(keepends=True):
                statement += line
                if sqlite3.complete_statement(statement):
                    con.execute(statement)
                    statement = ''
            if statement.strip():
                raise RuntimeError(f'Migração incompleta: {path.name}')
            timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
            con.execute('INSERT OR IGNORE INTO schema_migrations VALUES (?, ?)', (version, timestamp))
            con.execute(f'PRAGMA user_version = {version}')
        con.commit()
    except Exception:
        con.rollback()
        raise
