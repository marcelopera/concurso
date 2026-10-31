"""Initialize external plan data without replacing existing user progress."""

import json
import sqlite3

from estudo.mapping import __main__ as map_questions
from estudo.plans import load_plan
from estudo.services import plans as roadmap


def prepare_study(app, plan_file=None):
    if app.settings.study_db.exists():
        raise RuntimeError("O banco inicial já existe; recusei sobrescrevê-lo.")
    if not (plan_file or app.settings.plan_file):
        raise ValueError("Informe o arquivo do plano para inicializar o progresso.")
    load_plan(plan_file or app.settings.plan_file)
    app.init_db()
    roadmap.install(app.settings.study_db, plan_file or app.settings.plan_file)
    mapping = app.settings.study_db.parent / "vinculacao"
    links_file, report_file = mapping / "vinculos.jsonl", mapping / "relatorio.json"
    links = []
    with app.content_db() as catalog:
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
        map_questions.apply_links(links, report, app.settings.study_db)
    with sqlite3.connect(app.settings.study_db) as con:
        if not con.execute("SELECT count(*) FROM plan_units").fetchone()[0]:
            raise RuntimeError("O plano não contém aulas.")
        if con.execute("SELECT count(*) FROM lesson_questions").fetchone()[0] != len(links):
            raise RuntimeError("Quantidade de vínculos importados inesperada.")
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("O banco de estudo contém referências inválidas.")


def initialize_once(app, plan_file=None):
    if app.settings.study_db.exists():
        print(f"Progresso existente preservado: {app.settings.study_db}")
        return False
    prepare_study(app, plan_file)
    return True
