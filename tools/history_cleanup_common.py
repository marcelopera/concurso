"""Shared safeguards for private history-cleanup artifacts."""

import subprocess
from pathlib import Path


def reject_path_inside_git_repository(path: Path, repository: Path, label: str) -> Path:
    resolved = path.resolve()
    repository = repository.resolve()
    if resolved.is_relative_to(repository):
        raise ValueError(f"{label} precisa ficar fora do repositório.")

    probe = resolved if resolved.is_dir() else resolved.parent
    while not probe.exists():
        probe = probe.parent
    top_level = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if top_level.returncode == 0 and resolved.is_relative_to(Path(top_level.stdout.strip()).resolve()):
        raise ValueError(f"{label} precisa ficar fora de qualquer checkout Git.")

    git_dir = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--absolute-git-dir"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if git_dir.returncode == 0 and resolved.is_relative_to(Path(git_dir.stdout.strip()).resolve()):
        raise ValueError(f"{label} precisa ficar fora de qualquer diretório Git.")
    return resolved
