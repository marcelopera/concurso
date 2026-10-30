"""Execution configuration; importing extractors never creates directories."""

import hashlib
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from concurso_contracts import resource_file as resource_file
from concurso_contracts.catalog.contrato import current_commit

from .common import relative_file

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


def _provenance_status(settings: Settings) -> str:
    manifest = settings.run_dir / "MANIFEST.raw.json"
    if not manifest.is_file():
        return "desconhecida"
    try:
        provenance = json.loads(manifest.read_text(encoding="utf-8")).get("provenance")
    except (OSError, json.JSONDecodeError, AttributeError):
        return "desconhecida"
    if not isinstance(provenance, dict):
        return "desconhecida"
    status = provenance.get("status")
    if status in {"synthetic", "sintetica"}:
        return "sintetica"
    if status == "legacy-unrecorded" or status in {None, "unknown", "desconhecida"}:
        return "desconhecida"
    return "registrada"


def execution_metadata(settings: Settings) -> dict:
    """Create once and return stable metadata for this pipeline execution."""
    settings.run_dir.mkdir(parents=True, exist_ok=True)
    path = settings.run_dir / "execucao.json"
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        metadata = {
            "execucao_id": settings.run_id,
            "origem": "concurso_pipeline",
            "proveniencia": _provenance_status(settings),
            "gerado_em": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "commit_execucao": current_commit(Path(__file__)),
        }
        try:
            with path.open("x", encoding="utf-8", newline="\n") as destination:
                json.dump(metadata, destination, ensure_ascii=False, sort_keys=True)
                destination.write("\n")
        except FileExistsError:
            metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Metadados da execução inválidos; o arquivo execucao.json não foi alterado.") from exc

    generated_at = metadata.get("gerado_em") if isinstance(metadata, dict) else None
    try:
        parsed_generated_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        valid_generated_at = (
            parsed_generated_at.tzinfo is not None
            and parsed_generated_at.utcoffset() == timezone.utc.utcoffset(parsed_generated_at)
        )
    except (AttributeError, ValueError):
        valid_generated_at = False

    if (
        not isinstance(metadata, dict)
        or metadata.get("execucao_id") != settings.run_id
        or metadata.get("origem") != "concurso_pipeline"
        or metadata.get("proveniencia") not in {"desconhecida", "sintetica", "registrada"}
        or not valid_generated_at
        or not isinstance(metadata.get("commit_execucao"), str)
        or not re.fullmatch(r"(?:desconhecido|[0-9a-f]{40}|[0-9a-f]{64})", metadata["commit_execucao"])
    ):
        raise ValueError(
            "Metadados da execução inválidos; identifique a execução e os valores desconhecidos explicitamente."
        )
    return {**metadata, "commit_origem": current_commit(Path(__file__))}


def catalog_source_hashes(settings: Settings) -> dict[str, str]:
    """Hash stable execution metadata, the canonical snapshot and any raw manifest."""
    paths = {"execucao.json": settings.run_dir / "execucao.json"}
    paths.update(
        {
            f"canonical/{name}": settings.canonical / name
            for name in ("documentos.json", "questoes.jsonl", "topicos.jsonl", "gabaritos.jsonl")
        }
    )
    manifest = settings.run_dir / "MANIFEST.raw.json"
    if manifest.is_file():
        paths["MANIFEST.raw.json"] = manifest
    hashes = {}
    for name, path in paths.items():
        try:
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise ValueError(f"Fonte canônica ausente ou ilegível: {name}.") from exc
    return hashes


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
