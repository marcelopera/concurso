#!/usr/bin/env python3
"""Extrai questões de prova FCC, ESAF e Vunesp para lote JSONL auditável.

O extrator preserva o texto de página fornecido pelo pdfplumber, numeração e
regiões de origem em nível de página. Não tenta inferir disciplina/assunto.
"""
from __future__ import annotations
import json, re, hashlib, unicodedata
from pathlib import Path
from collections import Counter
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
BASE = Path(__file__).resolve().parent
RUN = BASE / "execucoes" / "2026-10-29"
MANIFEST = RUN / "documentos.json"
OUT = RUN / "lotes" / "fcc_esaf_vunesp.questoes.jsonl"
REPORT = RUN / "lotes" / "fcc_esaf_vunesp.relatorio.json"
AGENT = "fleet-luna-fcc-esaf-vunesp"

# Números de questão impressos no início da linha. Alternativas A-E continuam
# no bloco da questão; algarismos romanos internos não são tratados como itens.
START_DOT = re.compile(r"^\s*(?:Quest(?:ão|ao)\s*)?(\d{1,3})[.)](?=$|\s)\s*(.*?)\s*$", re.I)
START_ESAF = re.compile(r"^\s*(\d{1,3})\s*[-–—−]\s*(.*?)\s*$", re.I)
ALT = re.compile(r"^\s*\(([A-Ea-e])\)\s*(.*)$")
ALT2 = re.compile(r"^\s*([A-Ea-e])\)\s+(.*)$")
ALT_ONLY = re.compile(r"^\s*([A-Ea-e])\)\s*$")

def normalize(s):
    s = s.replace("\x0c", "\n").replace("\u00ad", "")
    s = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def expected_count(text):
    pats = [r"cont[eé]m\s*(\d{1,3})\s*quest(?:ões|oes)", r"(\d{1,3})\s*quest(?:ões|oes)\s*,?\s*numeradas?\s*de\s*1\s*a\s*(\d{1,3})"]
    for pat in pats:
        m = re.search(pat, text, re.I)
        if m:
            return int(m.group(2) if len(m.groups()) > 1 and m.group(2) else m.group(1))
    return None

def parse_alternatives(body):
    alts, current = [], None
    for line in body.splitlines():
        m = ALT.match(line) or ALT2.match(line)
        mo = ALT_ONLY.match(line)
        if m:
            if current: alts.append(current)
            current = {"rotulo": m.group(1), "texto": m.group(2).strip()}
        elif mo:
            if current: alts.append(current)
            current = {"rotulo": mo.group(1), "texto": ""}
        elif current and line.strip():
            current["texto"] += (" " if current["texto"] else "") + line.strip()
    if current: alts.append(current)
    # Ignore stray option-shaped material immediately before a complete A-E
    # set (for example the final alternative of a preceding shared passage).
    for i in range(max(0, len(alts) - 4)):
        if [a["rotulo"].upper() for a in alts[i:i+5]] == list("ABCDE"):
            return alts[i:i+5]
    return alts

def fmt(body, alts):
    if len(alts) >= 2: return "multipla_escolha"
    return None

def norm_refs(text):
    pat = re.compile(r"\b(?:Lei|Decreto|Constitui\w*|Emenda Constitucional|Código Civil|Código Penal|art(?:igo)?s?\.?\s*(?:n[ºo°.]?\s*)?)\s*(?:n[ºo°.]?\s*)?\d+(?:[.\d]*)?(?:\s*/\s*\d{2,4})?(?:\s*,?\s*(?:art(?:igo)?\.?\s*)?\d+[º°]?(?:\s*(?:,|e|a)\s*\d+[º°]?)?)?", re.I)
    return list(dict.fromkeys(m.group(0).strip() for m in pat.finditer(text)))

def main():
    docs = json.loads(MANIFEST.read_text(encoding="utf-8"))
    docs = [d for d in docs if d.get("tipo") == "provas" and d.get("banca") in {"FCC", "ESAF", "Vunesp"}]
    rows, reports = [], []
    for d in docs:
        pages, lines, dimensions, margins_by_page = [], [], [], {}
        cache_path = RUN / "paginas" / f"{d['documento_id']}.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else None
        if cache:
            for pno, cp in enumerate(cache["paginas"], 1):
                width, height = float(cp["largura"]), float(cp["altura"])
                clines = cp["linhas"]
                valid = [x for x in clines if 0 <= x["bbox"][0] < width and 0 <= x["bbox"][2] <= width]
                left = [x for x in valid if x["bbox"][0] < width / 2]
                right = [x for x in valid if x["bbox"][0] >= width / 2]
                # A true two-column page has text starts in both halves; in that
                # case process complete columns top-to-bottom, avoiding rows
                # interleaved by the PDF's extraction order.
                two_col = len(left) >= 5 and len(right) >= 5
                margins = [min(x["bbox"][0] for x in left)] if left else [0]
                if two_col and right:
                    margins.append(min(x["bbox"][0] for x in right))
                margins_by_page[pno] = margins
                if two_col:
                    ordered = sorted(left, key=lambda x: x["bbox"][1]) + sorted(right, key=lambda x: x["bbox"][1])
                else:
                    ordered = sorted(valid, key=lambda x: (x["bbox"][1], x["bbox"][0]))
                txt = normalize("\n".join(x["texto"] for x in ordered))
                pages.append(txt); dimensions.append((width, height))
                # Retain the coordinate for margin-based question-marker checks.
                for x in ordered:
                    lines.append((pno, x["texto"], x["bbox"]))
        else:
          with pdfplumber.open(d["arquivo"]) as pdf:
            for pno, page in enumerate(pdf.pages, 1):
                # Determine if the page has a real central gutter. pdfplumber's
                # global top-to-bottom sort interleaves two newspaper columns.
                words = page.extract_words() or []
                width, height = float(page.width), float(page.height)
                center_chars = sum(len(w.get("text", "")) for w in words if .45 * width <= (w["x0"]+w["x1"])/2 <= .55 * width)
                total_chars = sum(len(w.get("text", "")) for w in words) or 1
                has_left = any(w["x1"] < .47 * width for w in words)
                has_right = any(w["x0"] > .53 * width for w in words)
                two_col = has_left and has_right and center_chars / total_chars < .035
                if two_col:
                    left = page.crop((0, 0, width/2, height)).extract_text(layout=False) or ""
                    right = page.crop((width/2, 0, width, height)).extract_text(layout=False) or ""
                    txt = normalize(left + "\n" + right)
                else:
                    txt = normalize(page.extract_text(layout=False) or "")
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
                # Numeric text must start at the left edge of a column. This
                # excludes line references, numbered assertions, and prose lists.
                if bbox is not None:
                    x0 = bbox[0]
                    if min(abs(x0 - margin) for margin in margins_by_page.get(pno, [x0])) > 32:
                        continue
                # Ignore page numbering and table/list numbering outside exam body.
                tail = m.group(2).strip()
                if n >= 1 and len(tail) >= 2:
                    starts.append((idx, pno, str(n)))
                elif n >= 1 and not tail and idx + 1 < len(lines) and len(lines[idx+1][1].strip()) >= 3:
                    # Some PDFs put the question marker on its own line.
                    starts.append((idx, pno, str(n)))
        # Keep at most one occurrence of each printed question number, in
        # document order. Margin checks above provide the primary segmentation.
        compact, seen_starts = [], set()
        for s in starts:
            n = int(s[2])
            if expected is not None and n > expected: continue
            if n in seen_starts: continue
            compact.append(s); seen_starts.add(n)
        raw_numbers = {int(s[2]) for s in compact}
        # Some PDFs encode isolated graphic/table labels as large integers.
        # If those extend beyond 100, keep only the sequential exam run.
        if expected is None and raw_numbers and max(raw_numbers) > 100:
            cap = 0
            while cap + 1 in raw_numbers: cap += 1
            compact = [s for s in compact if int(s[2]) <= cap]
        # Shared reading passages often announce a question range. Preserve the
        # passage once as a context and link it to every numbered question in
        # that range; its position in the two-column flow may follow Q1.
        context_ranges = []
        range_re = re.compile(r"(?:quest(?:ões|oes)|quest(?:ão|ao))\s*(?:de\s+n[uú]meros\s*)?(?:de\s*)?(\d{1,3})\s*(?:a|à|até)\s*(\d{1,3})", re.I)
        start_indices = {s[0] for s in compact}
        for li, (pno, ln, bbox) in enumerate(lines):
            rm = range_re.search(ln)
            if not rm: continue
            a, b = int(rm.group(1)), int(rm.group(2))
            next_start = min((si for si in start_indices if si > li), default=len(lines))
            ctxt = normalize("\n".join(x[1] for x in lines[li:next_start]))
            if len(ctxt) > 35:
                cpages = sorted({x[0] for x in lines[li:next_start]})
                context_ranges.append((a, b, {"texto": ctxt, "paginas_pdf": cpages, "regioes_fonte": [{"pagina": p, "bbox": [0, 0, dimensions[p-1][0], dimensions[p-1][1]]} for p in cpages]}))
        nums, seen, gaps, dups = [], set(), [], []
        candidate_counts = Counter(int(s[2]) for s in starts)
        dups = [str(n) for n, count in sorted(candidate_counts.items()) if count > 1]
        for _, _, n in compact:
            seen.add(n); nums.append(int(n))
        # Keep printed order; each record may span multiple pages.
        for j, (idx, pstart, number) in enumerate(compact):
            end = compact[j+1][0] if j+1 < len(compact) else len(lines)
            raw = normalize("\n".join(ln for _, ln, _ in lines[idx:end]))
            alts = parse_alternatives(raw)
            pg = sorted({p for p, _, _ in lines[idx:end]}) or [pstart]
            # Avoid interpreting repeated headers/page numbers as substantive text.
            clean = re.sub(r"(?im)^\s*(?:Caderno de Prova.*|www\..*|\d{1,3}\s*)$", "", raw).strip()
            alerts = []
            if not clean: alerts.append("enunciado_vazio_apos_limpeza")
            if len(alts) not in (0, 5): alerts.append(f"quantidade_alternativas_detectada_{len(alts)}")
            if len(alts) == 0: alerts.append("alternativas_ou_formato_nao_identificados")
            if any("(cid:" in x for x in clean.lower().splitlines()): alerts.append("caractere_substituido_no_texto_pdf")
            region = [{"pagina": p, "bbox": [0, 0, dimensions[p-1][0], dimensions[p-1][1]]} for p in pg]
            row = {
                "documento_id": d["documento_id"], "prova_id": d["documento_id"],
                "numero_original": number, "bloco_original": d.get("nome"),
                "formato": fmt(clean, alts), "disciplina_original": None,
                "enunciado_original": clean, "alternativas": alts,
                "contextos": [ctx for a, b, ctx in context_ranges if a <= int(number) <= b],
                "paginas_pdf": pg, "regioes_fonte": region,
                "texto_original_completo": raw,
            "status_extracao": "precisa_revisao" if alerts else "extraido",
                "alertas": alerts, "classificacoes": [], "habilidades": [],
                "referencias_normativas_literais": norm_refs(clean),
                "metodo_extracao": "linhas/bboxes do cache pdfplumber; colunas separadas pelo eixo central e ordem vertical; segmentação por marcador numérico na margem; transcrição automática sem classificação semântica",
                "agente": AGENT,
            }
            rows.append(row)
        numeric = sorted(set(nums))
        if numeric:
            maxn = expected if expected is not None else max(numeric)
            gaps = [str(n) for n in range(1, maxn+1) if n not in set(nums)]
        reports.append({
            "documento_id": d["documento_id"], "banca": d["banca"], "concurso": d["concurso"],
            "arquivo": d["arquivo_relativo"], "paginas_manifesto": d["paginas"],
            "paginas_lidas": len(pages), "quantidade_esperada_explicita": expected,
            "questoes_extraidas": len(compact), "numeros_encontrados_em_ordem": nums,
            "lacunas_numeracao_ate_maximo": gaps, "duplicacoes_numero_detectadas": dups,
            "questoes_para_revisao": sum(1 for r in rows if r["documento_id"] == d["documento_id"] and r["status_extracao"] != "extraido"),
            "amostras_visuais_revisadas": ([{"pagina_pdf": 3, "arquivo_renderizado": "execucoes/2026-10-29/revisao-visual/piloto-vunesp-03.png", "observacao": "duas colunas e passagem compartilhada verificadas visualmente"}] if d["documento_id"] == "doc_996cea21fa0a001ca696" else ([{"pagina_pdf": 2, "arquivo_renderizado": "execucoes/2026-10-29/revisao-visual/piloto-fcc-02.png", "observacao": "texto contínuo, numeração e alternativas verificadas visualmente"}] if d["documento_id"] == "doc_1efe6714afa2325e6998" else [])),
            "alertas_documento": (["contagem_extraida_diverge_da_quantidade_explicita"] if expected is not None and len(compact) != expected else [])
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    report = {"grupo": "fcc_esaf_vunesp", "agente": AGENT, "metodo": "extração automática local das linhas e coordenadas do cache pdfplumber; duas colunas ordenadas por coluna e posição vertical; sem uso de gabaritos ou classificação semântica; bbox de página completa usado como região-fonte ampla", "total_documentos": len(docs), "total_questoes": len(rows), "documentos": reports}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"documentos": len(docs), "questoes": len(rows), "saida": str(OUT), "relatorio": str(REPORT)}, ensure_ascii=False))

if __name__ == "__main__": main()
