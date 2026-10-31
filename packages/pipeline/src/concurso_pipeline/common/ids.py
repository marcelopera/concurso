"""Shared pipeline ids operations."""

import hashlib
import re
import unicodedata


def ident(prefix, *parts):
    # Retain the historical identity algorithm, including case. Changing source
    # text may change a question ID but must never change an occurrence ID.
    values = [re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(p or ""))).strip() for p in parts]
    return prefix + "_" + hashlib.sha256("\x1f".join(values).encode()).hexdigest()[:24]
