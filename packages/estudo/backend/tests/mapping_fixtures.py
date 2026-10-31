"""Build small, redistributable synthetic catalogs for mapping regressions."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from concurso_contracts.catalog.criar_demo import criar

FIXTURE = Path(__file__).parent / "fixtures" / "mapping_questions.json"


def create_mapping_catalog(destination: Path) -> dict[str, dict]:
    """Create public synthetic questions that exercise mapping and session behavior."""
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
    destination = Path(destination)
    criar(destination)
    with closing(sqlite3.connect(destination)) as con, con:
        origin = "fixtures sintéticas de regressão"
        con.execute("UPDATE schema_meta SET origem=?", (origin,))
        for execution_id, metadata_json in con.execute("SELECT execucao_id,metadados_json FROM execucoes").fetchall():
            metadata = json.loads(metadata_json or "{}")
            metadata["origem"] = origin
            con.execute(
                "UPDATE execucoes SET metadados_json=? WHERE execucao_id=?",
                (json.dumps(metadata, ensure_ascii=False), execution_id),
            )
        for case in cases["cases"]:
            con.execute(
                "UPDATE questoes SET enunciado_original=?,texto_para_busca=? WHERE questao_id=?",
                (case["text"], case["text"], case["question_id"]),
            )
            con.execute(
                "UPDATE ocorrencias SET disciplina_original=? WHERE ocorrencia_id=?",
                (case["discipline"], case["occurrence_id"]),
            )

        for number in range(1, cases["bulk_count"] + 1):
            occurrence_id = f"o-large-{number:03d}"
            question_id = f"q-large-{number:03d}"
            text = cases["bulk_text"].format(number=number)
            con.execute(
                "INSERT INTO questoes(questao_id,formato,enunciado_original,texto_para_busca,hash_texto,registro_json) "
                "VALUES(?,?,?,?,?,?)",
                (question_id, "multipla_escolha", text, text, f"synthetic-hash-{number:03d}", "{}"),
            )
            con.execute(
                "INSERT INTO ocorrencias(ocorrencia_id,questao_id,prova_id,documento_id,numero_original,"
                "disciplina_original,paginas_json,status_extracao) VALUES(?,?,?,?,?,?,?,?)",
                (
                    occurrence_id,
                    question_id,
                    "p1",
                    "doc1",
                    str(number + 20),
                    "Língua Portuguesa",
                    "[]",
                    "extraido",
                ),
            )
            for order, (label, answer) in enumerate((("A", "1"), ("B", "2"))):
                con.execute(
                    "INSERT INTO alternativas VALUES(?,?,?,?,?)",
                    (f"{question_id}-{label}", question_id, label, order, answer),
                )
            answer_id = f"g-large-{number:03d}"
            con.execute(
                "INSERT INTO gabaritos(gabarito_registro_id,documento_id,concurso,numero_original,"
                "resposta_publicada,situacao_item,natureza_gabarito) VALUES(?,?,?,?,?,?,?)",
                (answer_id, "doc1", "Questões sintéticas", str(number + 20), "A", "valido", "definitivo"),
            )
            con.execute(
                "INSERT INTO ocorrencia_gabarito VALUES(?,?,?,?)",
                (occurrence_id, answer_id, "associado", "fixture-sintetica"),
            )
    return {case["occurrence_id"]: case for case in cases["cases"]}
