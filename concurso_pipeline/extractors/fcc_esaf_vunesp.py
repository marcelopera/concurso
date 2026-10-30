"""Extrai questões de prova FCC, ESAF e Vunesp para lote JSONL auditável.

O extrator preserva o texto de página fornecido pelo pdfplumber, numeração e
regiões de origem em nível de página. Não tenta inferir disciplina/assunto.
"""

import json
import re
from collections import Counter

import pdfplumber

from ..common import clean, expected_count, write_selected_batch
from ..config import config, load_documents, source_file

AGENT = "fleet-luna-fcc-esaf-vunesp"
START_DOT = re.compile("^\\s*(?:Quest(?:ão|ao)\\s*)?(\\d{1,3})[.)](?=$|\\s)\\s*(.*?)\\s*$", re.I)
START_ESAF = re.compile("^\\s*(\\d{1,3})\\s*[-–—−]\\s*(.*?)\\s*$", re.I)
ALT = re.compile("^\\s*\\(([A-Ea-e])\\)\\s*(.*)$")
ALT2 = re.compile("^\\s*([A-Ea-e])\\)\\s+(.*)$")
ALT_ONLY = re.compile("^\\s*([A-Ea-e])\\)\\s*$")


def parse_alternatives(body):
    alts, current = ([], None)
    for line in body.splitlines():
        m = ALT.match(line) or ALT2.match(line)
        mo = ALT_ONLY.match(line)
        if m:
            if current:
                alts.append(current)
            current = {"rotulo": m.group(1), "texto": m.group(2).strip()}
        elif mo:
            if current:
                alts.append(current)
            current = {"rotulo": mo.group(1), "texto": ""}
        elif current and line.strip():
            current["texto"] += (" " if current["texto"] else "") + line.strip()
    if current:
        alts.append(current)
    for i in range(max(0, len(alts) - 4)):
        if [a["rotulo"].upper() for a in alts[i : i + 5]] == list("ABCDE"):
            return alts[i : i + 5]
    return alts


def fmt(body, alts):
    if len(alts) >= 2:
        return "multipla_escolha"
    return "multipla_escolha"


def norm_refs(text):
    pat = re.compile(
        "\\b(?:Lei|Decreto|Constitui\\w*|Emenda Constitucional|Código Civil|Código Penal|art(?:igo)?s?\\.?\\s*(?:n[ºo°.]?\\s*)?)\\s*(?:n[ºo°.]?\\s*)?\\d+(?:[.\\d]*)?(?:\\s*/\\s*\\d{2,4})?(?:\\s*,?\\s*(?:art(?:igo)?\\.?\\s*)?\\d+[º°]?(?:\\s*(?:,|e|a)\\s*\\d+[º°]?)?)?",
        re.I,
    )
    return list(dict.fromkeys((m.group(0).strip() for m in pat.finditer(text))))


def main():
    docs = load_documents()
    docs = [d for d in docs if d.get("tipo") == "provas" and d.get("banca") in {"FCC", "ESAF", "Vunesp"}]
    rows, reports = ([], [])
    for d in docs:
        pages, lines, dimensions, margins_by_page = ([], [], [], {})
        cache_path = config().run_dir / "paginas" / f"{d['documento_id']}.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else None
        if cache:
            for pno, cp in enumerate(cache["paginas"], 1):
                width, height = (float(cp["largura"]), float(cp["altura"]))
                clines = cp["linhas"]
                valid = [x for x in clines if 0 <= x["bbox"][0] < width and 0 <= x["bbox"][2] <= width]
                left = [x for x in valid if x["bbox"][0] < width / 2]
                right = [x for x in valid if x["bbox"][0] >= width / 2]
                two_col = len(left) >= 5 and len(right) >= 5
                margins = [min((x["bbox"][0] for x in left))] if left else [0]
                if two_col and right:
                    margins.append(min((x["bbox"][0] for x in right)))
                margins_by_page[pno] = margins
                if two_col:
                    ordered = sorted(left, key=lambda x: x["bbox"][1]) + sorted(right, key=lambda x: x["bbox"][1])
                else:
                    ordered = sorted(valid, key=lambda x: (x["bbox"][1], x["bbox"][0]))
                txt = clean("\n".join((x["texto"] for x in ordered)))
                pages.append(txt)
                dimensions.append((width, height))
                for x in ordered:
                    lines.append((pno, x["texto"], x["bbox"]))
        else:
            with pdfplumber.open(source_file(d)) as pdf:
                for pno, page in enumerate(pdf.pages, 1):
                    words = page.extract_words() or []
                    width, height = (float(page.width), float(page.height))
                    center_chars = sum(
                        (
                            len(w.get("text", ""))
                            for w in words
                            if 0.45 * width <= (w["x0"] + w["x1"]) / 2 <= 0.55 * width
                        )
                    )
                    total_chars = sum((len(w.get("text", "")) for w in words)) or 1
                    has_left = any((w["x1"] < 0.47 * width for w in words))
                    has_right = any((w["x0"] > 0.53 * width for w in words))
                    two_col = has_left and has_right and (center_chars / total_chars < 0.035)
                    if two_col:
                        left = page.crop((0, 0, width / 2, height)).extract_text(layout=False) or ""
                        right = page.crop((width / 2, 0, width, height)).extract_text(layout=False) or ""
                        txt = clean(left + "\n" + right)
                    else:
                        txt = clean(page.extract_text(layout=False) or "")
                    pages.append(txt)
                    dimensions.append((width, height))
                    for ln in txt.splitlines():
                        lines.append((pno, ln, None))
        full = "\n".join(pages)
        expected = expected_count(full)
        starts = []
        for idx, (pno, ln, bbox) in enumerate(lines):
            m = (START_ESAF if d["banca"] == "ESAF" else START_DOT).match(ln)
            if m:
                n = int(m.group(1))
                if bbox is not None:
                    x0 = bbox[0]
                    if min((abs(x0 - margin) for margin in margins_by_page.get(pno, [x0]))) > 32:
                        continue
                tail = m.group(2).strip()
                if n >= 1 and len(tail) >= 2:
                    starts.append((idx, pno, str(n)))
                elif n >= 1 and (not tail) and (idx + 1 < len(lines)) and (len(lines[idx + 1][1].strip()) >= 3):
                    starts.append((idx, pno, str(n)))
        compact, seen_starts = ([], set())
        for s in starts:
            n = int(s[2])
            if expected is not None and n > expected:
                continue
            if n in seen_starts:
                continue
            compact.append(s)
            seen_starts.add(n)
        raw_numbers = {int(s[2]) for s in compact}
        if expected is None and raw_numbers and (max(raw_numbers) > 100):
            cap = 0
            while cap + 1 in raw_numbers:
                cap += 1
            compact = [s for s in compact if int(s[2]) <= cap]
        context_ranges = []
        range_re = re.compile(
            "(?:quest(?:ões|oes)|quest(?:ão|ao))\\s*(?:de\\s+n[uú]meros\\s*)?(?:de\\s*)?(\\d{1,3})\\s*(?:a|à|até)\\s*(\\d{1,3})",
            re.I,
        )
        start_indices = {s[0] for s in compact}
        for li, (pno, ln, bbox) in enumerate(lines):
            rm = range_re.search(ln)
            if not rm:
                continue
            a, b = (int(rm.group(1)), int(rm.group(2)))
            next_start = min((si for si in start_indices if si > li), default=len(lines))
            ctxt = clean("\n".join((x[1] for x in lines[li:next_start])))
            if len(ctxt) > 35:
                cpages = sorted({x[0] for x in lines[li:next_start]})
                context_ranges.append(
                    (
                        a,
                        b,
                        {
                            "texto": ctxt,
                            "paginas_pdf": cpages,
                            "regioes_fonte": [
                                {"pagina": p, "bbox": [0, 0, dimensions[p - 1][0], dimensions[p - 1][1]]}
                                for p in cpages
                            ],
                        },
                    )
                )
        nums, seen, gaps, dups = ([], set(), [], [])
        candidate_counts = Counter((int(s[2]) for s in starts))
        dups = [str(n) for n, count in sorted(candidate_counts.items()) if count > 1]
        for _, _, n in compact:
            seen.add(n)
            nums.append(int(n))
        for j, (idx, pstart, number) in enumerate(compact):
            end = compact[j + 1][0] if j + 1 < len(compact) else len(lines)
            raw = clean("\n".join((ln for _, ln, _ in lines[idx:end])))
            alts = parse_alternatives(raw)
            pg = sorted({p for p, _, _ in lines[idx:end]}) or [pstart]
            cleaned = re.sub("(?im)^\\s*(?:Caderno de Prova.*|www\\..*|\\d{1,3}\\s*)$", "", raw).strip()
            first_line, separator, remaining = cleaned.partition("\n")
            marker = (START_ESAF if d["banca"] == "ESAF" else START_DOT).match(first_line)
            if marker:
                cleaned = marker.group(2) + separator + remaining
            first_alternative = re.search(r"(?m)^\s*\(?[Aa]\)\s+", cleaned)
            if first_alternative:
                cleaned = cleaned[: first_alternative.start()].strip()
            alerts = []
            if not cleaned:
                alerts.append("enunciado_vazio_apos_limpeza")
            if len(alts) not in (0, 5):
                alerts.append(f"quantidade_alternativas_detectada_{len(alts)}")
            if len(alts) == 0:
                alerts.append("alternativas_ou_formato_nao_identificados")
            if any(("(cid:" in x for x in cleaned.lower().splitlines())):
                alerts.append("caractere_substituido_no_texto_pdf")
            region = [{"pagina": p, "bbox": [0, 0, dimensions[p - 1][0], dimensions[p - 1][1]]} for p in pg]
            row = {
                "documento_id": d["documento_id"],
                "prova_id": d["documento_id"],
                "numero_original": number,
                "bloco_original": d.get("nome"),
                "formato": fmt(cleaned, alts),
                "disciplina_original": None,
                "enunciado_original": cleaned,
                "alternativas": alts,
                "contextos": [ctx for a, b, ctx in context_ranges if a <= int(number) <= b],
                "paginas_pdf": pg,
                "regioes_fonte": region,
                "texto_original_completo": raw,
                "status_extracao": "precisa_revisao" if alerts else "extraido",
                "alertas": alerts,
                "classificacoes": [],
                "habilidades": [],
                "referencias_normativas_literais": norm_refs(cleaned),
                "metodo_extracao": "linhas/bboxes do cache pdfplumber; colunas separadas pelo eixo central e ordem vertical; segmentação por marcador numérico na margem; transcrição automática sem classificação semântica",
                "agente": AGENT,
            }
            rows.append(row)
        numeric = sorted(set(nums))
        if numeric:
            maxn = expected if expected is not None else max(numeric)
            gaps = [str(n) for n in range(1, maxn + 1) if n not in set(nums)]
        reports.append(
            {
                "documento_id": d["documento_id"],
                "banca": d["banca"],
                "concurso": d["concurso"],
                "arquivo": d["arquivo_relativo"],
                "paginas_manifesto": d["paginas"],
                "paginas_lidas": len(pages),
                "quantidade_esperada_explicita": expected,
                "questoes_extraidas": len(compact),
                "numeros_encontrados_em_ordem": nums,
                "lacunas_numeracao_ate_maximo": gaps,
                "duplicacoes_numero_detectadas": dups,
                "questoes_para_revisao": sum(
                    (1 for r in rows if r["documento_id"] == d["documento_id"] and r["status_extracao"] != "extraido")
                ),
                "amostras_visuais_revisadas": [],
                "alertas_documento": ["contagem_extraida_diverge_da_quantidade_explicita"]
                if expected is not None and len(compact) != expected
                else [],
            }
        )
    (config().run_dir / "lotes" / "fcc_esaf_vunesp.questoes.jsonl").parent.mkdir(parents=True, exist_ok=True)
    write_selected_batch(
        config().run_dir / "lotes" / "fcc_esaf_vunesp.questoes.jsonl", rows, [d["documento_id"] for d in docs]
    )
    report = {
        "grupo": "fcc_esaf_vunesp",
        "agente": AGENT,
        "metodo": "extração automática local das linhas e coordenadas do cache pdfplumber; duas colunas ordenadas por coluna e posição vertical; sem uso de gabaritos ou classificação semântica; bbox de página completa usado como região-fonte ampla",
        "total_documentos": len(docs),
        "total_questoes": len(rows),
        "documentos": reports,
    }
    (config().run_dir / "lotes" / "fcc_esaf_vunesp.relatorio.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "documentos": len(docs),
                "questoes": len(rows),
                "saida": str(config().run_dir / "lotes" / "fcc_esaf_vunesp.questoes.jsonl"),
                "relatorio": str(config().run_dir / "lotes" / "fcc_esaf_vunesp.relatorio.json"),
            },
            ensure_ascii=False,
        )
    )
