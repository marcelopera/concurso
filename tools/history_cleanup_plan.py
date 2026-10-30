"""List historical paths to remove, without modifying Git objects or refs."""

import argparse
import json
import re
import subprocess
from pathlib import Path

REMOVED = re.compile(
    r"^(?:base-questoes/|biblioteca-concursos/|sistema-estudo/dados/)|"
    r"(?:^|/)(?:execucoes|fontes-visuais|revisao-visual|piloto-[^/]+|evidencias[^/]*)(?:/|$)|"
    r"\.(?:pdf|png|jpe?g|log|sqlite(?:-wal|-shm)?)$",
    re.I,
)


def plan(repository):
    result = subprocess.run(
        ["git", "-c", "core.quotePath=false", "log", "--all", "--format=", "--name-only"],
        cwd=repository,
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
    )
    paths = sorted({name for name in result.stdout.splitlines() if name and REMOVED.search(name)})
    refs = subprocess.run(
        ["git", "show-ref"], cwd=repository, capture_output=True, check=True, text=True
    ).stdout.splitlines()
    return {
        "version": 1,
        "refs_before": refs,
        "remove_paths": paths,
        "note": "Somente plano. Executar filter-repo em clone separado após merge e backup verificado.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(plan(args.repository), output, ensure_ascii=False, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
