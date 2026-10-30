"""Version and structural contract for catalogs consumed by the application."""

import hashlib
import json
import re
import sqlite3
import subprocess
from contextlib import closing
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path, PurePosixPath

CATALOG_VERSION = 2
LEGACY_CATALOG_VERSIONS = (0, 1)
UNKNOWN = "desconhecido"
SCHEMA_FILE = Path(__file__).with_name("esquema.sql")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def serialize_sources(sources: dict[str, str]) -> str:
    """Serialize a relative-path-to-SHA-256 manifest deterministically."""
    return json.dumps(sources, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_sources(sources: dict[str, str]) -> str:
    """Return the SHA-256 of a canonical source manifest."""
    return hashlib.sha256(serialize_sources(sources).encode("utf-8")).hexdigest()


def current_commit(source_file: Path) -> str:
    """Return the clean Git commit containing source_file, or an explicit unknown marker."""
    for candidate in Path(source_file).resolve().parents:
        if not (candidate / ".git").exists():
            continue
        try:
            status = subprocess.run(
                ["git", "-C", str(candidate), "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            ).stdout
            if status:
                return UNKNOWN
            result = subprocess.run(
                ["git", "-C", str(candidate), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return UNKNOWN
        return result if re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", result) else UNKNOWN
    return UNKNOWN


@lru_cache(maxsize=1)
def expected_columns() -> dict[str, set[str]]:
    """Derive requirements from the same schema used to build the demo."""
    with closing(sqlite3.connect(":memory:")) as reference:
        reference.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        names = [
            r[0]
            for r in reference.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE '%_fts%'"
            )
            if r[0] != "schema_meta"
        ]
        return {name: {r[1] for r in reference.execute(f'PRAGMA table_info("{name}")')} for name in names}


def _valid_utc(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _valid_sources(value: object) -> bool:
    return (
        isinstance(value, dict)
        and bool(value)
        and all(
            isinstance(path, str)
            and path
            and not PurePosixPath(path).is_absolute()
            and not re.match(r"^[A-Za-z]:", path)
            and "\\" not in path
            and ".." not in PurePosixPath(path).parts
            and isinstance(digest, str)
            and _SHA256.fullmatch(digest) is not None
            for path, digest in value.items()
        )
    )


def _validate_v2(con: sqlite3.Connection) -> None:
    columns = {row[1] for row in con.execute('PRAGMA table_info("schema_meta")')}
    required = {"versao", "execucao_id", "origem", "gerado_em", "commit_origem", "hash_fontes", "fontes_json"}
    if not required <= columns:
        raise RuntimeError("Catálogo incompatível: schema_meta não contém os metadados v2 obrigatórios.")

    rows = con.execute(
        "SELECT versao, execucao_id, origem, gerado_em, commit_origem, hash_fontes, fontes_json FROM schema_meta"
    ).fetchall()
    if len(rows) != 1:
        raise RuntimeError("Catálogo incompatível: schema_meta deve conter exatamente uma linha.")
    version, execution_id, origin, generated_at, commit, source_hash, sources_json = rows[0]
    if version != CATALOG_VERSION:
        raise RuntimeError("Catálogo incompatível: schema_meta diverge de PRAGMA user_version.")
    if (
        not isinstance(execution_id, str)
        or not execution_id.strip()
        or not isinstance(origin, str)
        or not origin.strip()
    ):
        raise RuntimeError("Catálogo incompatível: identificação ou origem da execução inválida.")
    if not _valid_utc(generated_at):
        raise RuntimeError("Catálogo incompatível: data de geração deve ser um instante UTC válido.")
    if not _valid_commit(commit):
        raise RuntimeError("Catálogo incompatível: commit de origem inválido ou desconhecido não declarado.")
    try:
        sources = json.loads(sources_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Catálogo incompatível: manifesto de fontes inválido.") from exc
    if not _valid_sources(sources) or serialize_sources(sources) != sources_json:
        raise RuntimeError(
            "Catálogo incompatível: manifesto de fontes não está normalizado ou contém hashes inválidos."
        )
    if (
        not isinstance(source_hash, str)
        or _SHA256.fullmatch(source_hash) is None
        or hash_sources(sources) != source_hash
    ):
        raise RuntimeError("Catálogo incompatível: hash do manifesto de fontes diverge.")

    execution_rows = con.execute(
        "SELECT data_inicio, contrato_versao, metadados_json FROM execucoes WHERE execucao_id = ?", (execution_id,)
    ).fetchall()
    if len(execution_rows) != 1:
        raise RuntimeError("Catálogo incompatível: schema_meta não identifica uma execução existente.")
    started_at, contract_version, metadata_json = execution_rows[0]
    if started_at != generated_at or contract_version != f"v{CATALOG_VERSION}" or not _valid_utc(started_at):
        raise RuntimeError("Catálogo incompatível: metadados da execução divergem de schema_meta.")
    try:
        metadata = json.loads(metadata_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Catálogo incompatível: metadados da execução inválidos.") from exc
    if (
        not isinstance(metadata, dict)
        or metadata.get("execucao_id") != execution_id
        or metadata.get("origem") != origin
        or metadata.get("gerado_em") != generated_at
        or metadata.get("proveniencia") not in {"desconhecida", "sintetica", "registrada"}
        or not _valid_commit(metadata.get("commit_execucao"))
        or metadata.get("commit_origem") != commit
        or metadata.get("hash_fontes") != source_hash
        or metadata.get("fontes") != sources
    ):
        raise RuntimeError("Catálogo incompatível: execução e metadados do catálogo divergem.")


def _valid_commit(value: object) -> bool:
    return isinstance(value, str) and (
        value == UNKNOWN or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value) is not None
    )


def validate_catalog(con: sqlite3.Connection) -> None:
    """Validate current catalogs and accept known legacy formats without writes."""
    version = con.execute("PRAGMA user_version").fetchone()[0]
    if version not in (*LEGACY_CATALOG_VERSIONS, CATALOG_VERSION):
        raise RuntimeError(
            f"Catálogo versão {version} não é compatível com esta aplicação (esperada: {CATALOG_VERSION})."
        )
    try:
        for name, required in expected_columns().items():
            actual = {r[1] for r in con.execute(f'PRAGMA table_info("{name}")')}
            missing = required - actual
            if missing:
                raise RuntimeError(f"Catálogo incompatível: {name} não contém as colunas {', '.join(sorted(missing))}.")
        if version == CATALOG_VERSION:
            _validate_v2(con)
        elif version == 1:
            rows = con.execute("SELECT versao FROM schema_meta").fetchall()
            if len(rows) != 1 or rows[0][0] != 1:
                raise RuntimeError("Catálogo incompatível: schema_meta diverge de PRAGMA user_version.")
    except sqlite3.Error as exc:
        raise RuntimeError("Catálogo incompatível: estrutura ou metadados inválidos.") from exc
