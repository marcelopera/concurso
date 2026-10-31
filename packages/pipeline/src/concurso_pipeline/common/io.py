"""Shared pipeline io operations."""

import json
from pathlib import Path


def readjl(path):
    """Missing inputs are errors; callers explicitly choose optional inputs."""
    with Path(path).open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def js(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def writejl(path, rows):
    Path(path).write_text("".join(js(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def write_selected_batch(path, rows, document_ids):
    """Re-extract selected documents without dropping sibling boards in a batch."""
    path = Path(path)
    selected = set(document_ids)
    preserved = [row for row in readjl(path) if row["documento_id"] not in selected] if path.exists() else []
    combined = preserved + list(rows)
    combined.sort(key=lambda row: (row["documento_id"], str(row["numero_original"])))
    temporary = path.with_suffix(path.suffix + ".tmp")
    writejl(temporary, combined)
    temporary.replace(path)
