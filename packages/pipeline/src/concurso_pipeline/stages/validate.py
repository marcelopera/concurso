"""Schema, source, identity and SQLite integrity validation without private PDFs."""

import json
import sqlite3
from contextlib import closing

import jsonschema

from concurso_contracts.catalog.contrato import CATALOG_VERSION, hash_sources, serialize_sources, validate_catalog

from ..common import norm, question_text, readjl, relative_file
from ..config import catalog_source_hashes, config, resource_file

SCHEMAS = {"questoes": "question", "topicos": "topic", "gabaritos": "answer"}


def validate_records(kind, records, documents):
    schema = json.loads(resource_file("schemas", f"extraction-{SCHEMAS[kind]}.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    docs = {d["documento_id"]: d for d in documents}
    for row in records:
        validator.validate(row)
        document = docs[row["documento_id"]]
        relative_file(document["arquivo"])
        if any(p > document["paginas"] for p in row["paginas_pdf"]):
            raise ValueError("Página fora do documento.")
        for region in row["regioes_fonte"]:
            x0, y0, x1, y1 = region["bbox"]
            if region["pagina"] > document["paginas"] or x1 < x0 or y1 < y0:
                raise ValueError("Região de origem inválida.")
        if kind == "questoes":
            text = norm(question_text(row))
            for evidence in row.get("habilidades", []) + row.get("classificacoes", []):
                if not norm(evidence["trecho_evidencia"]) or norm(evidence["trecho_evidencia"]) not in text:
                    raise ValueError("Evidência não encontrada no conteúdo da questão.")


def main():
    settings = config()
    docs = json.loads((settings.canonical / "documentos.json").read_text(encoding="utf-8"))
    for kind in SCHEMAS:
        validate_records(kind, readjl(settings.canonical / f"{kind}.jsonl"), docs)
    with closing(sqlite3.connect(f"{(settings.output_dir / 'conteudo.sqlite').as_uri()}?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA user_version").fetchone()[0] != CATALOG_VERSION:
            raise ValueError("Versão do catálogo inválida.")
        validate_catalog(db)
        stored_sources = db.execute("SELECT hash_fontes, fontes_json FROM schema_meta").fetchone()
        current_sources = catalog_source_hashes(settings)
        if stored_sources != (hash_sources(current_sources), serialize_sources(current_sources)):
            raise ValueError(
                "O catálogo diverge das fontes canônicas, do manifesto ou dos metadados atuais da execução."
            )
        if (
            db.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
            or db.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise ValueError("Integridade do catálogo inválida.")
        for table in ("questoes", "topicos"):
            if (
                db.execute(f"SELECT count(*) FROM {table}").fetchone()
                != db.execute(f"SELECT count(*) FROM {table}_fts").fetchone()
            ):
                raise ValueError("Índice de busca incompleto.")
    print("Contrato, fontes e catálogo válidos.")
