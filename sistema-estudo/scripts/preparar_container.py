"""Prepare portable catalog paths and a fresh, populated study database at build time."""

import json
import sqlite3
import sys
from pathlib import Path

app = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(app))
import map_questions
import roadmap
import server


def prepare_study():
    if server.STUDY_DB.exists():
        raise RuntimeError("O banco inicial já existe; recusei sobrescrevê-lo.")
    server.init_db()
    roadmap.install(server.STUDY_DB)
    mapping = app / "dados" / "vinculacao"
    links_file, report_file = mapping / "vinculos.jsonl", mapping / "relatorio.json"
    links = []
    with server.content_db() as catalog:
        has_meta = catalog.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_meta'").fetchone()
        meta_columns = {row[1] for row in catalog.execute("PRAGMA table_info(schema_meta)")} if has_meta else set()
        is_demo = bool(
            "origem" in meta_columns
            and catalog.execute("SELECT 1 FROM schema_meta WHERE origem='demonstracao sintetica'").fetchone()
        )
        available_ids = {row[0] for row in catalog.execute("SELECT ocorrencia_id FROM ocorrencias")}
    if links_file.is_file() and report_file.is_file() and not is_demo:
        links = [json.loads(line) for line in links_file.read_text(encoding="utf-8").splitlines() if line]
        if any(link["occurrence_id"] not in available_ids for link in links):
            raise RuntimeError("Os vínculos privados não correspondem ao catálogo selecionado.")
        report = json.loads(report_file.read_text(encoding="utf-8"))
        map_questions.apply_links(links, report, server.STUDY_DB)
    with sqlite3.connect(server.STUDY_DB) as con:
        if not con.execute("SELECT count(*) FROM plan_units").fetchone()[0]:
            raise RuntimeError("O plano não contém aulas.")
        if con.execute("SELECT count(*) FROM lesson_questions").fetchone()[0] != len(links):
            raise RuntimeError("Quantidade de vínculos importados inesperada.")
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("O banco de estudo contém referências inválidas.")


if __name__ == "__main__":
    prepare_study()
