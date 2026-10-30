"""Rank distinct question content for practice using immutable attempt history."""

from estudo.repositories import question_links


def session_pool(study, content, lesson_id, size=12):
    items, history = question_links.session_candidates(study, content, lesson_id)
    if not items:
        return {}
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
