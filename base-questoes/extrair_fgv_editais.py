"""Extract FGV syllabus sections from the geometry-preserving page cache."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "execucoes" / "2026-10-29"
MANIFEST = RUN / "documentos.json"
PAGES = RUN / "paginas"
OUT = RUN / "lotes" / "fgv.topicos.jsonl"
REPORT = RUN / "lotes" / "fgv.editais.relatorio.json"
AGENT = "fleet-luna-fgv"

TOPIC_NUM = re.compile(r"(?<![\w/,])(\d{1,2}(?:\.\d{1,2}){0,3})\.\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])")
END_RE = re.compile(r"ANEXO\s+(?:II|III)\s*[–-].*(?:ATRIBUIÇÕES|REQUISITOS|VAGAS|PROTOCOLOS|MODELO|FORMULÁRIO|DECLARAÇÃO)", re.I)


def tidy(s):
    return re.sub(r"\s+", " ", s).strip()


def page_lines(page):
    """Merge cache fragments sharing a baseline, keeping the original PDF order."""
    width = page.get("largura", 595.32)
    raw = sorted((x for x in page["linhas"] if x["bbox"][0] < width * 0.92), key=lambda x: (x["bbox"][1], x["bbox"][0]))
    groups = []
    for line in raw:
        if groups and abs(line["bbox"][1] - groups[-1]["top"]) <= 0.8 and line["bbox"][0] - groups[-1]["right"] < 40:
            g = groups[-1]
            g["parts"].append(line)
            g["right"] = max(g["right"], line["bbox"][2])
            g["top"] = min(g["top"], line["bbox"][1])
            g["bottom"] = max(g["bottom"], line["bbox"][3])
        else:
            groups.append({"top": line["bbox"][1], "bottom": line["bbox"][3], "right": line["bbox"][2], "parts": [line]})
    result = []
    for g in groups:
        parts = sorted(g["parts"], key=lambda x: x["bbox"][0])
        text = tidy(" ".join(x["texto"] for x in parts))
        bbox = [min(x["bbox"][0] for x in parts), g["top"], max(x["bbox"][2] for x in parts), g["bottom"]]
        if text:
            result.append({"texto": text, "pagina": page["numero"], "bbox": bbox})
    return result


def appendix_bounds(pages):
    starts = []
    for i, p in enumerate(pages):
        lines = [x["texto"] for x in page_lines(p)]
        direct = any(re.search(r"^\s*ANEXO\s+(?:I(?!I)|II)\s*[–-]\s*CONTEÚDOS?\s+PROGRAMÁTICOS?", s, re.I) for s in lines)
        split = any(re.match(r"^ANEXO\s+II\s*$", s, re.I) and j + 1 < len(lines) and re.match(r"^CONTEÚDOS?\s+PROGRAMÁTICOS?", lines[j + 1], re.I) for j, s in enumerate(lines))
        if direct or split:
            starts.append(i)
    if not starts:
        return None, None
    start = starts[-1] if len(starts) > 1 else starts[0]
    end = len(pages)
    for i in range(start + 1, len(pages)):
        lines = page_lines(pages[i])
        joined = " ".join(x["texto"] for x in lines)
        if re.search(r"ANEXO\s+(?:II|III)\s*[–-]?\s*.{0,120}(?:ATRIBUIÇÕES|REQUISITOS|VAGAS|PROTOCOLOS|MODELO|FORMULÁRIO|DECLARAÇÃO)", joined, re.I):
            end = i
            break
    return start, end


def is_heading(s):
    s = s.strip()
    if s.startswith("") or s.startswith("▶") or s.startswith("▸"):
        return True
    if len(s) < 4 or len(s) > 180:
        return False
    alpha = re.sub(r"[^A-Za-zÀ-ÿ]", "", s)
    if len(alpha) < 4 or alpha != alpha.upper():
        return False
    return not re.search(r"^(EDITAL|CONCURSO PÚBLICO|PREFEITURA|INSTITUTO|SECRETARIA|EMPRESA DE PESQUISA|FGV |REALIZAÇÃO)", s, re.I)


def classify_scope(line, state, concurso, all_areas):
    u = line.upper()
    if re.search(r"\bPROVA\s+1\b", u):
        state["bloco"] = "comum"
        state["cargos"] = ["Analista de Planejamento e Orçamento"]
        state["especialidades"] = []
        return True
    if re.search(r"\bPROVA\s+2\b", u):
        state["bloco"] = "especifico"
        state["cargos"] = ["Analista de Planejamento e Orçamento"]
        state["especialidades"] = []
        return True
    # Only treat explicit scope headers as scope controls. Phrases such as
    # "CONHECIMENTOS BÁSICOS" also occur as discipline labels inside a single
    # specialty (notably the EPE IT profiles).
    if (re.fullmatch(r"COMUM\s+A\s+TODAS\s+AS\s+ÁREAS", u)
            or re.fullmatch(r"CONHECIMENTOS\s+GERAIS\s*\(\s*COMUM\s+A\s+TODAS\s+AS\s+ÁREAS\s*\)\s*:?", u)
            or re.fullmatch(r"CARGOS?\s+DE\s+NÍVEL\s+SUPERIOR", u)
            or re.fullmatch(r"CONHECIMENTOS\s+BÁSICOS", u)):
        state["bloco"] = "comum"
        if "STN" in concurso:
            state["cargos"] = ["Auditor Federal de Finanças e Controle"]
            state["especialidades"] = all_areas
        elif "EPE" in concurso:
            state["cargos"] = ["Analista de Gestão Corporativa"]
            state["especialidades"] = all_areas
        elif "IBGE" in concurso:
            state["cargos"] = ["Analista", "Tecnologista"]
            state["especialidades"] = ["Todas, exceto Tecnologista – Estatística"]
        return True
    if "ANALISTA E TECNOLOGISTA" in u:
        state["cargos"] = ["Analista", "Tecnologista"]
        state["especialidades"] = ["Todas, exceto Tecnologista – Estatística"]
        return True
    if u.startswith("CARGO:") or u.startswith("CARGOS:"):
        line_value = re.sub(r"^CARGOS?:\s*", "", line, flags=re.I)
        m_area = re.search(r"ÁREA\s+DE\s+ATUAÇÃO:\s*([^;]+)", line_value, re.I)
        cargo_part = re.split(r"ÁREA\s+DE\s+ATUAÇÃO:", line_value, flags=re.I)[0].strip(" –-:")
        if cargo_part:
            state["cargos"] = [tidy(x) for x in re.split(r"\s*/\s*", cargo_part) if tidy(x)]
        state["especialidades"] = []
        state["bloco"] = "comum"
        if m_area:
            state["especialidades"] = [tidy(m_area.group(1)).strip(" –-")]
            state["bloco"] = "especifico"
        return True
    if u.startswith("ÁREA DE ATUAÇÃO:") or u.startswith("ÁREA DE CONHECIMENTO:"):
        val = re.split(r":", line, maxsplit=1)[-1]
        val = re.split(r"\bFORMAÇÃO\s*:", val, maxsplit=1, flags=re.I)[0]
        state["especialidades"] = [tidy(val).strip(" –-")]
        state["bloco"] = "especifico"
        return True
    if u == "ANALISTA":
        state["cargos"] = ["Analista"]
        state["especialidades"] = []
        state["bloco"] = "especifico"
        return True
    if u == "TECNOLOGISTA":
        state["cargos"] = ["Tecnologista"]
        state["especialidades"] = []
        state["bloco"] = "especifico"
        return True
    if re.match(r"^(?:[IVX]+\s*[–—-]\s*)?CONHECIMENTOS\s+(?:ESPECÍFICOS|BÁSICOS|GERAIS)\s*:?", u):
        # In EPE, numbered knowledge blocks are part of the already identified
        # specialty and must not overwrite that scope.
        if "EPE" in concurso:
            state["bloco"] = "especifico"
            return True
        state["bloco"] = "especifico"
        m = re.search(r"ESPECÍFICOS\s*[–-]\s*(.+)$", line, re.I)
        if m:
            value = tidy(m.group(1))
            if "ANALISTA DE POLÍTICAS PÚBLICAS/" in value.upper() or "ANALISTA DE PLANEJAMENTO" in value.upper():
                role, specialty = value.split("/", 1)
                state["cargos"] = [tidy(role)]
                state["especialidades"] = [tidy(specialty)]
            else:
                state["especialidades"] = [value]
        return True
    return False


def split_topics(text):
    text = text.strip()
    matches = list(TOPIC_NUM.finditer(text))
    if not matches:
        return [(None, text)] if text else []
    parts = []
    prefix = text[:matches[0].start()].strip(" ;\n")
    if prefix:
        parts.append((None, prefix))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        number = m.group(1)
        content = text[m.end():end].strip(" ;\n")
        parts.append((number, (number + ". " + content).strip()))
    return parts


def extract_doc(doc):
    cache_path = PAGES / f"{doc['documento_id']}.json"
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    pages = data["paginas"]
    start, end = appendix_bounds(pages)
    if start is None:
        return [], {"status": "incompleto", "alertas": ["Anexo de conteúdo programático não localizado no cache."]}
    lines = []
    for p in pages[start:end]:
        lines.extend(page_lines(p))
    if "EPE" in doc["concurso"]:
        all_areas = ["Recursos Humanos – Perfil 1", "Recursos Humanos – Perfil 2: Comunicação", "Administração Geral – Perfil 1: Administração", "Administração Geral – Perfil 2: Governança Corporativa", "Contabilidade", "Finanças e Orçamento", "Tecnologia da Informação – Perfil 1: Infraestrutura e Segurança", "Tecnologia da Informação – Perfil 2: Soluções", "Tecnologia da Informação – Perfil 3: Ciência de Dados"]
    elif "STN" in doc["concurso"]:
        all_areas = ["Econômico-Financeira", "Econômico-Financeira – Contratações", "Contábil", "TI – Operação e Infraestrutura", "TI – Transformação Digital"]
    else:
        all_areas = []
    # Remove the annex heading and stop at any subsequent annex/requirements.
    cleaned = []
    ix = 0
    while ix < len(lines):
        line = lines[ix]
        s = line["texto"]
        if re.search(r"ANEXO\s+(?:I(?!I)|II)\s*[–-]?\s*CONTEÚDOS?\s+PROGRAMÁTICOS?", s, re.I) or re.match(r"^ANEXO\s+II$|^CONTEÚDOS?\s+PROGRAMÁTICOS?$", s, re.I):
            ix += 1
            continue
        if END_RE.search(s):
            break
        if re.search(r"^(?:EDITAL\s+N[º°]|CONCURSO PÚBLICO|FGV CONHECIMENTO|INSTITUTO BRASILEIRO|EMPRESA DE PESQUISA ENERGÉTICA|SECRETARIA DO TESOURO NACIONAL)", s, re.I):
            ix += 1
            continue
        if "PBH" in doc["concurso"] and s.upper().endswith("/CIÊNCIAS DA") and ix + 1 < len(lines) and lines[ix + 1]["texto"].upper() == "COMPUTAÇÃO":
            line = dict(line)
            line["texto"] = s + " COMPUTAÇÃO"
            line["bbox"] = [line["bbox"][0], line["bbox"][1], max(line["bbox"][2], lines[ix + 1]["bbox"][2]), max(line["bbox"][3], lines[ix + 1]["bbox"][3])]
            ix += 1
        cleaned.append(line)
        ix += 1

    state = {"bloco": "nao_identificado", "cargos": [], "especialidades": []}
    sections, current = [], None
    for line in cleaned:
        s = line["texto"].strip()
        # Scope and test-part headers are control markers, not syllabus topics.
        if classify_scope(s, state, doc["concurso"], all_areas):
            if current:
                sections.append(current)
                current = None
            continue
        prefix_heading = re.match(r"^([A-ZÀ-Ý][A-ZÀ-Ý0-9 /(),–—-]{3,100}):\s*(.+)$", s)
        if prefix_heading and not re.match(r"^(?:LEI|DECRETO|PORTARIA|ART\.)\b", prefix_heading.group(1), re.I):
            if current:
                sections.append(current)
            heading = tidy(prefix_heading.group(1))
            if state["bloco"] == "especifico" and "IBGE" in doc["concurso"]:
                state["especialidades"] = [heading]
            current = {"heading": heading, "lines": [prefix_heading.group(2).strip()], "scope": dict(state), "pages": {line["pagina"]: line["bbox"]}}
            continue
        if is_heading(s):
            if current:
                sections.append(current)
            heading = s.lstrip("▶▸ ").strip()
            if state["bloco"] == "especifico" and "IBGE" in doc["concurso"] and not heading.startswith("CONHECIMENTOS ESPECÍFICOS"):
                state["especialidades"] = [heading]
            current = {"heading": heading, "lines": [], "scope": dict(state)}
            current["pages"] = {line["pagina"]: line["bbox"]}
            continue
        if current is None:
            # Unheaded text is preserved as a section under an explicit neutral title.
            current = {"heading": "(sem título impresso)", "lines": [], "scope": dict(state), "pages": {}}
        current["lines"].append(s)
        b = line["bbox"]
        pno = line["pagina"]
        if pno not in current["pages"]:
            current["pages"][pno] = b
        else:
            old = current["pages"][pno]
            current["pages"][pno] = [min(old[0], b[0]), min(old[1], b[1]), max(old[2], b[2]), max(old[3], b[3])]
    if current:
        sections.append(current)

    records, report_sections = [], []
    order = 0
    for sec in sections:
        body = tidy(" ".join(sec["lines"]))
        heading = sec["heading"]
        if not body or not re.search(r"[A-Za-zÀ-ÿ0-9]", body):
            continue
        scope = sec["scope"]
        scope_label = " / ".join(scope["cargos"] + scope["especialidades"])
        chunks = split_topics(body)
        section_parent = None
        # A heading becomes an explicit parent only when the source has numbered children.
        if len(chunks) > 1 and not heading.startswith("(sem título"):
            order += 1
            section_parent = f"{doc['documento_id']}_p{min(sec['pages'])}_h{order}"
            records.append({
                "documento_id": doc["documento_id"], "topico_id_local": section_parent,
                "topico_pai_id_local": None, "numero_original": None, "ordem_original": order,
                "texto_original": heading, "disciplina_original": heading,
                "caminho_original": [heading],
                "escopo_cargos": scope["cargos"], "escopo_especialidades": scope["especialidades"],
                "bloco": scope["bloco"], "tipo_publicacao": "abertura-retificada-consolidada",
                "estado_na_versao": "retificado; versão compilada no arquivo disponível",
                "paginas_pdf": sorted(sec["pages"]),
                "regioes_fonte": [{"pagina": p, "bbox": [round(v, 2) for v in b]} for p, b in sorted(sec["pages"].items())],
                "conceitos_normalizados": [], "status_extracao": "extraido", "alertas": [],
                "metodo_extracao": "Cache geométrico de linhas PDF; cabeçalho de disciplina impresso como agrupador hierárquico.", "agente": AGENT
            })
        number_parent = {}
        for num, text in chunks:
            order += 1
            tid = f"{doc['documento_id']}_p{min(sec['pages'])}_t{order}"
            parent_id = section_parent
            if num and "." in num:
                parent_num = num.rsplit(".", 1)[0]
                parent_id = number_parent.get(parent_num, section_parent)
            elif num and section_parent:
                number_parent[num] = tid
            no_subject_heading = heading.startswith("(sem título")
            topic_path = ([*(scope["especialidades"] or scope["cargos"]), num] if no_subject_heading else [heading, num])
            records.append({
                "documento_id": doc["documento_id"], "topico_id_local": tid,
                "topico_pai_id_local": parent_id, "numero_original": num, "ordem_original": order,
                "texto_original": text, "disciplina_original": None if no_subject_heading else heading,
                "caminho_original": [x for x in topic_path if x],
                "escopo_cargos": scope["cargos"], "escopo_especialidades": scope["especialidades"],
                "bloco": scope["bloco"], "tipo_publicacao": "abertura-retificada-consolidada",
                "estado_na_versao": "retificado; versão compilada no arquivo disponível",
                "paginas_pdf": sorted(sec["pages"]),
                "regioes_fonte": [{"pagina": p, "bbox": [round(v, 2) for v in b]} for p, b in sorted(sec["pages"].items())],
                "conceitos_normalizados": [], "status_extracao": "extraido",
                "alertas": (["A fonte não imprime um subtítulo disciplinar autônomo para este conteúdo; disciplina_original permanece nula."] if no_subject_heading else []),
                "metodo_extracao": "Cache geométrico de linhas PDF; segmentação de itens numerados explícitos preservando a numeração literal.", "agente": AGENT
            })
        report_sections.append({"disciplina_original": None if heading.startswith("(sem título") else heading, "itens": len(chunks), "paginas_pdf": sorted(sec["pages"]), "escopo_cargos": scope["cargos"], "escopo_especialidades": scope["especialidades"], "bloco": scope["bloco"], "alerta_subtitulo_ausente": heading.startswith("(sem título")})
    return records, {"status": "extraido", "paginas_anexo": list(range(start + 1, end + 1)), "secoes": report_sections}


def main():
    docs = [d for d in json.loads(MANIFEST.read_text(encoding="utf-8")) if d.get("banca") == "FGV" and d.get("tipo") == "editais"]
    all_topics, details = [], []
    for doc in docs:
        rows, info = extract_doc(doc)
        all_topics.extend(rows)
        details.append({"documento_id": doc["documento_id"], "concurso": doc["concurso"], "arquivo": doc["arquivo_relativo"], "paginas": doc["paginas"], "topicos_extraidos": len(rows), **info})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in all_topics) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps({"grupo": "FGV editais", "execucao": "2026-10-29", "metodo": "Extração por anexo de conteúdo programático a partir do cache geométrico; cabeçalhos de disciplina e escopo preservados; enumerações literais segmentadas conservadoramente.", "documentos": details, "total_topicos": len(all_topics), "observacao": "Os PDFs disponíveis são aberturas retificadas consolidadas. O histórico comparativo de retificações não está presente em arquivos separados nesta execução; nenhum conteúdo foi inferido de requisitos ou atribuições."}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"documentos": len(docs), "topicos": len(all_topics), "out": str(OUT), "report": str(REPORT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
