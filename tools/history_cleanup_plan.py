"""Create a private, read-only plan for removing data from Git history."""

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path, PurePosixPath

from history_cleanup_common import reject_path_inside_git_repository

PRIVATE_ROOTS = {
    ("base-questoes", "dados"),
    ("biblioteca-concursos",),
    ("sistema-estudo", "dados"),
}
PRIVATE_DIRECTORIES = {
    "amostras",
    "captura",
    "capturas",
    "dados",
    "dataset",
    "datasets",
    "execucao",
    "execucoes",
    "evidencias",
    "fontes-visuais",
    "revisao-visual",
    "screenshot",
    "screenshots",
}
DATA_EXTENSIONS = {
    ".db",
    ".db3",
    ".jsonl",
    ".ndjson",
    ".parquet",
    ".pickle",
    ".pkl",
    ".sqlite",
    ".sqlite-shm",
    ".sqlite-wal",
    ".sqlite3",
}
REVIEW_EXTENSIONS = {
    ".7z",
    ".csv",
    ".gif",
    ".heic",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp4",
    ".pdf",
    ".png",
    ".tar",
    ".webm",
    ".webp",
    ".zip",
}
SOURCE_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


def git(repository: Path, *arguments: str, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        check=True,
        text=not binary,
        encoding=None if binary else "utf-8",
    )
    return result.stdout


def classify_path(path: str) -> tuple[str, str | None]:
    """Return (remove|review|keep, reason) for a repository-relative path."""
    parsed = PurePosixPath(path)
    parts = tuple(part.casefold() for part in parsed.parts)
    name = parsed.name.casefold()
    is_test_fixture = any(part in {"test", "tests"} for part in parts) and "fixtures" in parts
    if is_test_fixture:
        return "review", "test-fixture-needs-data-ownership-review"
    if name.endswith(tuple(REVIEW_EXTENSIONS)) and any(
        marker in name for marker in ("screenshot", "screen-shot", "captura", "evidencia")
    ):
        return "remove", "screenshot-or-evidence-artifact"

    private_root = any(parts[: len(root)] == root for root in PRIVATE_ROOTS)

    has_private_directory = any(
        part in PRIVATE_DIRECTORIES
        or part.startswith("piloto-")
        or part.startswith("evidencias-")
        or part.startswith("evidencias_")
        for part in parts
    )
    in_private_data = private_root or has_private_directory
    if in_private_data and name.endswith(tuple(SOURCE_EXTENSIONS)):
        return "review", "source-or-document-in-data-directory"
    if private_root:
        return "remove", "private-data-root"
    if has_private_directory:
        return "remove", "private-data-directory"
    if name.endswith(".log") or name.endswith(tuple(DATA_EXTENSIONS)):
        return "remove", "data-artifact-extension"
    if name.endswith(tuple(REVIEW_EXTENSIONS)):
        return "review", "ambiguous-media-or-archive"
    return "keep", None


def repository_refs(repository: Path) -> list[dict[str, str | None]]:
    output = git(repository, "for-each-ref", "--format=%(refname)%09%(objectname)%09%(*objectname)")
    refs = []
    for line in output.splitlines():
        name, object_sha, peeled_sha = line.split("\t")
        refs.append({"ref": name, "object": object_sha, "peeled": peeled_sha or None})
    return refs


def object_storage_bytes(repository: Path) -> int:
    values = {}
    for line in git(repository, "count-objects", "-v").splitlines():
        key, value = line.split(":", 1)
        if key in {"size", "size-pack"}:
            values[key] = int(value.strip())
    return (values.get("size", 0) + values.get("size-pack", 0)) * 1024


def history_paths(repository: Path) -> set[str]:
    output = git(repository, "log", "--all", "--root", "--format=", "--name-only", "-z", binary=True)
    paths = set()
    for raw_path in output.split(b"\0"):
        if not raw_path:
            continue
        try:
            paths.add(raw_path.decode("utf-8"))
        except UnicodeDecodeError as error:
            raise ValueError("Histórico contém um caminho fora de UTF-8; gere e revise o plano manualmente.") from error
    return paths


def current_tree_summary(repository: Path, base_ref: str, remove_paths: set[str]) -> dict[str, str | int]:
    entries = git(repository, "ls-tree", "-r", "-z", "--full-tree", base_ref, binary=True)
    digest = hashlib.sha256()
    preserved_files = 0
    removable_files = 0
    review_files = 0
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        try:
            path = raw_path.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(
                "Árvore atual contém um caminho fora de UTF-8; gere e revise o plano manualmente."
            ) from error
        mode, _object_type, object_sha = metadata.decode("ascii").split(" ")
        classification, _reason = classify_path(path)
        if classification == "remove" or path in remove_paths:
            removable_files += 1
        elif classification == "review":
            review_files += 1
            digest.update(raw_path + b"\0" + mode.encode("ascii") + b"\0" + object_sha.encode("ascii") + b"\0")
            preserved_files += 1
        else:
            digest.update(raw_path + b"\0" + mode.encode("ascii") + b"\0" + object_sha.encode("ascii") + b"\0")
            preserved_files += 1
    return {
        "base_ref": base_ref,
        "preserved_files": preserved_files,
        "preserved_digest": digest.hexdigest(),
        "removable_files": removable_files,
        "review_files": review_files,
    }


def read_decisions(
    path: Path | None, repository: Path, review_paths: list[dict[str, str]]
) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    resolved = reject_path_inside_git_repository(path.resolve(strict=True), repository, "As decisões de caminhos")
    decision_stat = resolved.stat()
    if not stat.S_ISREG(decision_stat.st_mode) or (os.name == "posix" and decision_stat.st_mode & 0o077):
        raise ValueError("As decisões precisam ser um arquivo regular e, em POSIX, ter permissão 0600.")
    document = json.loads(resolved.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or document.get("version") != 1
        or not isinstance(document.get("decisions"), list)
    ):
        raise ValueError("Formato das decisões privadas de caminho desconhecido.")
    candidates = {entry["path"] for entry in review_paths}
    decisions = {}
    for decision in document["decisions"]:
        if (
            not isinstance(decision, dict)
            or set(decision) != {"path", "decision", "reason"}
            or not isinstance(decision["decision"], str)
            or decision["decision"] not in {"remove", "keep"}
            or not isinstance(decision["path"], str)
            or not isinstance(decision["reason"], str)
            or not decision["reason"].strip()
            or decision["path"] not in candidates
            or decision["path"] in decisions
        ):
            raise ValueError("Uma decisão de caminho é inválida, duplicada ou não corresponde a um candidato.")
        decisions[decision["path"]] = {"decision": decision["decision"], "reason": decision["reason"].strip()}
    return decisions


def create_plan(repository: Path, base_ref: str, decisions_file: Path | None) -> dict:
    repository = repository.resolve(strict=True)
    git(repository, "rev-parse", "--git-dir")
    paths = history_paths(repository)
    automatic_remove_paths = []
    review_paths = []
    for path in sorted(paths):
        classification, reason = classify_path(path)
        if classification == "remove":
            automatic_remove_paths.append(path)
        elif classification == "review":
            review_paths.append({"path": path, "reason": reason})
    decisions = read_decisions(decisions_file, repository, review_paths)
    reviewed_remove_paths = [
        {"path": path, "reason": decision["reason"]}
        for path, decision in sorted(decisions.items())
        if decision["decision"] == "remove"
    ]
    reviewed_keep_paths = [path for path, decision in sorted(decisions.items()) if decision["decision"] == "keep"]
    remove_paths = automatic_remove_paths + [entry["path"] for entry in reviewed_remove_paths]
    remove_paths.sort()
    unresolved_review_paths = [entry["path"] for entry in review_paths if entry["path"] not in decisions]
    return {
        "version": 2,
        "refs_before": repository_refs(repository),
        "base_ref": base_ref,
        "current_tree_before": current_tree_summary(repository, base_ref, set(remove_paths)),
        "object_storage_before_bytes": object_storage_bytes(repository),
        "history_path_counts": {
            "seen": len(paths),
            "remove_total": len(remove_paths),
            "automatic_remove": len(automatic_remove_paths),
            "review_candidates": len(review_paths),
            "review_decisions_remove": len(reviewed_remove_paths),
            "review_decisions_keep": len(reviewed_keep_paths),
            "pending_review": len(unresolved_review_paths),
            "keep": len(paths) - len(automatic_remove_paths) - len(review_paths),
        },
        "remove_paths": remove_paths,
        "review_paths": review_paths,
        "reviewed_remove_paths": reviewed_remove_paths,
        "reviewed_keep_paths": reviewed_keep_paths,
        "unresolved_review_paths": unresolved_review_paths,
        "note": (
            "Somente plano de leitura. Revise os caminhos localmente; não inclua este arquivo nem a lista de caminhos "
            "em um commit público. A reescrita depende de backup completo verificado e autorização específica."
        ),
    }


def require_outside_repository(path: Path, repository: Path, argument: str) -> Path:
    return reject_path_inside_git_repository(path, repository, argument)


def write_new_json(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument(
        "output", type=Path, help="Plano privado; deve ficar fora do repositório e não será sobrescrito."
    )
    parser.add_argument("--base-ref", default="HEAD", help="Ref usada para comparar a árvore de código atual.")
    parser.add_argument(
        "--decisions-file",
        type=Path,
        help="JSON privado externo ao repositório com decisões explícitas para cada caminho ambíguo.",
    )
    parser.add_argument(
        "--paths-output",
        type=Path,
        help="Lista privada de caminhos para filter-repo; um caminho por linha, sem sobrescrita.",
    )
    args = parser.parse_args()
    repository = args.repository.resolve(strict=True)
    try:
        plan = create_plan(repository, args.base_ref, args.decisions_file)
        output_path = require_outside_repository(args.output, repository, "O plano")
        paths_path = (
            require_outside_repository(args.paths_output, repository, "A lista de caminhos")
            if args.paths_output
            else None
        )
        if output_path.exists() or (paths_path and paths_path.exists()):
            raise ValueError("O plano e a lista de caminhos são criados sem sobrescrita.")
        if paths_path and plan["remove_paths"]:
            if any("\n" in path or "\r" in path for path in plan["remove_paths"]):
                raise ValueError("Há caminho com quebra de linha; não é seguro gerar uma lista do filter-repo.")
            descriptor = os.open(paths_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as paths_file:
                paths_file.writelines(f"{path}\n" for path in plan["remove_paths"])
        write_new_json(output_path, plan)
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        parser.error(str(error))
    counts = plan["history_path_counts"]
    print(
        "Plano criado sem modificar refs: "
        f"{len(plan['refs_before'])} refs, {counts['remove_total']} remoções propostas, "
        f"{counts['review_candidates']} candidatos, {counts['pending_review']} sem decisão, "
        f"{counts['keep']} preservados."
    )


if __name__ == "__main__":
    main()
