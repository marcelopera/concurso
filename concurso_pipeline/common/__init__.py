"""Shared text, identity and JSONL operations."""

import hashlib
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath, PureWindowsPath


def clean(value):
    """Preserve case and paragraph boundaries in source transcriptions."""
    text = unicodedata.normalize("NFKC", str(value or "")).replace("\x0c", "\n").replace("\u00ad", "")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def norm(value):
    """One comparison normalization for consolidation and validation."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or ""))).strip().casefold()


def unaccent(value):
    return "".join(c for c in unicodedata.normalize("NFD", norm(value)) if not unicodedata.combining(c)).upper()


def ident(prefix, *parts):
    # Retain the historical identity algorithm, including case. Changing source
    # text may change a question ID but must never change an occurrence ID.
    values = [re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(p or ""))).strip() for p in parts]
    return prefix + "_" + hashlib.sha256("\x1f".join(values).encode()).hexdigest()[:24]


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


def relative_file(value):
    text = str(value).replace("\\", "/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or PureWindowsPath(text).drive or ".." in path.parts or ":" in text:
        raise ValueError("O manifesto deve usar caminhos relativos à biblioteca, sem travessia.")
    return path.as_posix()


def expected_count(text):
    """Read explicit objective counts, including written numbers on covers."""
    words = {
        "sessenta e cinco": 65,
        "sessenta": 60,
        "oitenta": 80,
        "quarenta": 40,
        "cinquenta": 50,
        "trinta": 30,
        "setenta": 70,
        "noventa": 90,
        "cem": 100,
    }
    match = re.search(r"\b(\d{1,3}|" + "|".join(words) + r")(?:\s*\([^)]*\))?\s+quest(?:ões|oes)", norm(text))
    if match:
        value = match.group(1)
        return int(value) if value.isdigit() else words[value]
    return None


def question_text(row):
    return "\n".join(
        [
            row.get("enunciado_original") or "",
            row.get("texto_original_completo") or "",
            *(a["texto"] for a in row.get("alternativas", [])),
            *(c["texto"] for c in row.get("contextos", [])),
        ]
    )
