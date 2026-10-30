"""Create a verified private checkout snapshot and Git mirror."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXCLUDED_COMPONENTS = frozenset(
    {
        ".aws",  # Local credentials are not part of the dataset backup.
        ".git",
        ".qa-tools",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "node_modules",
    }
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def excluded(relative: Path, excluded_components: frozenset[str] = EXCLUDED_COMPONENTS) -> bool:
    return any(part in excluded_components or part.endswith(".egg-info") for part in relative.parts)


def tree_manifest(root: Path, excluded_components: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Describe files, symlinks, and directories without following symlinks."""
    root = root.resolve(strict=True)
    files: list[dict[str, Any]] = []
    directories: list[str] = []
    for current, child_dirs, child_files in os.walk(root, followlinks=False):
        current_path = Path(current)
        child_dirs.sort()
        child_files.sort()
        kept_dirs: list[str] = []
        for name in child_dirs:
            path = current_path / name
            relative = path.relative_to(root)
            if excluded(relative, excluded_components):
                continue
            if path.is_symlink():
                files.append({"path": relative.as_posix(), "type": "symlink", "target": os.readlink(path)})
                continue
            directories.append(relative.as_posix())
            kept_dirs.append(name)
        child_dirs[:] = kept_dirs
        for name in child_files:
            path = current_path / name
            relative = path.relative_to(root)
            if excluded(relative, excluded_components):
                continue
            if path.is_symlink():
                files.append({"path": relative.as_posix(), "type": "symlink", "target": os.readlink(path)})
            elif path.is_file():
                files.append(
                    {
                        "path": relative.as_posix(),
                        "type": "file",
                        "bytes": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                )
            else:
                raise ValueError(f"Tipo de arquivo não suportado: {relative}")
    return {
        "manifest_version": 1,
        "directories": sorted(directories),
        "files": sorted(files, key=lambda item: item["path"]),
    }


def verify_tree(root: Path, expected: dict[str, Any]) -> None:
    """Require the actual tree to match the manifest exactly."""
    actual = tree_manifest(root)
    if actual != expected:
        expected_files = {entry["path"] for entry in expected["files"]}
        actual_files = {entry["path"] for entry in actual["files"]}
        expected_dirs = set(expected["directories"])
        actual_dirs = set(actual["directories"])
        missing = sorted((expected_files - actual_files) | (expected_dirs - actual_dirs))
        extra = sorted((actual_files - expected_files) | (actual_dirs - expected_dirs))
        changed = sorted(
            path
            for path in expected_files & actual_files
            if next(entry for entry in expected["files"] if entry["path"] == path)
            != next(entry for entry in actual["files"] if entry["path"] == path)
        )
        details = []
        if missing:
            details.append(f"ausentes: {', '.join(missing[:5])}")
        if extra:
            details.append(f"extras: {', '.join(extra[:5])}")
        if changed:
            details.append(f"divergentes: {', '.join(changed[:5])}")
        raise ValueError("Árvore divergente do manifesto (" + "; ".join(details) + ").")


def copy_tree(source: Path, destination: Path, excluded_components: frozenset[str]) -> None:
    """Copy a tree while preserving symlinks and excluding named components."""
    destination.mkdir(parents=True, exist_ok=False)
    for current, child_dirs, child_files in os.walk(source, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for name in sorted(child_dirs):
            source_path = current_path / name
            relative = source_path.relative_to(source)
            if excluded(relative, excluded_components):
                continue
            target_path = destination / relative
            if source_path.is_symlink():
                os.symlink(os.readlink(source_path), target_path)
            else:
                target_path.mkdir(exist_ok=True)
                kept_dirs.append(name)
        child_dirs[:] = kept_dirs
        for name in sorted(child_files):
            source_path = current_path / name
            relative = source_path.relative_to(source)
            if excluded(relative, excluded_components):
                continue
            target_path = destination / relative
            if source_path.is_symlink():
                os.symlink(os.readlink(source_path), target_path)
            elif source_path.is_file():
                shutil.copy2(source_path, target_path)
            else:
                raise ValueError(f"Tipo de arquivo não suportado: {relative}")


def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8")


def create_backup(source: Path, destination_root: Path, remote: str, run_id: str | None = None) -> Path:
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise ValueError("A origem precisa ser um diretório.")
    source_git = run_git(["git", "rev-parse", "--show-toplevel"], cwd=source).stdout.strip()
    if Path(source_git).resolve() != source:
        raise ValueError("A origem precisa ser a raiz do checkout Git.")

    destination_root = destination_root.expanduser().resolve()
    if destination_root == source or source in destination_root.parents:
        raise ValueError("O destino precisa ficar fora do checkout de origem.")
    if destination_root in source.parents:
        raise ValueError("O destino não pode conter a origem.")

    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not run_id or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in run_id
    ):
        raise ValueError("Identificador de execução inválido.")
    run_root = destination_root / run_id
    destination_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destination_root, 0o700)
    run_root.mkdir(mode=0o700, exist_ok=False)
    os.chmod(run_root, 0o700)
    evidence_dir = run_root / "evidence"
    evidence_dir.mkdir(mode=0o700)

    mirror = run_root / "remote.git"
    run_git(["git", "clone", "--mirror", remote, str(mirror)])
    fsck = run_git(["git", "fsck", "--full"], cwd=mirror)
    refs = run_git(["git", "show-ref"], cwd=mirror).stdout
    (evidence_dir / "git-fsck.txt").write_text(fsck.stdout + fsck.stderr, encoding="utf-8")
    (evidence_dir / "git-refs.txt").write_text(refs, encoding="utf-8")

    snapshot = run_root / "checkout-snapshot"
    source_before = tree_manifest(source, EXCLUDED_COMPONENTS)
    copy_tree(source, snapshot, EXCLUDED_COMPONENTS)
    source_after = tree_manifest(source, EXCLUDED_COMPONENTS)
    if source_after != source_before:
        raise ValueError("A origem mudou durante a cópia; o snapshot não é consistente.")
    verify_tree(snapshot, source_before)
    (evidence_dir / "checkout-manifest.json").write_text(
        json.dumps(source_before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    restored_files = 0
    with tempfile.TemporaryDirectory(prefix="restore-drill-", dir=evidence_dir) as temporary:
        restored = Path(temporary) / "restored"
        copy_tree(snapshot, restored, frozenset())
        verify_tree(restored, source_before)
        restored_files = len(source_before["files"])

    byte_count = sum(entry.get("bytes", 0) for entry in source_before["files"])
    report = {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source),
        "remote": remote,
        "mirror_fsck": "passed",
        "mirror_ref_count": len(refs.splitlines()),
        "checkout_manifest_files": len(source_before["files"]),
        "checkout_manifest_directories": len(source_before["directories"]),
        "checkout_manifest_bytes": byte_count,
        "excluded_components": sorted(EXCLUDED_COMPONENTS),
        "restore_drill": "passed",
        "restore_drill_files": restored_files,
        "provenance_status": "unknown",
        "provenance_note": "This utility verifies byte integrity only; it does not infer dataset provenance.",
    }
    (evidence_dir / "backup-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return run_root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Raiz do checkout que contém arquivos locais ignorados.")
    parser.add_argument("destination", type=Path, help="Diretório privado fora do checkout.")
    parser.add_argument("remote", help="URL do remoto Git para criar o espelho completo.")
    parser.add_argument("--run-id", help="Nome único para esta execução; por padrão, horário UTC.")
    args = parser.parse_args()
    run_root = create_backup(args.source, args.destination, args.remote, args.run_id)
    report = json.loads((run_root / "evidence" / "backup-report.json").read_text(encoding="utf-8"))
    print(
        "Backup privado criado: "
        f"{report['mirror_ref_count']} refs no espelho; "
        f"{report['checkout_manifest_files']} arquivos e {report['checkout_manifest_directories']} diretórios "
        f"no snapshot; fsck e ensaio de restauração aprovados."
    )


if __name__ == "__main__":
    main()
