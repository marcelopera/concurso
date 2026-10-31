"""Shared pipeline text operations."""

import re
import unicodedata


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
