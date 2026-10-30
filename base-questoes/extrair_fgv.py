import json
import re
import sys
from collections import Counter
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parent
RUN = ROOT / "execucoes" / "2026-10-29"
MANIFEST = RUN / "documentos.json"
OUT = RUN / "lotes" / "fgv.questoes.jsonl"
REPORT = RUN / "lotes" / "fgv.relatorio.json"
AGENT = "fleet-luna-fgv"

NUM = re.compile(r"^\s*(\d{1,3})\s*\.?\s*$")
ALT = re.compile(r"^\s*\(([A-E])\)\s*(.*)$")


def clean(s):
    return re.sub(r"[ \t]+", " ", s).strip()


def lines_in_column(page, x0, x1):
    crop = page.crop((x0, 0, x1, page.height))
    txt = crop.extract_text(x_tolerance=2, y_tolerance=3, use_text_flow=False) or ""
    return [clean(x) for x in txt.splitlines() if clean(x)]


def page_stream(pdf):
    stream = []
    # FGV objective booklets are conventionally two columns. Split by page geometry
    # so numbering never jumps between columns due to global text-flow ordering.
    for pi, page in enumerate(pdf.pages, 1):
        mid = page.width / 2
        whole = page.extract_text() or ""
        if re.search(r"INFORMAÇÕES\s+GERAIS|SUA\s+PROVA|caderno\s+de\s+provas", whole, re.I):
            continue
        if re.search(r"(?m)^\s*Redação\s*$", whole):
            continue
        bare_nums = len(re.findall(r"(?m)^\s*\d{1,3}\s*$", whole))
        dashed = len(re.findall(r"(?m)^\s*-{12,}\s*$", whole))
        if bare_nums >= 10 and dashed >= 10:
            continue
        for col, (x0, x1) in enumerate(((0, mid), (mid, page.width)), 1):
            lines = lines_in_column(page, x0, x1)
            if lines:
                stream.append({"page": pi, "col": col, "bbox": [round(x0, 1), 0, round(x1, 1), round(page.height, 1)], "lines": lines})
    return stream


def parse_stream(stream):
    qs, current, pending = [], None, []
    active_discipline = None
    last_number = None
    for block in stream:
        page, bbox = block["page"], block["bbox"]
        for line in block["lines"]:
            m = NUM.match(line)
            if m and int(m.group(1)) > 0 and (last_number is None or int(m.group(1)) == last_number + 1):
                n = m.group(1)
                last_number = int(n)
                if current is not None:
                    qs.append(current)
                current = {"n": n, "lines": [], "pages": [], "regions": [], "discipline": active_discipline}
                if pending:
                    # Preserve preceding standalone instructions as context for the next item.
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
                # Discipline heading heuristic is limited to short, standalone headings;
                # it is recorded as printed text, not semantic subject classification.
                if len(line) < 90 and not re.search(r"\b(quest|prova|caderno|tipo|página)\b", line, re.I):
                    if line.isupper() or (len(line.split()) <= 5 and line[:1].isupper()):
                        active_discipline = line
    if current is not None:
        qs.append(current)
    return qs


def split_item(q, doc):
    raw = "\n".join(q["lines"]).strip()
    # Remove recurrent page furniture, retaining the question content itself.
    lines = [x for x in raw.splitlines() if not re.search(r"(?:Página\s+\d+|Tipo\s+\d+\s*[–-]|FGV Conhecimento)", x, re.I)]
    raw = "\n".join(lines).strip()
    alternatives, stem = [], []
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
        r"\b(?:gráfico|tabela|quadro)\s+(?:a\s+seguir|abaixo|seguinte)\b|\bfigura\s+(?:a\s+seguir|abaixo|seguinte)|\bimagem\s+(?:a\s+seguir|abaixo|seguinte)|\b(?:na|pela|conforme\s+a)\s+figura\b",
        raw, re.I
    )
    if visual_cue:
        alerts.append("Enunciado remete a elemento visual; transcrição textual pode não capturar gráfico/tabela. Conferir o PDF na região indicada.")
        status = "precisa_revisao" if status == "extraido" else status
    return {
        "documento_id": doc["documento_id"], "prova_id": doc["documento_id"],
        "numero_original": q["n"], "bloco_original": None,
        "formato": "multipla_escolha" if alternatives else "discursiva",
        "disciplina_original": q.get("discipline"),
        "enunciado_original": "\n".join(stem).strip() or None,
        "alternativas": alternatives, "contextos": [],
        "paginas_pdf": sorted(set(q["pages"])), "regioes_fonte": q["regions"],
        "texto_original_completo": raw,
        "status_extracao": status, "alertas": alerts,
        "classificacoes": [], "habilidades": [], "referencias_normativas_literais": [],
        "metodo_extracao": "pdfplumber: extração textual com segmentação geométrica em duas colunas; alternativas por rótulos A-E; contextos compartilhados não inferidos automaticamente",
        "agente": AGENT
    }


def expected_count(doc):
    p = Path(doc["arquivo"])
    try:
        with pdfplumber.open(p) as pdf:
            page = pdf.pages[0]
            texts = [page.extract_text() or ""]
            texts.extend(page.crop((x0, 0, x1, page.height)).extract_text() or "" for x0, x1 in ((0, page.width / 2), (page.width / 2, page.width)))
        words = {"sessenta e cinco": 65, "sessenta": 60, "oitenta": 80, "quarenta": 40, "cinquenta": 50, "trinta": 30, "setenta": 70, "noventa": 90}
        for text in texts:
            cover = re.sub(r"\s+", " ", text)
            m = re.search(r"\b(\d+|sessenta e cinco|sessenta|oitenta|quarenta|cinquenta|trinta|setenta|noventa)(?:\s*\([^)]*\))?\s+quest(?:ões|oes)(?:\s+objetivas)?", cover, re.I)
            if m:
                phrase = clean(m.group(1)).lower()
                return int(phrase) if phrase.isdigit() else words.get(phrase)
        return None
    except Exception:
        return None


def extract_discursiva(doc):
    with pdfplumber.open(doc["arquivo"]) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            full = page.extract_text() or ""
            m = re.search(r"(?m)^\s*Redação\s*$", full)
            if not m:
                continue
            source = full[m.end():].strip()
            source = re.sub(r"(?m)^.*(?:PÁGINA|Página)\s+\d+.*$", "", source).strip()
            split = re.search(r"Tendo em vista|Elabore um texto", source, re.I)
            context_text = source[:split.start()].strip() if split else None
            command = source[split.start():].strip() if split else source
            return {
                "documento_id": doc["documento_id"], "prova_id": doc["documento_id"],
                "numero_original": "redacao", "bloco_original": "Redação", "formato": "discursiva",
                "disciplina_original": "Redação", "enunciado_original": command or None,
                "alternativas": [],
                "contextos": ([{"texto": context_text, "paginas_pdf": [page_num], "regioes_fonte": [{"pagina": page_num, "bbox": [0, 0, round(page.width, 1), round(page.height, 1)]}]}] if context_text else []),
                "paginas_pdf": [page_num],
                "regioes_fonte": [{"pagina": page_num, "bbox": [0, 0, round(page.width, 1), round(page.height, 1)]}],
                "texto_original_completo": source, "status_extracao": "extraido", "alertas": [],
                "classificacoes": [], "habilidades": [], "referencias_normativas_literais": [],
                "metodo_extracao": "pdfplumber: seção discursiva identificada pelo cabeçalho literal Redação; texto-base separado do comando",
                "agente": AGENT
            }
    return None


def expected_discursivas(doc):
    try:
        with pdfplumber.open(doc["arquivo"]) as pdf:
            p = pdf.pages[0]
            texts = [p.extract_text() or ""]
            texts.extend(p.crop((x0, 0, x1, p.height)).extract_text() or "" for x0, x1 in ((0, p.width / 2), (p.width / 2, p.width)))
        for text in texts:
            flat = re.sub(r"\s+", " ", text)
            m = re.search(r"\b(\d+)\s*(?:\([^)]*\))?\s+redação\b", flat, re.I)
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
                    while ai + k < len(a) and bi + k < len(b) and a[ai + k].strip() == b[bi + k].strip():
                        k += 1
                    candidate = a[ai:ai + k]
                    value = "\n".join(candidate).strip()
                    if k >= 3 and len(value) >= 60 and (best is None or len(value) > len(best)):
                        best = value
            if best:
                groups.setdefault(best, set()).update((i, j))
    contexts = {}
    for value, indexes in groups.items():
        for i in indexes:
            r = rows[i]
            contexts.setdefault(i, []).append({
                "texto": value,
                "paginas_pdf": sorted(set(r["paginas_pdf"])),
                "regioes_fonte": r["regioes_fonte"]
            })
            current = r["enunciado_original"] or ""
            r["enunciado_original"] = current.replace(value, "", 1).strip() or None
    for i, items in contexts.items():
        rows[i]["contextos"] = items


def visual_audit(doc_id):
    samples = {
        "doc_35b17fc80bf93dd95250": (3, "múltipla escolha, duas colunas", "fgv_p1_p3-03.png"),
        "doc_4bed8817399f2b277afe": (8, "questões com subscritos matemáticos e alternativas", "fgv_epe_fin_p8-08.png"),
        "doc_2a2d58c85ea13233cbe6": (3, "quatro alternativas e contexto literal compartilhado entre Q1 e Q2", "fgv_pbh_p3-03.png"),
        "doc_424ae74c09fcc17c25f5": (3, "duas colunas, contexto literário e numeração", "fgv_ibge_orc_p3-03.png"),
        "doc_a21258c1c3793745484e": (12, "Redação, texto-base e comando separado", "fgv_stn_cont_redacao-12.png"),
    }
    if doc_id == "doc_cdae387002f58e6262e6":
        return [
            {"pagina_pdf": 12, "tipo": "Redação, reportagem como contexto e comando separado", "arquivo": "revisao-visual/fgv_stn_econ_redacao-12.png"},
            {"pagina_pdf": 14, "tipo": "folha de respostas numerada, excluída do fluxo", "arquivo": "revisao-visual/fgv_stn_af_p14-14.png"},
        ]
    if doc_id not in samples:
        return []
    page, kind, filename = samples[doc_id]
    return [{"pagina_pdf": page, "tipo": kind, "arquivo": "revisao-visual/" + filename}]


def main():
    docs = json.loads(MANIFEST.read_text(encoding="utf-8"))
    docs = [d for d in docs if d.get("banca") == "FGV" and d.get("tipo") == "provas"]
    all_records, details = [], []
    for doc in docs:
        with pdfplumber.open(doc["arquivo"]) as pdf:
            qs = parse_stream(page_stream(pdf))
        # Keep only a monotonic sequence of question numbers. Standalone numerals
        # also occur in tables, examples, and page furniture; those are not new items.
        rows = [split_item(q, doc) for q in qs]
        # Exclude line-only response scaffolding occasionally numbered as if it
        # were an item; keep substantive unlabelled response prompts for review.
        filtered = []
        for r in rows:
            if not re.search(r"[A-Za-zÀ-ÿ0-9]", r["texto_original_completo"]):
                continue
            filtered.append(r)
        rows = filtered
        link_repeated_contexts(rows)
        alt_counts = Counter(len(r["alternativas"]) for r in rows if len(r["alternativas"]) in (4, 5))
        expected_alternatives = alt_counts.most_common(1)[0][0] if alt_counts else None
        for r in rows:
            count = len(r["alternativas"])
            if count and expected_alternatives is not None and count != expected_alternatives:
                r["alertas"].append(f"Padrão do caderno: {expected_alternatives} alternativas; encontradas {count}. Conferir segmentação.")
                r["status_extracao"] = "precisa_revisao"
        expected_disc = expected_discursivas(doc)
        discursive = extract_discursiva(doc) if expected_disc else None
        if discursive:
            rows.append(discursive)
        nums = [int(r["numero_original"]) for r in rows if r["numero_original"].isdigit()]
        dup = sorted(n for n, c in Counter(nums).items() if c > 1)
        gaps = []
        if nums:
            gaps = sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
        expected = expected_count(doc)
        declared_range_note = None
        objective_count = sum(r["formato"] == "multipla_escolha" for r in rows)
        discursive_count = sum(r["formato"] == "discursiva" for r in rows)
        if expected is not None and objective_count != expected:
            if nums and nums[0] > 1:
                declared_range_note = f"Capa declara {expected} itens no conjunto da prova, mas este arquivo contém a sequência numerada {nums[0]}–{nums[-1]} ({objective_count} questões objetivas); a parte anterior pode estar em outro caderno/documento."
            else:
                declared_range_note = f"Capa declara {expected} questões objetivas; extraídas {objective_count} neste arquivo."
        if expected_disc is not None and discursive_count != expected_disc:
            declared_range_note = (declared_range_note + " " if declared_range_note else "") + f"Capa declara {expected_disc} discursiva(s); extraídas {discursive_count}."
        all_records.extend(rows)
        details.append({
            "documento_id": doc["documento_id"], "concurso": doc["concurso"], "arquivo": doc["arquivo_relativo"],
            "paginas": doc["paginas"], "quantidade_esperada_explicita": expected,
            "quantidade_esperada_discursivas_explicita": expected_disc,
            "questoes_extraidas": len(rows), "numeros_encontrados": [r["numero_original"] for r in rows],
            "lacunas": gaps, "duplicacoes": dup,
            "multipla_escolha": sum(r["formato"] == "multipla_escolha" for r in rows),
            "alternativas_por_documento": expected_alternatives,
            "discursivas": sum(r["formato"] == "discursiva" for r in rows),
            "precisa_revisao": sum(r["status_extracao"] == "precisa_revisao" for r in rows),
            "incompletas": sum(r["status_extracao"] == "incompleto" for r in rows),
            "alertas": [declared_range_note] if declared_range_note else [],
            "amostras_visuais_revisadas": visual_audit(doc["documento_id"]),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in all_records) + "\n", encoding="utf-8")
    report = {"grupo": "FGV", "execucao": "2026-10-29", "metodo": "pdfplumber com separação de colunas por geometria da página; questões sequenciadas monotonicamente; contextos compartilhados identificados apenas por blocos literais repetidos; sem categorização temática automática", "documentos": details, "total_questoes": len(all_records), "observacao": "Questões dependentes de figuras/tabelas mantêm transcrição e regiões para consulta ao PDF; classificar disciplinas/assuntos/habilidades exige revisão semântica e não foi preenchido automaticamente."}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"documentos": len(docs), "questoes": len(all_records), "out": str(OUT), "report": str(REPORT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
