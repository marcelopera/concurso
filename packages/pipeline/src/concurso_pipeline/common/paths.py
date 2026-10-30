"""Shared pipeline paths operations."""

from pathlib import PurePosixPath, PureWindowsPath


def relative_file(value):
    text = str(value).replace("\\", "/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or PureWindowsPath(text).drive or ".." in path.parts or ":" in text:
        raise ValueError("O manifesto deve usar caminhos relativos à biblioteca, sem travessia.")
    return path.as_posix()
