"""Build the canonical snapshot from immutable raw batches and explicit reviews."""

import json

from ..common import js, norm, question_text, readjl, relative_file, writejl
from ..config import config
from .repair_ce import reconstruct
from .validate import validate_records


def documents(rows):
    result = []
    seen = set()
    for row in rows:
        row = dict(row)
        name = relative_file(row.get("arquivo_relativo") or row["arquivo"])
        # Old manifests sometimes include the library directory as a prefix.
        if name.startswith("biblioteca-concursos/"):
            name = name.removeprefix("biblioteca-concursos/")
        row.update(arquivo=name, arquivo_relativo=name)
        if row["documento_id"] in seen:
            raise ValueError("documento_id duplicado no manifesto.")
        seen.add(row["documento_id"])
        result.append(row)
    return result


def reject_absolute_paths(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"arquivo", "arquivo_pdf", "arquivo_relativo", "arquivo_local", "arquivo_imagem"} and item:
                relative_file(item)
            reject_absolute_paths(item)
    elif isinstance(value, list):
        for item in value:
            reject_absolute_paths(item)


def main():
    settings = config()
    raw = settings.run_dir / "lotes"
    manifest = documents(json.loads((settings.run_dir / "documentos.json").read_text(encoding="utf-8")))
    questions = {}
    for path in sorted(raw.glob("*.questoes.jsonl")):
        for row in readjl(path):
            key = row["documento_id"], str(row["numero_original"]), row.get("prova_id")
            if key in questions:
                raise ValueError(f"Questão duplicada nos lotes: {key}")
            questions[key] = row
    corrections = settings.run_dir / "correcoes_questoes.jsonl"
    if settings.repair_ce:

        def changed(row, reason):
            row.setdefault("correcoes_coordenador", []).append(reason)

        reconstruct(settings.run_dir, list(questions.values()), changed)
    if corrections.exists():
        for row in readjl(corrections):
            key = row["documento_id"], str(row["numero_original"]), row.get("prova_id")
            if key not in questions:
                raise ValueError(f"Correção sem questão de origem: {key}")
            questions[key] = row
    for path in sorted(raw.glob("*.enriquecimento.jsonl")):
        for row in readjl(path):
            keys = [k for k in questions if k[:2] == (row["documento_id"], str(row["numero_original"]))]
            if len(keys) != 1:
                raise ValueError("Enriquecimento sem ocorrência inequívoca.")
            for field in ("classificacoes", "habilidades"):
                if field in row:
                    questions[keys[0]][field] = row[field]
    records = {
        "questoes": list(questions.values()),
        "topicos": [r for p in sorted(raw.glob("*.topicos.jsonl")) for r in readjl(p)],
        "gabaritos": readjl(raw / "gabaritos.jsonl") if (raw / "gabaritos.jsonl").exists() else [],
    }
    for row in records["questoes"]:
        # Preserve rejected historical inferences as audit records, as the old
        # consolidator did. Only literal evidence enters the canonical labels.
        text = norm(question_text(row))
        for field in ("classificacoes", "habilidades"):
            accepted = []
            for candidate in row.get(field) or []:
                evidence = norm(candidate.get("trecho_evidencia"))
                if evidence and evidence in text:
                    accepted.append(candidate)
                else:
                    row.setdefault("enriquecimento_rejeitado", []).append(
                        {
                            "campo": field,
                            "registro": candidate,
                            "motivo": "Evidência não encontrada no conteúdo corrigido",
                        }
                    )
            row[field] = accepted
    for kind, rows in records.items():
        validate_records(kind, rows, manifest)
        reject_absolute_paths(rows)
    # Publish only after every input is valid. Raw batches are never modified.
    settings.canonical.mkdir(parents=True, exist_ok=True)
    (settings.canonical / "documentos.json").write_text(js(manifest) + "\n", encoding="utf-8")
    for kind, rows in records.items():
        writejl(settings.canonical / f"{kind}.jsonl", rows)
    print(js({kind: len(rows) for kind, rows in records.items()}))
