"""SQLite online backup with integrity validation and no overwrites."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path


def copy_database(source: Path, destination: Path) -> None:
    source, destination = (source.resolve(), destination.resolve())
    if not source.is_file():
        raise ValueError(f"Banco de origem não encontrado: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 384)
    except FileExistsError:
        raise ValueError(f"O destino já existe: {destination}") from None
    os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            if src.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("O banco de origem não passou na verificação de integridade.")
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
