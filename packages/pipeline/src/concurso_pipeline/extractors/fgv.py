import json
import re
from collections import Counter

import pdfplumber

from ..common import clean, expected_count
from ..config import config, load_documents, source_file

AGENT = "fleet-luna-fgv"
NUM = re.compile("^\\s*(\\d{1,3})\\s*\\.?\\s*$")
ALT = re.compile("^\\s*\\(([A-E])\\)\\s*(.*)$")


def lines_in_column(page, x0, x1):
    crop = page.crop((x0, 0, x1, page.height))
    txt = crop.extract_text(x_tolerance=2, y_tolerance=3, use_text_flow=False) or ""
    return [clean(x) for x in txt.splitlines() if clean(x)]


def page_stream(pdf):
    stream = []
    for pi, page in enumerate(pdf.pages, 1):
        mid = page.width / 2
        whole = page.extract_text() or ""
        if re.search("INFORMAÇÕES\\s+GERAIS|SUA\\s+PROVA|caderno\\s+de\\s+provas", whole, re.I):
            continue
        if re.search("(?m)^\\s*Redação\\s*$", whole):
            continue
        bare_nums = len(re.findall("(?m)^\\s*\\d{1,3}\\s*$", whole))
        dashed = len(re.findall("(?m)^\\s*-{12,}\\s*$", whole))
        if bare_nums >= 10 and dashed >= 10:
            continue
        for col, (x0, x1) in enumerate(((0, mid), (mid, page.width)), 1):
            lines = lines_in_column(page, x0, x1)
            if lines:
                stream.append(
                    {
                        "page": pi,
                        "col": col,
                        "bbox": [round(x0, 1), 0, round(x1, 1), round(page.height, 1)],
                        "lines": lines,
                    }
                )
    return stream


def parse_stream(stream):
    qs, current, pending = ([], None, [])
    active_discipline = None
    last_number = None
    for block in stream:
        page, bbox = (block["page"], block["bbox"])
        for line in block["lines"]:
            m = NUM.match(line)
            if m and int(m.group(1)) > 0 and (last_number is None or int(m.group(1)) == last_number + 1):
                n = m.group(1)
                last_number = int(n)
                if current is not None:
                    qs.append(current)
                current = {"n": n, "lines": [], "pages": [], "regions": [], "discipline": active_discipline}
                if pending:
                    current["leading"] = pending[-8:]
                    pending = []
                current["pages"].append(page)
                current["regions"].append({"pagina": page, "bbox": bbox})
            elif current is not None:
                current["lines"].append(line)
                if page not in current["pages"]:
                    current["pages"].append(page)
                    current["regions"].append({"pagina": page, "bbox": bbox})
            else:
                pending.append(line)
                if len(line) < 90 and (not re.search("\\b(quest|prova|caderno|tipo|página)\\b", line, re.I)):
                    if line.isupper() or (len(line.split()) <= 5 and line[:1].isupper()):
                        active_discipline = line
    if current is not None:
        qs.append(current)
    return qs


def split_item(q, doc):
    raw = "\n".join(q["lines"]).strip()
    lines = [
        x
        for x in raw.splitlines()
        if not re.search("(?:Página\\s+\\d+|Tipo\\s+\\d+\\s*[–-]|FGV Conhecimento)", x, re.I)
    ]
    raw = "\n".join(lines).strip()
    alternatives, stem = ([], [])
    active = None
    for line in lines:
        m = ALT.match(line)
        if m:
            if active:
                alternatives.append(active)
            active = {"rotulo": m.group(1), "texto": m.group(2).strip()}
        elif active:
            active["texto"] = (active["texto"] + " " + line).strip()
        else:
            stem.append(line)
    if active:
        alternatives.append(active)
    alerts = []
    status = "extraido"
    if not raw or len(raw) < 20:
        alerts.append("Texto curto ou vazio após segmentação.")
        status = "incompleto"
    visual_cue = re.search(
        "\\b(?:gráfico|tabela|quadro)\\s+(?:a\\s+seguir|abaixo|seguinte)\\b|\\bfigura\\s+(?:a\\s+seguir|abaixo|seguinte)|\\bimagem\\s+(?:a\\s+seguir|abaixo|seguinte)|\\b(?:na|pela|conforme\\s+a)\\s+figura\\b",
        raw,
        re.I,
    )
    if visual_cue:
        alerts.append(
            "Enunciado remete a elemento visual; transcrição textual pode não capturar gráfico/tabela. Conferir o PDF na região indicada."
        )
        status = "precisa_revisao" if status == "extraido" else status
    return {
        "documento_id": doc["documento_id"],
        "prova_id": doc["documento_id"],
        "numero_original": q["n"],
        "bloco_original": None,
        "formato": "multipla_escolha" if alternatives else "discursiva",
        "disciplina_original": q.get("discipline"),
        "enunciado_original": "\n".join(stem).strip(),
        "alternativas": alternatives,
        "contextos": [],
        "paginas_pdf": sorted(set(q["pages"])),
        "regioes_fonte": q["regions"],
        "texto_original_completo": raw,
        "status_extracao": status,
        "alertas": alerts,
        "classificacoes": [],
        "habilidades": [],
        "referencias_normativas_literais": [],
        "metodo_extracao": "pdfplumber: extração textual com segmentação geométrica em duas colunas; alternativas por rótulos A-E; contextos compartilhados não inferidos automaticamente",
        "agente": AGENT,
    }


def extract_discursiva(doc):
    with pdfplumber.open(source_file(doc)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            full = page.extract_text() or ""
            m = re.search("(?m)^\\s*Redação\\s*$", full)
            if not m:
                continue
            source = full[m.end() :].strip()
            source = re.sub("(?m)^.*(?:PÁGINA|Página)\\s+\\d+.*$", "", source).strip()
            split = re.search("Tendo em vista|Elabore um texto", source, re.I)
            context_text = source[: split.start()].strip() if split else None
            command = source[split.start() :].strip() if split else source
            return {
                "documento_id": doc["documento_id"],
                "prova_id": doc["documento_id"],
                "numero_original": "redacao",
                "bloco_original": "Redação",
                "formato": "discursiva",
                "disciplina_original": "Redação",
                "enunciado_original": command or "",
                "alternativas": [],
                "contextos": [
                    {
                        "texto": context_text,
                        "paginas_pdf": [page_num],
                        "regioes_fonte": [
                            {"pagina": page_num, "bbox": [0, 0, round(page.width, 1), round(page.height, 1)]}
                        ],
                    }
                ]
                if context_text
                else [],
                "paginas_pdf": [page_num],
                "regioes_fonte": [{"pagina": page_num, "bbox": [0, 0, round(page.width, 1), round(page.height, 1)]}],
                "texto_original_completo": source,
                "status_extracao": "extraido",
                "alertas": [],
                "classificacoes": [],
                "habilidades": [],
                "referencias_normativas_literais": [],
                "metodo_extracao": "pdfplumber: seção discursiva identificada pelo cabeçalho literal Redação; texto-base separado do comando",
                "agente": AGENT,
            }
    return None


def expected_discursivas(doc):
    try:
        with pdfplumber.open(source_file(doc)) as pdf:
            p = pdf.pages[0]
            texts = [p.extract_text() or ""]
            texts.extend(
                (
                    p.crop((x0, 0, x1, p.height)).extract_text() or ""
                    for x0, x1 in ((0, p.width / 2), (p.width / 2, p.width))
                )
            )
        for text in texts:
            flat = re.sub("\\s+", " ", text)
            m = re.search("\\b(\\d+)\\s*(?:\\([^)]*\\))?\\s+redação\\b", flat, re.I)
            if m:
                return int(m.group(1))
        return None
    except Exception:
        return None


def link_repeated_contexts(rows):
    """Separate a long, exactly repeated line block used by multiple questions."""
    groups = {}
    line_sets = [r["enunciado_original"].splitlines() if r["enunciado_original"] else [] for r in rows]
    for i in range(len(rows)):
        a = line_sets[i]
        for j in range(i + 1, len(rows)):
            b = line_sets[j]
            best = None
            for ai in range(len(a)):
                for bi in range(len(b)):
                    k = 0
                    while ai + k < len(a) and bi + k < len(b) and (a[ai + k].strip() == b[bi + k].strip()):
                        k += 1
                    candidate = a[ai : ai + k]
                    value = "\n".join(candidate).strip()
                    if k >= 3 and len(value) >= 60 and (best is None or len(value) > len(best)):
                        best = value
            if best:
                groups.setdefault(best, set()).update((i, j))
    contexts = {}
    for value, indexes in groups.items():
        for i in indexes:
            r = rows[i]
            contexts.setdefault(i, []).append(
                {"texto": value, "paginas_pdf": sorted(set(r["paginas_pdf"])), "regioes_fonte": r["regioes_fonte"]}
            )
            current = r["enunciado_original"] or ""
            r["enunciado_original"] = current.replace(value, "", 1).strip() or None
    for i, items in contexts.items():
        rows[i]["contextos"] = items


def visual_audit(doc_id):
    return []


def main():
    docs = load_documents()
    docs = [d for d in docs if d.get("banca") == "FGV" and d.get("tipo") == "provas"]
    all_records, details = ([], [])
    for doc in docs:
        with pdfplumber.open(source_file(doc)) as pdf:
            qs = parse_stream(page_stream(pdf))
        rows = [split_item(q, doc) for q in qs]
        filtered = []
        for r in rows:
            if not re.search("[A-Za-zÀ-ÿ0-9]", r["texto_original_completo"]):
                continue
            filtered.append(r)
        rows = filtered
        link_repeated_contexts(rows)
        alt_counts = Counter((len(r["alternativas"]) for r in rows if len(r["alternativas"]) in (4, 5)))
        expected_alternatives = alt_counts.most_common(1)[0][0] if alt_counts else None
        for r in rows:
            count = len(r["alternativas"])
            if count and expected_alternatives is not None and (count != expected_alternatives):
                r["alertas"].append(
                    f"Padrão do caderno: {expected_alternatives} alternativas; encontradas {count}. Conferir segmentação."
                )
                r["status_extracao"] = "precisa_revisao"
        expected_disc = expected_discursivas(doc)
        discursive = extract_discursiva(doc) if expected_disc else None
        if discursive:
            rows.append(discursive)
        nums = [int(r["numero_original"]) for r in rows if r["numero_original"].isdigit()]
        dup = sorted((n for n, c in Counter(nums).items() if c > 1))
        gaps = []
        if nums:
            gaps = sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
        with pdfplumber.open(source_file(doc)) as pdf:
            expected = expected_count(" ".join(p.extract_text() or "" for p in pdf.pages[:1]))
        declared_range_note = None
        objective_count = sum((r["formato"] == "multipla_escolha" for r in rows))
        discursive_count = sum((r["formato"] == "discursiva" for r in rows))
        if expected is not None and objective_count != expected:
            if nums and nums[0] > 1:
                declared_range_note = f"Capa declara {expected} itens no conjunto da prova, mas este arquivo contém a sequência numerada {nums[0]}–{nums[-1]} ({objective_count} questões objetivas); a parte anterior pode estar em outro caderno/documento."
            else:
                declared_range_note = (
                    f"Capa declara {expected} questões objetivas; extraídas {objective_count} neste arquivo."
                )
        if expected_disc is not None and discursive_count != expected_disc:
            declared_range_note = (
                declared_range_note + " " if declared_range_note else ""
            ) + f"Capa declara {expected_disc} discursiva(s); extraídas {discursive_count}."
        all_records.extend(rows)
        details.append(
            {
                "documento_id": doc["documento_id"],
                "concurso": doc["concurso"],
                "arquivo": doc["arquivo_relativo"],
                "paginas": doc["paginas"],
                "quantidade_esperada_explicita": expected,
                "quantidade_esperada_discursivas_explicita": expected_disc,
                "questoes_extraidas": len(rows),
                "numeros_encontrados": [r["numero_original"] for r in rows],
                "lacunas": gaps,
                "duplicacoes": dup,
                "multipla_escolha": sum((r["formato"] == "multipla_escolha" for r in rows)),
                "alternativas_por_documento": expected_alternatives,
                "discursivas": sum((r["formato"] == "discursiva" for r in rows)),
                "precisa_revisao": sum((r["status_extracao"] == "precisa_revisao" for r in rows)),
                "incompletas": sum((r["status_extracao"] == "incompleto" for r in rows)),
                "alertas": [declared_range_note] if declared_range_note else [],
                "amostras_visuais_revisadas": [],
            }
        )
    (config().run_dir / "lotes" / "fgv.questoes.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (config().run_dir / "lotes" / "fgv.questoes.jsonl").write_text(
        "\n".join((json.dumps(r, ensure_ascii=False) for r in all_records)) + "\n", encoding="utf-8"
    )
    report = {
        "grupo": "FGV",
        "execucao": config().run_id,
        "metodo": "pdfplumber com separação de colunas por geometria da página; questões sequenciadas monotonicamente; contextos compartilhados identificados apenas por blocos literais repetidos; sem categorização temática automática",
        "documentos": details,
        "total_questoes": len(all_records),
        "observacao": "Questões dependentes de figuras/tabelas mantêm transcrição e regiões para consulta ao PDF; classificar disciplinas/assuntos/habilidades exige revisão semântica e não foi preenchido automaticamente.",
    }
    (config().run_dir / "lotes" / "fgv.relatorio.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "documentos": len(docs),
                "questoes": len(all_records),
                "out": str(config().run_dir / "lotes" / "fgv.questoes.jsonl"),
                "report": str(config().run_dir / "lotes" / "fgv.relatorio.json"),
            },
            ensure_ascii=False,
        )
    )
