"""Shared value validation and serialization, independent of transport and persistence."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds") if value else None


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def json_load(value: str | None, fallback=None):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return fallback


def safe_json(value, max_chars: int = 20_000_000) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(encoded) > max_chars:
        raise ValueError("O conteúdo salvo é grande demais.")
    return encoded


def clean_text(value, name: str, maximum: int = 500, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Informe {name}.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"Informe {name}.")
    if len(value) > maximum:
        raise ValueError(f"{name.capitalize()} deve ter até {maximum} caracteres.")
    return value
