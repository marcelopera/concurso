"""One CLI for extraction, review and deterministic catalog generation."""

import argparse
import importlib
import json
import os
from dataclasses import replace
from pathlib import Path

from .common import js
from .config import Settings, execution
from .extractors import REGISTRY, SYLLABUS

STAGES = (
    "cache",
    "extract",
    "syllabus",
    "answers",
    "review",
    "consolidate",
    "index",
    "validate",
    "render",
    "report",
    "build",
)


def run(stage, settings, boards):
    if stage in {"extract", "syllabus"}:
        settings = replace(settings, boards=tuple(boards))
    with execution(settings):
        if stage == "build":
            # Build consumes the canonical source; extraction and review are explicit.
            for name in ("consolidate", "index", "validate", "report"):
                run(name, settings, boards)
            return
        if stage == "report":
            report = json.loads((settings.output_dir / "relatorio.json").read_text(encoding="utf-8"))
            lines = [f"# Execução {settings.run_id}", "", "Estatísticas geradas de `generated/relatorio.json`.", ""]
            for key, value in report.items():
                if isinstance(value, (int, str)):
                    lines.append(f"- {key}: {value}")
            lines += [
                "",
                "Proveniência: consultar os manifestos dos lotes de entrada. Revisão semântica não é inferida pelo build.",
                "",
            ]
            (settings.output_dir / "run.md").write_text("\n".join(lines), encoding="utf-8")
            return
        if stage in {"extract", "syllabus"}:
            registry = REGISTRY if stage == "extract" else SYLLABUS
            for module in dict.fromkeys(registry[b] for b in boards if b in registry):
                importlib.import_module(f".extractors.{module}", __package__).main()
        else:
            module = "gabaritos" if stage == "answers" else stage
            importlib.import_module(f".stages.{module}", __package__).main()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--library", type=Path, default=Path(os.environ.get("BIBLIOTECA_DIR", "biblioteca-concursos")))
    parser.add_argument("--board", action="append", choices=REGISTRY)
    parser.add_argument("--repair-ce", action="store_true", help="Revisar fronteiras C/E usando o cache geométrico.")
    args = parser.parse_args(argv)
    settings = Settings(args.data_root.resolve(), args.library.resolve(), args.run_id, args.repair_ce)
    for folder in (settings.run_dir / "lotes", settings.run_dir / "paginas", settings.output_dir):
        folder.mkdir(parents=True, exist_ok=True)
    run(args.stage, settings, args.board or list(REGISTRY))
    print(js({"stage": args.stage, "run_id": settings.run_id}))


if __name__ == "__main__":
    main()
