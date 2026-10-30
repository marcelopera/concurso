"""Reading linked collections, their provenance, and varied session selections."""

import json
from collections import defaultdict


def counts(con):
    return {r[0]: r[1] for r in con.execute("SELECT lesson_id,count(*) FROM lesson_questions GROUP BY lesson_id")}


def summary(con):
    row = con.execute(
        "SELECT report_json FROM question_mapping_runs ORDER BY created_at DESC,run_id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    report = json.loads(row[0])
    actual = counts(con)
    plan_lessons = {r[0] for r in con.execute("SELECT lesson_id FROM plan_units WHERE plan_id=?", (report["plan_id"],))}
    report["current_links"] = sum(actual.get(lid, 0) for lid in plan_lessons)
    report["current_lessons_with_questions"] = sum(actual.get(lid, 0) > 0 for lid in plan_lessons)
    report["gaps"] = [
        dict(lesson_id=r["lesson_id"], title=r["title"]) for r in report["lessons"] if not actual.get(r["lesson_id"], 0)
    ]
    return {k: v for k, v in report.items() if k not in ["lessons"]}


def lesson_mappings(con, lesson_id):
    result = {}
    for r in con.execute("SELECT * FROM lesson_question_mappings WHERE lesson_id=?", (lesson_id,)):
        mapping = dict(r)
        mapping["evidence"] = json.loads(mapping.pop("evidence_json"))
        mapping.pop("run_id", None)
        result[mapping["occurrence_id"]] = mapping
    return result


def content_items(con, occurrence_ids):
    """Batch equivalent of the read-only question loader; never returns answers."""
    if not occurrence_ids:
        return []
    rows = []
    for start in range(0, len(occurrence_ids), 300):
        ids = occurrence_ids[start : start + 300]
        marks = ",".join("?" for _ in ids)
        rows.extend(
            dict(r)
            for r in con.execute(
                f"""
            SELECT v.*,o.documento_id AS source_document_id,r.estado AS reference_state,
                   r.situacao_referencia,r.possui_publicacao_definitiva AS has_definitive
            FROM vw_questoes v JOIN ocorrencias o USING(ocorrencia_id)
            LEFT JOIN vw_gabaritos_referencia r USING(ocorrencia_id)
            WHERE v.ocorrencia_id IN ({marks})""",
                ids,
            )
        )
    qids = list({r["questao_id"] for r in rows})
    alts = defaultdict(list)
    contexts = defaultdict(list)
    for start in range(0, len(qids), 300):
        ids = qids[start : start + 300]
        marks = ",".join("?" for _ in ids)
        for r in con.execute(
            f"SELECT questao_id,rotulo,texto_original FROM alternativas WHERE questao_id IN ({marks}) ORDER BY ordem",
            ids,
        ):
            alts[r["questao_id"]].append(dict(r))
        for r in con.execute(
            f"SELECT qc.questao_id,c.texto_original FROM questao_contexto qc JOIN contextos c USING(contexto_id) WHERE qc.questao_id IN ({marks}) ORDER BY qc.ordem",
            ids,
        ):
            contexts[r["questao_id"]].append(r["texto_original"])
    by_id = {}
    for item in rows:
        item["alternatives"] = alts[item["questao_id"]]
        if item["formato"] == "certo_errado" and not item["alternatives"]:
            item["alternatives"] = [dict(rotulo="C", texto_original="Certo"), dict(rotulo="E", texto_original="Errado")]
        item["contexts"] = contexts[item["questao_id"]]
        item["reference_status"] = dict(
            state=item.pop("reference_state") or "sem referência consolidada",
            situation=item.pop("situacao_referencia"),
            has_definitive=bool(item.pop("has_definitive")),
            extraction=item["status_extracao"],
        )
        status = item["reference_status"]
        status["correctable"] = (
            status["state"] == "concordante"
            and status["situation"] == "valido"
            and status["has_definitive"]
            and status["extraction"] == "extraido"
        )
        by_id[item["ocorrencia_id"]] = item
    return [by_id[oid] for oid in occurrence_ids if oid in by_id]


def session_pool(study, content, lesson_id, size=12):
    ids = [
        r[0]
        for r in study.execute(
            "SELECT occurrence_id FROM lesson_questions WHERE lesson_id=? ORDER BY position,occurrence_id", (lesson_id,)
        )
    ]
    items = content_items(content, ids)
    if not items:
        return {}
    occurrence_to_question = dict(content.execute("SELECT ocorrencia_id,questao_id FROM ocorrencias"))
    history = {}
    for r in study.execute(
        "SELECT occurrence_id,correct,created_at FROM attempts ORDER BY created_at DESC,attempt_id DESC"
    ):
        qid = occurrence_to_question.get(r["occurrence_id"])
        if qid not in history:
            history[qid] = dict(count=0, last_correct=r["correct"], last_at=r["created_at"])
        history[qid]["count"] += 1
    best = {}
    for position, q in enumerate(items):
        if q["formato"] == "discursiva":
            continue
        qid = q["questao_id"]
        old = best.get(qid)
        if old is None or (not q["reference_status"]["correctable"], position) < (
            not old[1]["reference_status"]["correctable"],
            old[0],
        ):
            best[qid] = (position, q)
    ranked = []
    for qid, (position, q) in best.items():
        h = history.get(qid, dict(count=0, last_correct=None, last_at=""))
        priority = (
            not q["reference_status"]["correctable"],
            h["count"] > 0,
            h["last_correct"] == 1,
            h["last_at"],
            position,
        )
        ranked.append((priority, q["ocorrencia_id"]))
    ranked.sort()
    pool = [oid for _, oid in ranked[:size]]
    return dict(
        questionPool=pool,
        pretestOccurrenceId=pool[0] if pool else "",
        recallOccurrenceId=pool[1] if len(pool) > 1 else "",
        practiceOccurrenceIds=pool[2:] if len(pool) > 2 else pool,
        poolStrategy="Até 12 conteúdos distintos: prioridade para itens corrigíveis ainda não respondidos, depois erros e revisões mais antigas. Questões discursivas ficam para consulta na aula.",
    )
