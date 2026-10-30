"""Catalog use cases; dependencies are supplied by the composition root."""

from __future__ import annotations

from pathlib import Path, PureWindowsPath

from estudo.repositories import catalog as catalog_store


def exams(app) -> list[dict]:
    with app.content_db() as con:
        result = catalog_store.exams(con)
    return result


def exam_questions(app, exam_id: str) -> list[dict] | None:
    with app.content_db() as con:
        result = catalog_store.exam_questions(con, exam_id)
    return [app.question_for_client(item) for item in result] if result is not None else None


def safe_library_file(app, path_value: str | None) -> Path | None:
    if not path_value:
        return None
    try:
        parts = PureWindowsPath(path_value.replace("/", "\\")).parts
        markers = [i for i, part in enumerate(parts) if part.lower() == "biblioteca-concursos"]
        if markers:
            if len(markers) != 1:
                return None
            parts = parts[markers[0] + 1 :]
        elif PureWindowsPath(path_value).is_absolute() or Path(path_value).is_absolute():
            return None
        if not parts or any((part in ("..", ".") for part in parts)):
            return None
        target = app.settings.library_root.joinpath(*parts).resolve(strict=True)
        if not target.is_file() or not target.is_relative_to(app.settings.library_root):
            return None
        if target.suffix.lower() != ".pdf":
            return None
        return target
    except (OSError, RuntimeError, ValueError):
        return None


def content_question(app, occurrence_id: str, include_answer: bool = False) -> dict | None:
    with app.content_db() as con:
        result = catalog_store.content_question(con, occurrence_id, include_answer)
    return result


def question_for_client(app, item: dict, include_answer: bool = False) -> dict:
    out = {
        "occurrence_id": item["ocorrencia_id"],
        "question_id": item["questao_id"],
        "format": item.get("formato"),
        "stem": item.get("enunciado_original"),
        "search_text": item.get("texto_para_busca"),
        "contexts": item.get("contexts", []),
        "alternatives": [
            {"label": a.get("rotulo"), "text": a.get("texto_original")} for a in item.get("alternatives", [])
        ],
        "bank": item.get("banca"),
        "contest": item.get("concurso"),
        "exam_title": item.get("titulo"),
        "number": item.get("numero_original"),
        "block": item.get("bloco_original"),
        "discipline": item.get("disciplina_original"),
        "pages": app.json_load(item.get("paginas_json"), []),
        "source_document_id": item.get("source_document_id"),
        "status_extraction": item.get("status_extracao"),
        "reference_status": item.get("reference_status"),
        "mapping": item.get("mapping"),
    }
    if include_answer:
        out["reference_answer"] = item.get("resposta_referencia")
        out["source_answers"] = [
            {
                "answer": source.get("resposta_publicada"),
                "situation": source.get("situacao_item"),
                "nature": source.get("natureza_gabarito"),
                "pages": app.json_load(source.get("paginas_json"), []),
                "document_id": source.get("documento_id"),
                "document_title": source.get("document_title"),
            }
            for source in item.get("source_answers", [])
        ]
    return out


def question_page(
    app, search: str, bank: str, discipline: str, page: int, eligible_only: bool = True, limit: int = 24
) -> dict:
    with app.content_db() as con:
        result = catalog_store.question_page(con, search, bank, discipline, page, eligible_only, limit)
    result["items"] = [app.question_for_client(item) for item in result["items"]]
    return result


def library_docs(app, search: str = "") -> list[dict]:
    with app.content_db() as con:
        rows = catalog_store.documents(con)
    needle = search.strip().casefold()
    result = []
    for r in rows:
        path = app.safe_library_file(r["arquivo_local"])
        if path is None:
            continue
        data = dict(r)
        data["label"] = " · ".join(
            (x for x in [data.get("concurso"), data.get("banca"), data.get("nome") or data.get("titulo")] if x)
        )
        if needle and needle not in " ".join((str(x or "") for x in data.values())).casefold():
            continue
        data.pop("arquivo_local", None)
        result.append(data)
    return result[:160]


def associated_snapshot(app, occurrence_id: str) -> dict:
    with app.content_db() as con:
        result = catalog_store.associated_snapshot(con, occurrence_id)
    return result


def health(app):
    with app.content_db() as con:
        count = catalog_store.occurrence_count(con)[0]
    return {"ok": True, "content_occurrences": count}


def library_file(app, document_id):
    with app.content_db() as con:
        document = catalog_store.document(con, document_id)
    return safe_library_file(app, document["arquivo_local"] if document else None)
