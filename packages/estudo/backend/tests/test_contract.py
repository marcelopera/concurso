import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

from concurso_contracts import resource_file
from concurso_contracts.catalog.contrato import UNKNOWN, current_commit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.dataset_manifest import inventory, verify


class ContractTests(unittest.TestCase):
    def test_generator_commit_requires_its_source_to_be_tracked_and_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def git(*arguments):
                return subprocess.run(
                    ["git", "-C", str(root), *arguments], check=True, capture_output=True, text=True
                ).stdout.strip()

            git("init")
            git("config", "core.autocrlf", "false")
            (root / ".gitignore").write_text(".venv/\n", encoding="utf-8")
            tracked_source = root / "generator.py"
            tracked_source.write_text("# synthetic generator\n", encoding="utf-8")
            git("add", ".gitignore", "generator.py")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
            self.assertEqual(current_commit(tracked_source), git("rev-parse", "HEAD"))

            installed_source = root / ".venv" / "lib" / "installed_generator.py"
            installed_source.parent.mkdir(parents=True)
            installed_source.write_text("# untracked installed wheel\n", encoding="utf-8")
            self.assertEqual(current_commit(installed_source), UNKNOWN)

            tracked_source.write_text("# modified generator\n", encoding="utf-8")
            self.assertEqual(current_commit(tracked_source), UNKNOWN)

    def test_synthetic_extraction_matches_schema_and_invalid_sources_are_rejected(self):
        schema = json.loads(resource_file("schemas", "extraction-question.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        record = dict(
            documento_id="demo",
            prova_id="demo",
            numero_original="1",
            formato="certo_errado",
            enunciado_original="Um mais um é dois.",
            alternativas=[],
            contextos=[],
            paginas_pdf=[1],
            regioes_fonte=[dict(pagina=1, bbox=[0, 0, 100, 100])],
            status_extracao="extraido",
            alertas=[],
            metodo_extracao="fixture sintetica",
            agente="teste",
        )
        jsonschema.validate(record, schema)
        for key, value in [("paginas_pdf", [0]), ("formato", "invalido"), ("numero_original", 1)]:
            invalid = {**record, key: value}
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(invalid, schema)

    def test_manifest_preserves_hashes_and_rejects_changed_or_external_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "lote.jsonl").write_text('{"origem":"sintetica"}\n', encoding="utf-8")
            manifest = inventory(root, {"status": "synthetic"})
            self.assertEqual(manifest["files"][0]["path"], "lote.jsonl")
            verify(root, manifest)
            changed = copy.deepcopy(manifest)
            changed["files"][0]["path"] = "../fora"
            with self.assertRaises(ValueError):
                verify(root, changed)
            (root / "lote.jsonl").write_text("alterado", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify(root, manifest)
