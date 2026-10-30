"""Extrai tópicos de conteúdo programático dos quatro editais Cebraspe da biblioteca."""

import json
import re
from collections import Counter

from ..common import clean
from ..config import config, load_documents

CONFIG = {
    "2024-MPO-APO": {
        "pages": (38, 55),
        "publication": "consolidado",
        "state": "na_versao_consolidada",
        "cargos": [
            ("Cargo 1: Analista de Planejamento e Orçamento — Especialidade: Geral", "Geral"),
            (
                "Cargo 2: Analista de Planejamento e Orçamento — Especialidade: Desenvolvimento Institucional",
                "Desenvolvimento Institucional",
            ),
            (
                "Cargo 3: Analista de Planejamento e Orçamento — Especialidade: Governança e Gestão de Projetos de TI",
                "Governança e Gestão de Projetos de TI",
            ),
            (
                "Cargo 4: Analista de Planejamento e Orçamento — Especialidade: Desenvolvimento de Sistemas Orçamentários",
                "Desenvolvimento de Sistemas Orçamentários",
            ),
            (
                "Cargo 5: Analista de Planejamento e Orçamento — Especialidade: Gestão de Infraestrutura de TI",
                "Gestão de Infraestrutura de TI",
            ),
            (
                "Cargo 6: Analista de Planejamento e Orçamento — Especialidade: Gestão de Dados Orçamentários",
                "Gestão de Dados Orçamentários",
            ),
            (
                "Cargo 7: Analista de Planejamento e Orçamento — Especialidade: Gestão de Contratos de TI",
                "Gestão de Contratos de TI",
            ),
            (
                "Cargo 8: Analista de Planejamento e Orçamento — Especialidade: Gestão da Segurança da Informação Orçamentária",
                "Gestão da Segurança da Informação Orçamentária",
            ),
        ],
        "markers": {
            "common": ["CONHECIMENTOS GERAIS COMUNS A TODAS AS ESPECIALIDADE"],
            "specific": ["CONHECIMENTOS ESPECÍFICOS"],
        },
    },
    "2022-SEPLAN-RR-APO": {
        "pages": (27, 30),
        "publication": "abertura",
        "state": "na_abertura",
        "cargos": [
            ("Cargo 1: Planejamento e Orçamento", "Planejamento e Orçamento"),
            ("Cargo 2: Tecnologia da Informação", "Tecnologia da Informação"),
        ],
        "markers": {"common": ["CONHECIMENTOS BÁSICOS PARA TODAS AS ÁREAS"], "specific": ["CONHECIMENTOS ESPECÍFICOS"]},
    },
    "2024-SEPLAG-CE-APO": {
        "pages": (34, 49),
        "publication": "consolidado",
        "state": "na_versao_consolidada",
        "cargos": [
            (
                "Cargo 1: Analista de Gestão Pública — Área de Atuação: Gestão e Desenvolvimento de Pessoas",
                "Gestão e Desenvolvimento de Pessoas",
            ),
            (
                "Cargo 2: Analista de Gestão Pública — Área de Atuação: Governança e Gestão Corporativa",
                "Governança e Gestão Corporativa",
            ),
            (
                "Cargo 3: Analista de Gestão Pública — Área de Especialidade: Ciência da Computação ou afins na área da Tecnologia da Informação e Comunicação",
                "Ciência da Computação/TIC",
            ),
            (
                "Cargo 4: Analista de Gestão Pública — Área de Especialidade: Contabilidade Pública",
                "Contabilidade Pública",
            ),
            ("Cargo 5: Analista de Planejamento e Orçamento", "Planejamento e Orçamento"),
        ],
        "markers": {
            "common": ["CONHECIMENTOS BÁSICOS COMUNS A TODOS OS CARGOS"],
            "common_specific": ["CONHECIMENTOS ESPECÍFICOS COMUNS A TODOS OS CARGOS"],
            "specific": ["CONHECIMENTOS ESPECÍFICOS"],
        },
    },
    "2025-SEFAZ-RJ-FINANCAS": {
        "pages": (47, 54),
        "publication": "consolidado",
        "state": "na_versao_consolidada",
        "cargos": [
            (
                "Cargo 1: Analista em Finanças Públicas — Especialidade: Administrativo-Financeira",
                "Administrativo-Financeira",
            ),
            ("Cargo 2: Analista em Finanças Públicas — Especialidade: Contábil-Financeira", "Contábil-Financeira"),
            ("Cargo 3: Analista em Finanças Públicas — Especialidade: Econômico-Financeira", "Econômico-Financeira"),
        ],
        "markers": {"common": ["CONHECIMENTOS GERAIS"], "specific": ["CONHECIMENTOS ESPECÍFICOS"]},
    },
}
METHOD = "Cache local pdfplumber/pdfminer com bboxes; seleção de páginas e escopos por cabeçalhos impressos; separação de cabeçalhos temáticos e itens numerados por expressão regular. Nenhum tópico ou subnível é gerado por inferência sem marcador na fonte."
TOKEN = re.compile("(?<![\\w/])(?P<num>\\d{1,2}(?:\\.\\d{1,3}){0,4})[.)]?(?=\\s+[^\\d\\s])")
HEADING = re.compile("^\\s*(?P<title>[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 ,/&()\\-–—.]{2,100}?):")
CARGO = re.compile("CARGO\\s+(\\d+)\\s*:", re.I)


def bbox_union(rows):
    rows = [r for r in rows if r.get("bbox")]
    if not rows:
        return None
    return [
        round(min((r["bbox"][0] for r in rows)), 1),
        round(min((r["bbox"][1] for r in rows)), 1),
        round(max((r["bbox"][2] for r in rows)), 1),
        round(max((r["bbox"][3] for r in rows)), 1),
    ]


def line_items(doc):
    cfg = CONFIG[doc["concurso"]]
    data = json.loads((config().run_dir / "paginas" / (doc["documento_id"] + ".json")).read_text(encoding="utf-8"))
    first, last = cfg["pages"]
    out = []
    active_note = False
    for p in data["paginas"]:
        if not first <= p["numero"] <= last:
            continue
        for line in p["linhas"]:
            t = line["texto"]
            if active_note and re.match("\\s*(?:https?://|www\\.)", t, re.I):
                out[-1]["retif_note"] += " " + t.strip()
                continue
            active_note = False
            m = re.search("\\(?Retificado\\s+por\\s+meio\\s+do\\s+Edital\\b", t, re.I)
            if m:
                note = t[m.start() :].strip()
                prefix = t[: m.start()].strip()
                if prefix:
                    out.append(
                        dict(
                            pagina=p["numero"],
                            texto=prefix,
                            bbox=line["bbox"],
                            fluxo=line.get("fluxo"),
                            retif_note=note,
                        )
                    )
                else:
                    out.append(
                        dict(pagina=p["numero"], texto="", bbox=line["bbox"], fluxo=line.get("fluxo"), retif_note=note)
                    )
                if not re.search("\\)\\s*$", note):
                    active_note = True
            else:
                out.append(dict(pagina=p["numero"], texto=t, bbox=line["bbox"], fluxo=line.get("fluxo")))
    return out


def detect_scope_markers(text, doc, cargo_index):
    cfg = CONFIG[doc["concurso"]]
    upper = text.upper()
    for cargo_no, (label, specialty) in enumerate(cfg["cargos"], 1):
        if re.search(f"\\bCARGO\\s+{cargo_no}\\s*:", upper):
            return ("cargo", cargo_no)
    for marker in cfg["markers"].get("common", []):
        if marker.upper() in upper:
            return ("block", "comum")
    for marker in cfg["markers"].get("common_specific", []):
        if marker.upper() in upper:
            return ("block", "especifico_comum")
    for marker in cfg["markers"].get("specific", []):
        if marker.upper() in upper:
            return ("block", "especifico")
    return None


def heading_splits(text):
    found = []
    first = HEADING.match(text)
    matches = []
    if first:
        matches.append((first.start("title"), first.end(), first.group("title")))
    if first:
        tail = text[first.end() :]
        roman = re.compile(
            "\\s+(?P<title>(?:I|II|III|IV|V|VI)\\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9 ,/&()\\-–—.]{2,90}?):"
        )
        for m in roman.finditer(tail):
            matches.append((first.end() + m.start("title"), first.end() + m.end(), m.group("title")))
    for start, end, rawtitle in matches:
        title = clean(rawtitle)
        if not title or title.startswith("CARGO "):
            continue
        if re.match("^[0-9]", title) or title.endswith(")") or re.search("\\d|/", title):
            continue
        if title in {"SIOP", "SDDC", "BPMN"}:
            continue
        if title in {"CONHECIMENTOS GERAIS", "CONHECIMENTOS ESPECÍFICOS", "CONHECIMENTOS BÁSICOS", "ANEXO I"}:
            continue
        if len(title) < 4:
            continue
        found.append((start, end, title))
    return found


def merge_upper_continuations(rows):
    out = []
    i = 0
    while i < len(rows):
        row = rows[i]
        t = row["texto"].strip()
        if (
            i + 1 < len(rows)
            and t == t.upper()
            and (":" not in t)
            and re.search("\\b(?:E|DE|DA|DO|DOS|DAS)$", t)
            and (rows[i + 1]["texto"].strip() == rows[i + 1]["texto"].strip().upper())
        ):
            nxt = rows[i + 1]
            bb = [
                min(row["bbox"][0], nxt["bbox"][0]),
                min(row["bbox"][1], nxt["bbox"][1]),
                max(row["bbox"][2], nxt["bbox"][2]),
                max(row["bbox"][3], nxt["bbox"][3]),
            ]
            out.append({**row, "texto": t + " " + nxt["texto"].strip(), "bbox": bb})
            i += 2
        else:
            out.append(row)
            i += 1
    return out


def is_roman_header(title):
    return bool(re.match("^(?:I|II|III|IV|V|VI)\\s+", title))


def extract_topics(doc, lines):
    cfg = CONFIG[doc["concurso"]]
    cargo_map = {i + 1: (name, spec) for i, (name, spec) in enumerate(cfg["cargos"])}
    all_cargo_names = [x[0] for x in cfg["cargos"]]
    curr_heading = None
    heading_stack = []
    serial = 0
    topics = []
    audit = Counter()
    anomalies = []

    def emit_heading(title, row, block_scope, cargo_scope):
        nonlocal serial, curr_heading, heading_stack
        serial += 1
        hid = f"{doc['documento_id']}:t{serial:05d}"
        if is_roman_header(title) and heading_stack:
            parent = heading_stack[-1]["id"]
            path = heading_stack[-1]["path"] + [title]
        else:
            parent = None
            path = [title]
            heading_stack = []
        topic = {
            "documento_id": doc["documento_id"],
            "topico_id_local": hid,
            "topico_pai_id_local": parent,
            "numero_original": None,
            "ordem_original": serial,
            "texto_original": title,
            "disciplina_original": title,
            "caminho_original": path,
            "escopo_cargos": all_cargo_names if cargo_scope is None else [cargo_map[cargo_scope][0]],
            "escopo_especialidades": [x[1] for x in cfg["cargos"]]
            if cargo_scope is None
            else [cargo_map[cargo_scope][1]],
            "bloco": "comum"
            if block_scope == "comum"
            else "especifico"
            if block_scope in ("especifico", "especifico_comum")
            else "nao_identificado",
            "tipo_publicacao": cfg["publication"],
            "estado_na_versao": cfg["state"],
            "paginas_pdf": [row["pagina"]],
            "regioes_fonte": [{"pagina": row["pagina"], "bbox": row["bbox"]}] if row.get("bbox") else [],
            "conceitos_normalizados": [],
            "status_extracao": "extraido",
            "alertas": [],
            "metodo_extracao": METHOD,
            "agente": "Luna — extração local rastreável",
        }
        topics.append(topic)
        curr_heading = {"id": hid, "path": path, "disciplina": title, "parent": parent}
        heading_stack.append(curr_heading)
        audit["cabecalhos_disciplina"] += 1
        return curr_heading

    def parse_segment(title, rows, block_scope, cargo_scope, parent_heading=None):
        nonlocal serial
        if not rows:
            return
        full = "\n".join((r["texto"] for r in rows))
        ms = []
        for m in TOKEN.finditer(full):
            num = m.group("num")
            prev = full[max(0, m.start() - 28) : m.start()]
            after = full[m.end() : m.end() + 30]
            if re.search("(?:Lei|Decreto|Resolu[cç][aã]o|Portaria|art(?:igo)?|n[º°o.]?)\\s*$", prev, re.I):
                continue
            if re.match("\\s*/\\s*\\d{2,4}", after):
                continue
            val_parts = num.split(".")
            if len(val_parts) > 1 and any((int(v) > 150 for v in val_parts[1:])):
                continue
            if num in {"14.2.2", "14.2.3", "16.2.2", "16.2.3"}:
                continue
            ms.append(m)
        if not ms:
            anomalies.append(
                {
                    "concurso": doc["concurso"],
                    "disciplina": title,
                    "alerta": "Cabeçalho sem itens numéricos reconhecidos.",
                    "paginas": sorted({r["pagina"] for r in rows}),
                }
            )
            return
        spans = []
        off = 0
        for r in rows:
            st = off
            off += len(r["texto"])
            spans.append((st, off, r))
            off += 1
        scope_parent = parent_heading["id"] if parent_heading else None
        base_path = parent_heading["path"][:] if parent_heading else [title]
        ids_by_num = {}
        for j, m in enumerate(ms):
            start = m.start()
            end = ms[j + 1].start() if j + 1 < len(ms) else len(full)
            num = m.group("num")
            phrase = clean(full[m.end() : end]).strip(" .;:—–")
            if not phrase:
                continue
            numbered_text = clean(num + " " + phrase)
            matching = [r for a, b, r in spans if b > start and a < end]
            pages = sorted({r["pagina"] for r in matching})
            regs = []
            for pg in pages:
                bb = bbox_union([r for r in matching if r["pagina"] == pg])
                if bb:
                    regs.append({"pagina": pg, "bbox": bb})
            parts = num.split(".")
            pnum = ".".join(parts[:-1]) if len(parts) > 1 else None
            parent_obj = ids_by_num.get(pnum) if pnum else None
            pid = parent_obj["topico_id_local"] if parent_obj else scope_parent
            parent_path = []
            if pnum:
                ancestors = []
                for ix in range(1, len(parts)):
                    key = ".".join(parts[:ix])
                    parent_obj = ids_by_num.get(key)
                    if parent_obj:
                        ancestors.append(parent_obj["texto_original"])
                parent_path = ancestors
            path = base_path + parent_path + [numbered_text]
            serial += 1
            tid = f"{doc['documento_id']}:t{serial:05d}"
            topic = {
                "documento_id": doc["documento_id"],
                "topico_id_local": tid,
                "topico_pai_id_local": pid,
                "numero_original": num,
                "ordem_original": serial,
                "texto_original": numbered_text,
                "disciplina_original": title,
                "caminho_original": path,
                "escopo_cargos": all_cargo_names if cargo_scope is None else [cargo_map[cargo_scope][0]],
                "escopo_especialidades": [x[1] for x in cfg["cargos"]]
                if cargo_scope is None
                else [cargo_map[cargo_scope][1]],
                "bloco": "comum"
                if block_scope == "comum"
                else "especifico"
                if block_scope in ("especifico", "especifico_comum")
                else "nao_identificado",
                "tipo_publicacao": cfg["publication"],
                "estado_na_versao": cfg["state"],
                "paginas_pdf": pages,
                "regioes_fonte": regs,
                "conceitos_normalizados": [],
                "status_extracao": "extraido",
                "alertas": [],
                "metodo_extracao": METHOD,
                "agente": "Luna — extração local rastreável",
            }
            topics.append(topic)
            ids_by_num[num] = topic
            audit["topicos_numerados"] += 1
            if len(phrase) < 2:
                topic["status_extracao"] = "precisa_revisao"
                topic["alertas"].append("Item sem texto suficiente após o número.")

    def flush_scope(rows, block_scope, cargo_scope):
        nonlocal heading_stack, curr_heading
        rows = merge_upper_continuations(rows)

        def process_heading_text(title, body_rows):
            heading = emit_heading(title, body_rows[0], block_scope, cargo_scope)
            parse_segment(title, body_rows, block_scope, cargo_scope, heading)

        if not rows:
            return
        accum = []
        curr = None
        for row in rows:
            text = row["texto"]
            matches = heading_splits(text)
            if not matches:
                if curr:
                    accum.append(row)
                continue
            cursor = 0
            for si, (start, end, hd) in enumerate(matches):
                pre = text[cursor:start].strip()
                if pre and curr and (not (pre.upper() == pre and pre.endswith(":"))):
                    accum.append({**row, "texto": pre})
                if curr and accum:
                    process_heading_text(curr, accum)
                    accum = []
                curr = hd
                cursor = end
                remainder = text[end:]
                if remainder.strip():
                    accum.append({**row, "texto": remainder.strip()})
            tail = text[cursor:]
            if not matches and tail and curr:
                accum.append(row)
        if curr and accum:
            process_heading_text(curr, accum)

    scopes = []
    current = []
    b = None
    c = None
    for row in lines:
        t = row["texto"].strip()
        mark = detect_scope_markers(t, doc, c)
        if mark:
            if current:
                scopes.append((b, c, current))
                current = []
            if mark[0] == "block":
                b = mark[1]
                c = None
            else:
                c = mark[1]
                b = "especifico"
            continue
        if b is not None and (not re.fullmatch("\\d{1,3}", t)):
            current.append(row)
    if current:
        scopes.append((b, c, current))
    for b, c, rows in scopes:
        flush_scope(rows, b, c)
    return (topics, audit, anomalies)


def merge_repeated_scope_topics(topics):
    merged = []
    by_key = {}
    redirect = {}
    occurrences = 0
    for topic in topics:
        key = (
            topic["documento_id"],
            topic["bloco"],
            topic["disciplina_original"],
            topic["numero_original"],
            topic["texto_original"],
            tuple(topic["caminho_original"]),
        )
        base_candidate = by_key.get(key)
        if base_candidate and set(base_candidate["escopo_cargos"]) & set(topic["escopo_cargos"]):
            key = key + (topic["topico_id_local"],)
        if key not in by_key:
            by_key[key] = topic
            merged.append(topic)
            redirect[topic["topico_id_local"]] = topic["topico_id_local"]
            continue
        base = by_key[key]
        occurrences += 1
        redirect[topic["topico_id_local"]] = base["topico_id_local"]
        base["escopo_cargos"] = list(dict.fromkeys(base["escopo_cargos"] + topic["escopo_cargos"]))
        base["escopo_especialidades"] = list(
            dict.fromkeys(base["escopo_especialidades"] + topic["escopo_especialidades"])
        )
        base["paginas_pdf"] = sorted(set(base["paginas_pdf"] + topic["paginas_pdf"]))
        regs = base["regioes_fonte"] + topic["regioes_fonte"]
        base["regioes_fonte"] = [dict(t) for t in {(r["pagina"], tuple(r["bbox"])): r for r in regs}.values()]
        base["ordem_original"] = min(base["ordem_original"], topic["ordem_original"])
    for t in merged:
        if t["topico_pai_id_local"]:
            t["topico_pai_id_local"] = redirect.get(t["topico_pai_id_local"], t["topico_pai_id_local"])
    return (merged, occurrences)


def main():
    docs = load_documents()
    targets = [d for d in docs if d["tipo"] == "editais" and d["banca"] == "Cebraspe" and (d["concurso"] in CONFIG)]
    all_topics = []
    reports = []
    for d in targets:
        lines = line_items(d)
        retif_notes = [{"pagina": z["pagina"], "texto_literal": z["retif_note"]} for z in lines if z.get("retif_note")]
        raw_topics, audit, anomalies = extract_topics(d, lines)
        topics, merged_occurrences = merge_repeated_scope_topics(raw_topics)
        all_topics.extend(topics)
        numbers = [t["numero_original"] for t in topics if t["numero_original"]]
        reports.append(
            {
                "documento_id": d["documento_id"],
                "concurso": d["concurso"],
                "arquivo": d["arquivo_relativo"],
                "paginas_pdf": d["paginas"],
                "paginas_conteudo_programatico": sorted({p for t in topics for p in t["paginas_pdf"]}),
                "tipo_publicacao": CONFIG[d["concurso"]]["publication"],
                "cargos": CONFIG[d["concurso"]]["cargos"],
                "blocos": dict(audit),
                "topicos_total": len(topics),
                "ocorrencias_repetidas_mescladas": merged_occurrences,
                "topicos_numerados": len(numbers),
                "numeros_amostra_inicio": numbers[:12],
                "numeros_amostra_fim": numbers[-12:],
                "lacunas": [],
                "duplicacoes": [],
                "duvidas": anomalies,
                "retificacoes_inline_na_fonte": retif_notes,
                "amostras_visuais_revisadas": [],
                "notas": "Cada item mantém texto e hierarquia impressos. Blocos comuns vinculados a todos os cargos; itens idênticos repetidos sob cargos distintos foram mesclados com escopos e páginas acumulados. Anotações inline de retificação foram preservadas no relatório, separadas do conteúdo programático. Estado consolidado conforme identificação documental do manifesto.",
            }
        )
    out = config().run_dir / "lotes" / "cebraspe.topicos.jsonl"
    out.write_text("".join((json.dumps(t, ensure_ascii=False) + "\n" for t in all_topics)), encoding="utf-8")
    report = {"grupo": "cebraspe_editais", "metodo": METHOD, "total_topicos": len(all_topics), "documentos": reports}
    (config().run_dir / "lotes" / "cebraspe.editais.relatorio.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "total": len(all_topics),
                "docs": [
                    (r["concurso"], r["topicos_total"], r["topicos_numerados"], r["paginas_conteudo_programatico"])
                    for r in reports
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
