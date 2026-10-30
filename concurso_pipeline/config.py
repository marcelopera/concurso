"""Execution configuration; importing extractors never creates directories."""

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from .common import relative_file

REPOSITORY = Path(__file__).resolve().parents[1]
ACTIVE = ContextVar("pipeline_config")


@dataclass(frozen=True)
class Settings:
    data_root: Path
    library: Path
    run_id: str
    repair_ce: bool = False
    boards: tuple[str, ...] = ()

    def __post_init__(self):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}", self.run_id):
            raise ValueError("run-id inválido: use letras, números, ponto, hífen ou sublinhado.")

    @property
    def run_dir(self):
        return self.data_root / "runs" / self.run_id

    @property
    def output_dir(self):
        return self.run_dir / "generated"

    @property
    def canonical(self):
        return self.run_dir / "canonical"


def config():
    return ACTIVE.get()


@contextmanager
def execution(settings):
    token = ACTIVE.set(settings)
    try:
        yield settings
    finally:
        ACTIVE.reset(token)


def source_file(document):
    root = config().library.resolve()
    path = (root / relative_file(document["arquivo"])).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("PDF ausente ou fora da biblioteca.")
    return path


def load_documents():
    import json

    rows = json.loads((config().run_dir / "documentos.json").read_text(encoding="utf-8"))
    return [d for d in rows if not config().boards or d["banca"] in config().boards]


def resource_file(group, name):
    """Package wheels carry the same canonical assets as a source checkout."""
    try:
        return files(f"concurso_pipeline.{group}").joinpath(name)
    except ModuleNotFoundError:
        folder = "docs/schemas" if group == "schemas" else "sistema-estudo/catalogo"
        return REPOSITORY / folder / name
