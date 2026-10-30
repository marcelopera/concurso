"""Golden checks use generated, original synthetic PDFs, never exam material."""

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from concurso_pipeline.__main__ import run
from concurso_pipeline.config import Settings
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from test_pipeline import document

from concurso_pipeline.common import js, readjl


def write_pdf(path, lines):
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    content = DecodedStreamObject()
    commands = ["BT /F1 8 Tf 12 TL 30 740 Td"]
    for line in lines:
        line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({line}) Tj T*")
    commands.append("ET")
    content.set_data("\n".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(content)
    path.parent.mkdir(parents=True)
    with path.open("wb") as output:
        writer.write(output)


class ExtractorGoldenTests(unittest.TestCase):
    def test_six_boards_from_pdf_through_review_and_catalog(self):
        stem = "Uma unidade mais outra resulta em duas unidades."
        expected = json.loads((Path(__file__).parent / "fixtures/golden.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = Settings(root / "data", root / "library", "golden-03")
            (settings.run_dir / "lotes").mkdir(parents=True)
            (settings.run_dir / "paginas").mkdir()
            settings.output_dir.mkdir()
            docs = [document(board) for board in expected]
            for doc in docs:
                board = doc["banca"]
                if board == "Cebraspe":
                    lines = ["Julgue os itens seguintes.", "1 " + stem]
                else:
                    marker = {"FGV": "1", "Fundatec": "QUESTAO 1", "ESAF": "1 -"}.get(board, "1.")
                    lines = [marker] if board in {"FGV", "Fundatec"} else []
                    lines += [stem if lines else marker + " " + stem]
                    lines += [
                        (f"{letter})" if board in {"Fundatec", "ESAF"} else f"({letter})") + f" Opcao {letter}."
                        for letter in "ABCDE"
                    ]
                write_pdf(settings.library / doc["arquivo"], lines)
            (settings.run_dir / "documentos.json").write_text(js(docs), encoding="utf-8")
            with redirect_stdout(StringIO()):
                run("cache", settings, list(expected))
                run("extract", settings, list(expected))
                run("review", settings, list(expected))
                run("build", settings, list(expected))
            records = readjl(settings.output_dir / "questoes.jsonl")
            self.assertEqual(len(records), 6)
            for row in records:
                with self.subTest(board=row["banca"]):
                    golden = expected[row["banca"]]
                    self.assertEqual(row["numero_original"], "1")
                    self.assertEqual(row["formato"], golden["formato"])
                    self.assertEqual(row["paginas_pdf"], [1])
                    self.assertEqual(row["alternativas"], golden["alternativas"])
                    self.assertTrue(row["enunciado_original"].startswith(stem))
                    self.assertTrue(row["regioes_fonte"])
            # Selecting one board must not rewrite batches of another board.
            other = settings.run_dir / "lotes/fgv.questoes.jsonl"
            original = other.read_bytes()
            with redirect_stdout(StringIO()):
                run("extract", settings, ["FCC"])
                run("extract", settings, ["Fundatec"])
                run("review", settings, list(expected))
                run("build", settings, list(expected))
            self.assertEqual(other.read_bytes(), original)
            self.assertEqual(
                {r["ocorrencia_id"] for r in readjl(settings.output_dir / "questoes.jsonl")},
                {r["ocorrencia_id"] for r in records},
            )


if __name__ == "__main__":
    unittest.main()
