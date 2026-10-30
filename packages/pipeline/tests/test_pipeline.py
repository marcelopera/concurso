import copy
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from io import StringIO
from pathlib import Path

from concurso_pipeline.__main__ import run
from concurso_pipeline.config import Settings, execution, source_file
from concurso_pipeline.stages.review import documents
from concurso_pipeline.stages.validate import validate_records

from concurso_pipeline.common import expected_count, ident, js, norm, readjl, writejl
from tools.dataset_manifest import verify
from tools.import_legacy_pipeline import migrate


def question(document="doc_Cebraspe", number="1"):
    return dict(
        documento_id=document,
        prova_id=document,
        numero_original=number,
        formato="certo_errado",
        enunciado_original="Uma unidade somada a outra resulta em duas unidades.",
        texto_original_completo="Uma unidade somada a outra resulta em duas unidades.",
        alternativas=[],
        contextos=[],
        paginas_pdf=[1],
        regioes_fonte=[dict(pagina=1, bbox=[0, 0, 100, 100])],
        status_extracao="extraido",
        alertas=[],
        metodo_extracao="fixture sintética",
        agente="teste",
    )


def document(board):
    return dict(
        documento_id=f"doc_{board}",
        sha256=hashlib.sha256(board.encode()).hexdigest(),
        tipo="provas",
        banca=board,
        concurso="sintetico",
        titulo="Prova fictícia",
        nome="unico",
        arquivo=f"{board}/prova.pdf",
        arquivo_relativo=f"{board}/prova.pdf",
        paginas=1,
        url=None,
    )


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.settings = Settings(self.root / "data", self.root / "library", "teste-02")
        for folder in (self.settings.run_dir / "lotes", self.settings.output_dir):
            folder.mkdir(parents=True)
        self.docs = [document(b) for b in ("Cebraspe", "FCC", "ESAF", "FGV", "Fundatec", "Vunesp")]
        (self.settings.run_dir / "documentos.json").write_text(js(self.docs), encoding="utf-8")
        writejl(
            self.settings.run_dir / "lotes/sintetico.questoes.jsonl", [question(d["documento_id"]) for d in self.docs]
        )

    def stage(self, name):
        with redirect_stdout(StringIO()):
            run(name, self.settings, ["Cebraspe"])

    def test_rebuild_is_byte_identical_and_text_corrections_preserve_historical_occurrence_ids(self):
        self.stage("review")
        self.stage("build")
        first = {
            p.relative_to(self.settings.output_dir): p.read_bytes()
            for p in self.settings.output_dir.rglob("*")
            if p.is_file()
        }
        self.stage("build")
        second = {
            p.relative_to(self.settings.output_dir): p.read_bytes()
            for p in self.settings.output_dir.rglob("*")
            if p.is_file()
        }
        self.assertEqual(first, second)
        before = {r["documento_id"]: r["ocorrencia_id"] for r in readjl(self.settings.output_dir / "questoes.jsonl")}
        corrected = question()
        corrected["enunciado_original"] = corrected["texto_original_completo"] = (
            "Texto corrigido de forma independente."
        )
        writejl(self.settings.run_dir / "correcoes_questoes.jsonl", [corrected])
        self.stage("review")
        self.stage("build")
        after = {r["documento_id"]: r["ocorrencia_id"] for r in readjl(self.settings.output_dir / "questoes.jsonl")}
        self.assertEqual(before, after)
        legacy = "o_" + hashlib.sha256("doc_Cebraspe\x1fdoc_Cebraspe\x1f1".encode()).hexdigest()[:24]
        self.assertEqual(after["doc_Cebraspe"], legacy)
        self.assertEqual(ident("o", "doc_Cebraspe", "doc_Cebraspe", "1"), legacy)
        with closing(sqlite3.connect(self.settings.output_dir / "conteudo.sqlite")) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM ocorrencias").fetchone()[0], 6)
            self.assertTrue(
                all(not Path(r[0]).is_absolute() for r in db.execute("SELECT arquivo_local FROM documentos"))
            )
        for p in self.settings.output_dir.rglob("*"):
            if p.is_file() and p.suffix in {".jsonl", ".json", ".csv", ".html"}:
                self.assertNotIn(str(self.root), p.read_text(encoding="utf-8-sig"))

    def test_cli_runs_from_another_directory_with_explicit_paths(self):
        self.stage("review")
        env = dict(os.environ)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "concurso_pipeline",
                "build",
                "--run-id",
                self.settings.run_id,
                "--data-root",
                str(self.settings.data_root),
                "--library",
                str(self.settings.library),
            ],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.settings.output_dir / "index.html").is_file())

    def test_review_rejects_duplicate_occurrences_invalid_pages_and_nonliteral_evidence(self):
        duplicate = self.settings.run_dir / "lotes/duplicate.questoes.jsonl"
        writejl(duplicate, [question()])
        with self.assertRaises(ValueError):
            self.stage("review")
        duplicate.unlink()
        invalid = question()
        invalid["paginas_pdf"] = [2]
        with self.assertRaises(ValueError):
            validate_records("questoes", [invalid], self.docs)
        invalid = question()
        invalid["habilidades"] = [dict(trecho_evidencia="Conteúdo inexistente", origem="teste", confianca="alta")]
        with self.assertRaises(ValueError):
            validate_records("questoes", [invalid], self.docs)

    def test_shared_unicode_normalization_and_portable_manifest(self):
        self.assertEqual(norm("  ＡÇÃＯ\nStraße  "), norm("ação strasse"))
        self.assertEqual(expected_count("Contém sessenta e cinco questões"), 65)
        self.assertEqual(expected_count("Contém 100 questões"), 100)
        for path in ("../fora.pdf", "/fora.pdf", "D:/fora.pdf", "//host/share/a.pdf"):
            with self.assertRaises(ValueError):
                documents([{**self.docs[0], "arquivo": path, "arquivo_relativo": path}])
        self.settings.library.mkdir()
        with execution(self.settings):
            with self.assertRaises(ValueError):
                source_file(self.docs[0])
        with self.assertRaises(ValueError):
            Settings(self.root, self.root, "../../outside")

    def test_topic_and_answer_contracts(self):
        base = dict(
            documento_id=self.docs[0]["documento_id"],
            paginas_pdf=[1],
            regioes_fonte=[dict(pagina=1, bbox=[0, 0, 100, 100])],
        )
        topic = dict(
            base,
            texto_original="Conteúdo fictício",
            status_extracao="extraido",
            alertas=[],
            metodo_extracao="teste",
            agente="teste",
        )
        answer = dict(
            base,
            concurso="sintetico",
            numero_original="1",
            resposta_publicada="C",
            situacao_item="valido",
            natureza_gabarito="definitivo",
            cargo_original="Cargo fictício",
        )
        validate_records("topicos", [topic], self.docs)
        validate_records("gabaritos", [answer], self.docs)
        for kind, row in (("topicos", topic), ("gabaritos", answer)):
            invalid = copy.deepcopy(row)
            invalid["regioes_fonte"][0]["bbox"] = [10, 10, 0, 0]
            with self.assertRaises(ValueError):
                validate_records(kind, [invalid], self.docs)

    def test_legacy_import_preserves_raw_hashes_and_refuses_overwrite(self):
        target = Settings(self.root / "imported", self.settings.library, "legacy")
        source = self.settings.run_dir
        original = (source / "lotes/sintetico.questoes.jsonl").read_bytes()
        migrate(source, target)
        manifest = json.loads((target.run_dir / "MANIFEST.raw.json").read_text(encoding="utf-8"))
        verify(target.run_dir / "lotes", manifest)
        self.assertEqual(manifest["provenance"]["status"], "legacy-unrecorded")
        self.assertEqual((source / "lotes/sintetico.questoes.jsonl").read_bytes(), original)
        with self.assertRaises(FileExistsError):
            migrate(source, target)
        (target.run_dir / "lotes/sintetico.questoes.jsonl").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            verify(target.run_dir / "lotes", manifest)

    def test_review_repairs_ce_boundaries_from_geometry(self):
        from dataclasses import replace

        settings = replace(self.settings, repair_ce=True)
        writejl(settings.run_dir / "lotes/sintetico.questoes.jsonl", [question()])
        cache = settings.run_dir / "paginas"
        cache.mkdir()
        text = "Uma unidade mais outra resulta em duas unidades."
        page = dict(
            numero=1,
            largura=600,
            altura=800,
            linhas=[
                dict(texto="1 " + text, bbox=[28.3, 60, 280, 70]),
                dict(texto="Esta frase continua no mesmo item.", bbox=[46.18, 72, 280, 82]),
            ],
        )
        (cache / "doc_Cebraspe.json").write_text(js({"paginas": [page]}), encoding="utf-8")
        with redirect_stdout(StringIO()):
            run("review", settings, ["Cebraspe"])
        row = readjl(settings.canonical / "questoes.jsonl")[0]
        self.assertIn(text, row["enunciado_original"])
        self.assertIn("continua no mesmo item", row["enunciado_original"])
        self.assertTrue(row["correcoes_coordenador"])


if __name__ == "__main__":
    unittest.main()
