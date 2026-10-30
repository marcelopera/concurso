"""Copy legacy inputs into a new private run; never alter or publish the originals."""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from concurso_pipeline.common import js
from concurso_pipeline.config import Settings
from concurso_pipeline.stages.review import documents
from tools.dataset_manifest import inventory, verify


def migrate(source, settings):
    source = source.resolve(strict=True)
    target = settings.run_dir
    target.mkdir(parents=True, exist_ok=False)
    (target / "lotes").mkdir()
    provenance = {
        "status": "legacy-unrecorded",
        "original_run": source.name,
        "model": None,
        "version": None,
        "prompt": None,
        "date": None,
        "note": "Importação preserva os lotes; recuperar proveniência nos registros originais antes de distribuir.",
    }
    for path in sorted((source / "lotes").glob("*.jsonl")):
        shutil.copyfile(path, target / "lotes" / path.name)
    if (source / "correcoes_questoes.jsonl").exists():
        shutil.copyfile(source / "correcoes_questoes.jsonl", target / "correcoes_questoes.jsonl")
    manifest = documents(json.loads((source / "documentos.json").read_text(encoding="utf-8")))
    (target / "documentos.json").write_text(js(manifest) + "\n", encoding="utf-8")
    original = inventory(source / "lotes", provenance)
    copied = {p.name for p in (target / "lotes").iterdir()}
    original["files"] = [entry for entry in original["files"] if entry["path"] in copied]
    verify(target / "lotes", original)
    (target / "MANIFEST.raw.json").write_text(js(original) + "\n", encoding="utf-8")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Execução antiga, contendo lotes/ e documentos.json.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    args = parser.parse_args()
    print(migrate(args.source, Settings(args.data_root.resolve(), Path("biblioteca-concursos").resolve(), args.run_id)))


if __name__ == "__main__":
    main()
