"""Read-only catalog queries. No HTTP or application-service dependencies."""


def document(con, document_id):
    return con.execute("SELECT arquivo_local,nome FROM documentos WHERE documento_id=?", (document_id,)).fetchone()


def documents(con):
    return con.execute(
        """
        SELECT documento_id,tipo,banca,concurso,titulo,nome,arquivo_local,paginas FROM documentos WHERE
        lower(arquivo_local) LIKE '%.pdf' ORDER BY concurso,banca,tipo,nome
        """
    ).fetchall()


def occurrence_count(con):
    return con.execute("SELECT count(*) FROM ocorrencias").fetchone()


def exams(con) -> list[dict]:
    rows = con.execute(
        """
        SELECT p.prova_id AS id, p.banca AS bank, p.concurso AS contest, p.titulo AS title, p.caderno AS booklet,
        count(o.ocorrencia_id) AS question_count FROM provas p LEFT JOIN ocorrencias o USING(prova_id) GROUP BY
        p.prova_id ORDER BY p.concurso, p.banca, p.titulo, p.caderno, p.prova_id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def exam_questions(con, exam_id: str) -> list[dict] | None:
    if con.execute("SELECT 1 FROM provas WHERE prova_id=?", (exam_id,)).fetchone() is None:
        return None
    rows = con.execute(
        """
        SELECT ocorrencia_id FROM ocorrencias WHERE prova_id=? ORDER BY CASE WHEN numero_original GLOB '[0-9]*' THEN
        0 ELSE 1 END, CAST(numero_original AS INTEGER), numero_original, ocorrencia_id
        """,
        (exam_id,),
    ).fetchall()
    return [content_question(con, row[0]) for row in rows]


def content_question(con, occurrence_id: str, include_answer: bool = False) -> dict | None:
    row = con.execute(
        """
        SELECT v.*, o.documento_id AS source_document_id, r.resposta_referencia, r.situacao_referencia, r.estado AS
        reference_state, r.possui_publicacao_definitiva AS has_definitive, CASE WHEN r.estado='concordante' AND
        r.situacao_referencia='valido' AND r.possui_publicacao_definitiva=1 AND v.status_extracao='extraido' THEN 1
        ELSE 0 END AS can_grade FROM vw_questoes v JOIN ocorrencias o USING(ocorrencia_id) LEFT JOIN
        vw_gabaritos_referencia r USING(ocorrencia_id) WHERE v.ocorrencia_id=?
        """,
        (occurrence_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["contexts"] = [
        r[0]
        for r in con.execute(
            """
        SELECT c.texto_original FROM questao_contexto qc JOIN contextos c USING(contexto_id) WHERE qc.questao_id=?
        ORDER BY qc.ordem
        """,
            (item["questao_id"],),
        )
    ]
    alternatives = [
        dict(r)
        for r in con.execute(
            "SELECT rotulo, texto_original FROM alternativas WHERE questao_id=? ORDER BY ordem, alternativa_id",
            (item["questao_id"],),
        )
    ]
    if item["formato"] == "certo_errado" and (not alternatives):
        alternatives = [{"rotulo": "C", "texto_original": "Certo"}, {"rotulo": "E", "texto_original": "Errado"}]
    item["alternatives"] = alternatives
    item["reference_status"] = {
        "state": item.pop("reference_state") or "sem referência consolidada",
        "situation": item.pop("situacao_referencia"),
        "has_definitive": bool(item.pop("has_definitive") or 0),
        "extraction": item.get("status_extracao"),
        "correctable": bool(item.pop("can_grade")),
    }
    if not include_answer:
        item.pop("resposta_referencia", None)
    else:
        item["source_answers"] = [
            dict(r)
            for r in con.execute(
                """
        SELECT g.resposta_publicada, g.situacao_item, g.natureza_gabarito, g.paginas_json, g.documento_id, d.titulo
        AS document_title FROM vw_gabaritos_associados g LEFT JOIN documentos d USING(documento_id) WHERE
        g.ocorrencia_id=? ORDER BY g.natureza_gabarito, g.documento_id
        """,
                (occurrence_id,),
            )
        ]
    return item


def question_page(
    con, search: str, bank: str, discipline: str, page: int, eligible_only: bool = True, limit: int = 24
) -> dict:
    where = ["1=1"]
    args: list = []
    eligible = "(r.estado='concordante' AND r.situacao_referencia='valido' AND r.possui_publicacao_definitiva=1 AND v.status_extracao='extraido')"
    if eligible_only:
        where.append(eligible)
    if bank:
        where.append("v.banca=?")
        args.append(bank)
    if discipline:
        where.append("v.disciplina_original=?")
        args.append(discipline)
    if search:
        needle = f"%{search[:160]}%"
        where.append(
            "(v.enunciado_original LIKE ? OR v.texto_para_busca LIKE ? OR v.banca LIKE ? OR v.titulo LIKE ? OR v.concurso LIKE ? OR v.numero_original LIKE ? OR v.disciplina_original LIKE ? OR v.bloco_original LIKE ?)"
        )
        args.extend([needle] * 8)
    cond = " AND ".join(where)
    offset = (page - 1) * limit
    total = con.execute(
        "SELECT count(*) FROM vw_questoes v LEFT JOIN vw_gabaritos_referencia r USING(ocorrencia_id) WHERE " + cond,
        args,
    ).fetchone()[0]
    rows = con.execute(
        """
        SELECT v.*, o.documento_id AS source_document_id, r.resposta_referencia, r.situacao_referencia, r.estado AS
        reference_state, r.possui_publicacao_definitiva AS has_definitive, CASE WHEN r.estado='concordante' AND
        r.situacao_referencia='valido' AND r.possui_publicacao_definitiva=1 AND v.status_extracao='extraido' THEN 1
        ELSE 0 END AS can_grade FROM vw_questoes v JOIN ocorrencias o USING(ocorrencia_id) LEFT JOIN
        vw_gabaritos_referencia r USING(ocorrencia_id) WHERE
        """
        + cond
        + " ORDER BY v.banca, v.concurso, v.titulo, v.numero_original, v.ocorrencia_id LIMIT ? OFFSET ?",
        [*args, limit, offset],
    ).fetchall()
    question_ids = list({r["questao_id"] for r in rows})
    alt_map: dict[str, list] = {q: [] for q in question_ids}
    context_map: dict[str, list] = {q: [] for q in question_ids}
    if question_ids:
        marks = ",".join(("?" for _ in question_ids))
        for r in con.execute(
            f"SELECT questao_id,rotulo,texto_original FROM alternativas WHERE questao_id IN ({marks}) ORDER BY ordem",
            question_ids,
        ):
            alt_map[r["questao_id"]].append({"rotulo": r["rotulo"], "texto_original": r["texto_original"]})
        for r in con.execute(
            f"SELECT qc.questao_id,c.texto_original FROM questao_contexto qc JOIN contextos c USING(contexto_id) WHERE qc.questao_id IN ({marks}) ORDER BY qc.ordem",
            question_ids,
        ):
            context_map[r["questao_id"]].append(r["texto_original"])
    items = []
    for row in rows:
        item = dict(row)
        item["alternatives"] = alt_map[item["questao_id"]]
        if item["formato"] == "certo_errado" and (not item["alternatives"]):
            item["alternatives"] = [
                {"rotulo": "C", "texto_original": "Certo"},
                {"rotulo": "E", "texto_original": "Errado"},
            ]
        item["contexts"] = context_map[item["questao_id"]]
        item["reference_status"] = {
            "state": item.pop("reference_state") or "sem referência consolidada",
            "situation": item.pop("situacao_referencia"),
            "has_definitive": bool(item.pop("has_definitive") or 0),
            "extraction": item.get("status_extracao"),
            "correctable": bool(item.pop("can_grade")),
        }
        item.pop("resposta_referencia", None)
        items.append(item)
    option_join = " JOIN ocorrencias o USING(ocorrencia_id) LEFT JOIN vw_gabaritos_referencia r USING(ocorrencia_id) "
    option_filter = f" AND {eligible}" if eligible_only else ""
    banks = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT v.banca FROM vw_questoes v"
            + option_join
            + "WHERE v.banca IS NOT NULL AND v.banca<>''"
            + option_filter
            + " ORDER BY v.banca"
        )
    ]
    disciplines = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT v.disciplina_original FROM vw_questoes v"
            + option_join
            + "WHERE v.disciplina_original IS NOT NULL AND v.disciplina_original<>''"
            + option_filter
            + " ORDER BY v.disciplina_original"
        )
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, (total + limit - 1) // limit),
        "banks": banks,
        "disciplines": disciplines,
    }


def associated_snapshot(con, occurrence_id: str) -> dict:
    row = con.execute(
        """
        SELECT resposta_referencia,situacao_referencia,estado,possui_publicacao_definitiva FROM
        vw_gabaritos_referencia WHERE ocorrencia_id=?
        """,
        (occurrence_id,),
    ).fetchone()
    answers = [
        dict(r)
        for r in con.execute(
            """
        SELECT g.resposta_publicada,g.situacao_item,g.natureza_gabarito, g.paginas_json,g.documento_id,d.titulo AS
        document_title FROM vw_gabaritos_associados g LEFT JOIN documentos d USING(documento_id) WHERE
        g.ocorrencia_id=? ORDER BY g.natureza_gabarito,g.documento_id
        """,
            (occurrence_id,),
        )
    ]
    if row is None:
        return {
            "answer": None,
            "situation": None,
            "state": "sem referência consolidada",
            "has_definitive": False,
            "associated": answers,
        }
    return {
        "answer": row["resposta_referencia"],
        "situation": row["situacao_referencia"],
        "state": row["estado"],
        "has_definitive": bool(row["possui_publicacao_definitiva"]),
        "associated": answers,
    }
