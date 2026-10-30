"""Extrai tópicos programáticos dos editais FCC/Vunesp indicados na rodada."""

import hashlib
import json
import re
import unicodedata

from ..common import clean
from ..config import config, load_documents

AGENT = "fleet-luna-fcc-vunesp-editais"
IDS = {
    "fcc_open": "doc_4e7d69a7ee3f185e9d35",
    "fcc_ret": "doc_3cf98ff08920cbb07ace",
    "camprev": "doc_8f4a14e95f8cc0baa09a",
    "aftm": "doc_0ef744d31327692325c5",
}


def slug(s):
    a = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub("[^a-z0-9]+", "-", a).strip("-")[:48] or "topico"


def load_doc(docid):
    return json.loads((config().run_dir / "paginas" / f"{docid}.json").read_text(encoding="utf-8"))


def page_region(cache, pnos):
    out = []
    for n in sorted(set(pnos)):
        pg = cache["paginas"][n - 1]
        out.append({"pagina": n, "bbox": [0, 0, float(pg["largura"]), float(pg["altura"])]})
    return out


def add_topic(
    rows,
    d,
    cache,
    *,
    title,
    body,
    pages,
    path,
    scopes,
    specialties,
    block,
    publication="abertura",
    state="vigente_no_edital_de_abertura",
    parent=None,
    number=None,
    order=None,
    alert=None,
):
    body = clean(body)
    if not body and (not title):
        return
    identity = "|".join(
        [
            d["documento_id"],
            str(parent),
            title,
            "/".join(path),
            str(number),
            str(order),
            "/".join(scopes),
            "/".join(specialties),
        ]
    )
    local = f"{d['documento_id']}:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:18]}"
    text = body if body else title
    rows.append(
        {
            "documento_id": d["documento_id"],
            "topico_id_local": local,
            "topico_pai_id_local": parent,
            "numero_original": number,
            "ordem_original": order if order is not None else len(rows) + 1,
            "texto_original": text,
            "disciplina_original": title,
            "caminho_original": path,
            "escopo_cargos": scopes,
            "escopo_especialidades": specialties,
            "bloco": block,
            "tipo_publicacao": publication,
            "estado_na_versao": state,
            "paginas_pdf": sorted(set(pages)),
            "regioes_fonte": page_region(cache, pages),
            "conceitos_normalizados": [],
            "status_extracao": "precisa_revisao" if alert else "extraido",
            "alertas": [alert] if alert else [],
            "metodo_extracao": "segmentação semântica por cabeçalhos e escopos impressos; texto literal do cache pdfplumber; itens numerados separados somente quando expressos na fonte",
            "agente": AGENT,
        }
    )
    return local


def split_numbered(rows, d, cache, title, body, pages, path, scopes, specialties, block):
    """Representa hierarquia impressa numerada sem inventar itens."""
    body = clean(body)
    if not body:
        return
    rx = re.compile("(?<!\\d)(\\d{1,2}(?:\\.[1-9])?)\\.(?=\\s)")
    ms = [m for m in rx.finditer(body) if int(m.group(1).split(".")[0]) <= 40]
    if len(ms) < 2 or len(body[: ms[0].start()].strip()) > 90:
        add_topic(
            rows,
            d,
            cache,
            title=title,
            body=body,
            pages=pages,
            path=path,
            scopes=scopes,
            specialties=specialties,
            block=block,
        )
        return
    parent = add_topic(
        rows,
        d,
        cache,
        title=title,
        body=title,
        pages=pages,
        path=path,
        scopes=scopes,
        specialties=specialties,
        block=block,
    )
    order = 0
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(body)
        chunk = clean(body[m.start() : end])
        if len(chunk) < 3:
            continue
        order += 1
        add_topic(
            rows,
            d,
            cache,
            title=title,
            body=chunk,
            pages=pages,
            path=path + [m.group(1)],
            scopes=scopes,
            specialties=specialties,
            block=block,
            parent=parent,
            number=m.group(1),
            order=order,
        )


def lines_range(cache, lo, hi):
    arr = []
    for pg in cache["paginas"][lo - 1 : hi]:
        for x in pg["linhas"]:
            tx = x["texto"].strip()
            if not tx or re.fullmatch("\\d{1,3}", tx):
                continue
            arr.append((pg["numero"], tx, x["bbox"]))
    return arr


def find_line(lines, pat, start=0):
    rx = re.compile(pat, re.I)
    for i in range(start, len(lines)):
        if rx.match(lines[i][1].strip()):
            return i
    return None


def split_by_headings(lines, heading_patterns, start=0, end=None):
    end = len(lines) if end is None else end
    marks = []
    for name, pat in heading_patterns:
        idx = find_line(lines[start:end], pat)
        if idx is not None:
            marks.append((idx + start, name))
    marks = sorted(set(marks))
    out = []
    for j, (idx, name) in enumerate(marks):
        stop = marks[j + 1][0] if j + 1 < len(marks) else end
        head_text = lines[idx][1]
        inline = head_text if ":" in head_text else ""
        body = clean("\n".join(([inline] if inline else []) + [t for _, t, _ in lines[idx + 1 : stop]]))
        pnos = [p for p, _, _ in lines[idx:stop]]
        out.append((name, body, pnos))
    return out


def find_marker(text, marker, start=0):
    m = re.search(marker, text[start:], re.I | re.M)
    return None if m is None else start + m.start()


def emit_plain_section(rows, d, cache, title, body, pages, path, scopes, specialties, block):
    if body.strip():
        split_numbered(rows, d, cache, title, body, pages, path, scopes, specialties, block)


def extract_fcc(rows, docs, cache):
    d = docs[IDS["fcc_open"]]
    lines = lines_range(cache, 31, 36)
    common = [
        ("Administração Geral e Pública", "Administração Geral, Administração Pública e Auditoria Governamental"),
        ("Direito Administrativo", "Direito Administrativo"),
        ("Direito Constitucional", "Direito Constitucional"),
        ("Economia", "Economia"),
        ("Língua Portuguesa", "Língua Portuguesa"),
        ("Matemática Financeira e Estatística", "Matemática Financeira\\s*/\\s*Estatística"),
        ("Administração Financeira e Orçamentária", "Administração Financeira e Orçamentária"),
        ("Contabilidade Geral e Pública", "Contabilidade Geral e Pública"),
        ("Direito Financeiro e Finanças Públicas", "Direito Financeiro e Finanças Públicas"),
        ("Fluência de Dados", "Fluência de Dados"),
    ]
    p2 = find_line(lines, "PROVA 2")
    sections = split_by_headings(lines, common, 0, p2)
    areas = ["Orçamento e Finanças Públicas", "Contabilidade Pública", "Ciências de Dados e Tecnologia da Informação"]
    common_scopes = ["Analista em Planejamento, Orçamento e Finanças Públicas"]
    for title, body, pages in sections:
        if title == "Administração Geral e Pública":
            sub = [
                ("Administração Geral e Pública", "Administração Geral e Pública \\(Convergência Público-Privada\\):"),
                (
                    "Auditoria Governamental e Controle Interno",
                    "Auditoria\\s+Governamental\\s+e\\s+Controle\\s+Interno:",
                ),
            ]
            for name, b, p in split_by_headings(lines, sub, 0, p2):
                emit_plain_section(
                    rows, d, cache, name, b, p, ["Prova 1 e Prova 3", name], common_scopes, areas, "comum"
                )
        elif title == "Matemática Financeira e Estatística":
            sub = [("Matemática Financeira", "Matemática Financeira:"), ("Estatística", "Estatística:")]
            for name, b, p in split_by_headings(lines, sub, 0, p2):
                emit_plain_section(
                    rows, d, cache, name, b, p, ["Prova 1 e Prova 3", name], common_scopes, areas, "comum"
                )
        elif title == "Fluência de Dados":
            sub = [
                ("Ciência de Dados", "Ciência\\s+de\\s+Dados:"),
                (
                    "Segurança da Informação e Proteção de Dados",
                    "Segurança\\s+da\\s+Informação\\s+e\\s+Proteção\\s+de\\s+Dados:",
                ),
            ]
            for name, b, p in split_by_headings(lines, sub, 0, p2):
                emit_plain_section(
                    rows, d, cache, name, b, p, ["Prova 1 e Prova 3", name], common_scopes, areas, "comum"
                )
        else:
            emit_plain_section(
                rows, d, cache, title, body, pages, ["Prova 1 e Prova 3", title], common_scopes, areas, "comum"
            )
    p2lines = lines_range(cache, 35, 36)
    a = find_line(p2lines, "A01:\\s*CONHECIMENTOS ESPECÍFICOS")
    b = find_line(p2lines, "B02:\\s*CONHECIMENTOS ESPECÍFICOS")
    c = find_line(p2lines, "C03:\\s*CONHECIMENTOS ESPECÍFICOS")
    specs = [
        ("Orçamento e Finanças Públicas", a, b, ["Orçamento e Finanças Públicas"]),
        ("Contabilidade Pública", b, c, ["Contabilidade Pública"]),
        (
            "Ciências de Dados e Tecnologia da Informação",
            c,
            len(p2lines),
            ["Ciências de Dados e Tecnologia da Informação"],
        ),
    ]
    for area, start, stop, specialty in specs:
        if start is None:
            continue
        stop = len(p2lines) if stop is None else stop
        blocklines = p2lines[start + 1 : stop]
        pats = []
        if area == "Orçamento e Finanças Públicas":
            pats = [
                (
                    "Execução orçamentária e financeira por fonte/destinação",
                    "Apuração\\s+e\\s+utilização\\s+do\\s+superávit",
                ),
                (
                    "Tópicos Avançados da Lei de Responsabilidade Fiscal",
                    "Tópicos Avançados da Lei de Responsabilidade Fiscal",
                ),
            ]
        elif area == "Contabilidade Pública":
            pats = [
                (n, re.escape(n) + ":")
                for n in [
                    "Contabilidade Geral",
                    "Contabilidade Pública",
                    "Contabilidade de Custos",
                    "Responsabilidade Fiscal e Demonstrativos",
                    "Tecnologia Aplicada à Contabilidade",
                ]
            ]
        else:
            pats = [
                (n, re.escape(n) + ":")
                for n in [
                    "Gestão ágil de produtos e projetos digitais",
                    "Ciência de dados e inteligência artificial",
                    "Business Intelligence, Analytics e Visualização",
                ]
            ]
        sections = split_by_headings(blocklines, pats)
        if not sections and blocklines:
            sections = [(area, clean("\n".join((x[1] for x in blocklines))), [x[0] for x in blocklines])]
        for title, body, pages in sections:
            emit_plain_section(
                rows, d, cache, title, body, pages, ["Prova 2", area, title], common_scopes, specialty, "especifico"
            )


def extract_aftm(rows, docs, cache):
    d = docs[IDS["aftm"]]
    cargo = "Auditor Fiscal Tributário Municipal"
    specialties = ["Gestão Tributária", "Tecnologia da Informação"]
    lines = lines_range(cache, 35, 52)
    first_end = find_line(lines, "CONHECIMENTOS ESPECÍFICOS")
    common_heads = [
        ("Língua Portuguesa", "Língua Portuguesa:"),
        ("Métodos Quantitativos e Raciocínio Lógico", "Métodos Quantitativos e Raciocínio Lógico:"),
        ("Direito Tributário", "Direito Tributário:"),
    ]
    for title, body, pages in split_by_headings(lines, common_heads, 0, first_end):
        emit_plain_section(
            rows,
            d,
            cache,
            title,
            body,
            pages,
            ["Prova Objetiva 1", "Conhecimentos Gerais", title],
            [cargo],
            specialties,
            "comum",
        )
    shared_pages = lines_range(cache, 35, 43)
    spec_heads = [
        ("Legislação Tributária Municipal", "Legislação Tributária Municipal:"),
        ("Direito Constitucional", "Direito Constitucional:"),
        ("Direito Administrativo", "Direito Administrativo:"),
        ("Auditoria", "Auditoria:"),
    ]
    spec_heads = [(n, pat.replace(":", "\\s*:?")) for n, pat in spec_heads]
    spec_start = find_line(shared_pages, "CONHECIMENTOS ESPECÍFICOS")
    p3_boundary = find_line(shared_pages, "Direito Civil, Empresarial e Criminal:", (spec_start or 0) + 1)
    specific = split_by_headings(shared_pages, spec_heads, (spec_start or 0) + 1, p3_boundary)
    for title, body, pages in specific:
        emit_plain_section(
            rows,
            d,
            cache,
            title,
            body,
            pages,
            ["Prova Objetiva 2", "Conhecimentos Específicos", title],
            [cargo],
            specialties,
            "especifico",
        )
    track_specs = {
        "Gestão Tributária": [
            ("Direito Civil, Empresarial e Criminal", "Direito Civil, Empresarial e Criminal:"),
            ("Contabilidade Pública", "Contabilidade Pública:"),
            ("Conhecimentos em Economia e Finanças Públicas", "Conhecimentos em Economia e Finanças Públicas:"),
            ("Contabilidade Societária", "Contabilidade Societária:"),
            ("Gestão Pública Contemporânea", "Gestão Pública Contemporânea:"),
        ],
        "Tecnologia da Informação": [
            ("Conhecimentos em Economia e Finanças Públicas", "Conhecimentos em Economia e Finanças Públicas:"),
            ("Tecnologia da Informação", "Tecnologia da Informação\\s*$"),
            ("Contabilidade Societária", "Contabilidade Societária\\s*:?"),
        ],
    }
    for specialty, heads in track_specs.items():
        lo, hi = (35, 43) if specialty == "Gestão Tributária" else (44, 51)
        track = lines_range(cache, lo, hi)
        for title, body, pages in split_by_headings(track, heads):
            emit_plain_section(
                rows,
                d,
                cache,
                title,
                body,
                pages,
                ["Prova Objetiva 3", "Conhecimentos Específicos", title],
                [cargo],
                [specialty],
                "especifico",
            )


def extract_camprev(rows, docs, cache):
    d = docs[IDS["camprev"]]
    med = lines_range(cache, 30, 30)
    upper = lines_range(cache, 30, 31)
    pro = lines_range(cache, 32, 34)
    scopes = ["Agente Administrativo"]
    med_heads = [
        ("Língua Portuguesa", "Língua\\s+Portuguesa:"),
        ("Matemática / Raciocínio Lógico", "Matemática\\s*/\\s*Raciocínio\\s+Lógico:"),
        ("Matemática / Raciocínio Lógico", "Matemática\\s*$"),
    ]
    for title, body, pages in split_by_headings(med, med_heads):
        emit_plain_section(
            rows,
            d,
            cache,
            title,
            body,
            pages,
            ["Ensino Médio completo", "Conhecimentos Gerais", title],
            scopes,
            [],
            "comum",
        )
    agent_marker = find_line(med, "AGENTE ADMINISTRATIVO")
    upper_marker = find_line(med, "ENSINO SUPERIOR COMPLETO")
    if agent_marker is not None and upper_marker is not None:
        abody = clean("\n".join((x[1] for x in med[agent_marker + 1 : upper_marker])))
        emit_plain_section(
            rows,
            d,
            cache,
            "Conhecimentos Específicos",
            abody,
            [x[0] for x in med[agent_marker:upper_marker]],
            ["Ensino Médio completo", "Agente Administrativo", "Conhecimentos Específicos"],
            scopes,
            [],
            "especifico",
        )
    upper_scopes = ["Assistente Social", "Contador", "Economista"]
    upstart = find_line(upper, "\\s*[•\\-]?\\s*PARA OS CARGOS DE ASSISTENTE SOCIAL, CONTADOR E ECONOMISTA")
    specstart = find_line(upper, "CONHECIMENTOS ESPECÍFICOS\\s*$", (upstart or 0) + 1)
    if upstart is None:
        upstart = 0
    if specstart is None:
        specstart = len(upper)
    uheads = [
        ("Língua Portuguesa", "Língua\\s+Portuguesa:"),
        ("Matemática / Raciocínio Lógico", "Matemática\\s*/\\s*Raciocínio\\s+Lógico:"),
        ("Matemática / Raciocínio Lógico", "Matemática\\s*$"),
        ("Noções de Informática", "Noções\\s+de\\s+Informática:"),
        ("Legislação", "Legislação:"),
    ]
    for title, body, pages in split_by_headings(upper, uheads, upstart, specstart):
        emit_plain_section(
            rows,
            d,
            cache,
            title,
            body,
            pages,
            ["Ensino Superior completo", "Conhecimentos Gerais", title],
            upper_scopes,
            [],
            "comum",
        )
    role_defs = [
        ("Assistente Social", "ASSISTENTE SOCIAL", "CONTADOR"),
        ("Contador", "CONTADOR", "ECONOMISTA"),
        ("Economista", "ECONOMISTA", "PARA O CARGO DE PROCURADOR"),
    ]
    for role, startpat, endpat in role_defs:
        a = find_line(upper, startpat, specstart)
        b = find_line(upper, endpat, (a or specstart) + 1)
        if a is None:
            continue
        if b is None:
            b = len(upper)
        chunk = upper[a + 1 : b]
        body = clean("\n".join((x[1] for x in chunk if not re.fullmatch("Conhecimentos Específicos:?", x[1], re.I))))
        emit_plain_section(
            rows,
            d,
            cache,
            "Conhecimentos Específicos",
            body,
            [x[0] for x in chunk],
            ["Ensino Superior completo", role, "Conhecimentos Específicos"],
            [role],
            [],
            "especifico",
        )
    pheads = [
        (n, re.escape(n) + "\\s*$")
        for n in [
            "Direito Constitucional",
            "Direito Administrativo",
            "Direito Civil",
            "Direito Processual Civil",
            "Direito Tributário e Financeiro",
            "Direito do Trabalho e Direito Processual do Trabalho",
            "Direito Previdenciário",
        ]
    ]
    pstart = find_line(pro, "CONHECIMENTOS ESPECÍFICOS\\s*$")
    for title, body, pages in split_by_headings(pro, pheads, (pstart or 0) + 1):
        emit_plain_section(
            rows,
            d,
            cache,
            title,
            body,
            pages,
            ["Procurador", "Conhecimentos Específicos", title],
            ["Procurador"],
            [],
            "especifico",
        )


def derive_inline_children(rows):
    """Atomiza parágrafos FCC nos títulos/separadores literais sem apagar o pai."""
    derived = []
    label_rx = re.compile("(?:^|(?<=[.;]))\\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][^:.;]{2,95}?):(?=\\s)")
    for parent in list(rows):
        if parent["documento_id"] != IDS["fcc_open"] or parent["topico_pai_id_local"] is not None:
            continue
        body = parent["texto_original"]
        marks = list(label_rx.finditer(body))
        chunks = []
        if len(marks) >= 2:
            for i, m in enumerate(marks):
                lo = m.start(1)
                hi = marks[i + 1].start(1) if i + 1 < len(marks) else len(body)
                chunk = clean(body[lo:hi])
                if len(chunk) > 12:
                    chunks.append((m.group(1).strip(), chunk))
        elif body.count(";") >= 2:
            for i, part in enumerate(body.split(";"), 1):
                part = clean(part)
                if len(part) > 25:
                    chunks.append((f"trecho {i}", part))
        if len(chunks) < 2:
            continue
        for order, (label, chunk) in enumerate(chunks, 1):
            ident = f"{parent['topico_id_local']}:d{order:03d}"
            derived.append(
                {
                    **parent,
                    "topico_id_local": ident,
                    "topico_pai_id_local": parent["topico_id_local"],
                    "numero_original": None,
                    "ordem_original": order,
                    "texto_original": chunk,
                    "caminho_original": parent["caminho_original"]
                    + ([label] if not label.startswith("trecho ") else []),
                    "unidade_indexacao_derivada": True,
                    "metodo_extracao": parent["metodo_extracao"]
                    + "; filhos derivados apenas em rótulos/separadores explícitos, texto do contêiner pai preservado",
                }
            )
        parent["unidade_indexacao_derivada"] = False
    rows.extend(derived)


def main():
    manifest = load_documents()
    wanted = [d for d in manifest if d["documento_id"] in IDS.values()]
    docs = {d["documento_id"]: d for d in wanted}
    caches = {k: load_doc(k) for k in IDS.values()}
    rows = []
    extract_fcc(rows, docs, caches[IDS["fcc_open"]])
    extract_camprev(rows, docs, caches[IDS["camprev"]])
    extract_aftm(rows, docs, caches[IDS["aftm"]])
    derive_inline_children(rows)
    reports = []
    for did in IDS.values():
        if did == IDS["fcc_ret"]:
            continue
        d = docs[did]
        cache = caches[did]
        rr = [x for x in rows if x["documento_id"] == did]
        coverage = {
            IDS["fcc_open"]: list(range(31, 37)),
            IDS["camprev"]: list(range(30, 35)),
            IDS["aftm"]: list(range(35, 53)),
        }[did]
        reports.append(
            {
                "documento_id": did,
                "banca": d["banca"],
                "concurso": d["concurso"],
                "arquivo": d["arquivo_relativo"],
                "paginas_manifesto": d["paginas"],
                "paginas_lidas": len(cache["paginas"]),
                "paginas_conteudo_programatico": coverage,
                "topicos_extraidos": len(rr),
                "topicos_por_cargo": {
                    c: sum((c in x["escopo_cargos"] for x in rr))
                    for c in sorted({c for x in rr for c in x["escopo_cargos"]})
                },
                "especialidades": sorted({s for x in rr for s in x["escopo_especialidades"]}),
                "pendencias": sum((x["status_extracao"] != "extraido" for x in rr)),
                "amostras_visuais_revisadas": [],
                "observacoes": [],
            }
        )
    reports.append(
        {
            "documento_id": IDS["fcc_ret"],
            "banca": "FCC",
            "concurso": "2026-SEFAZ-SP-APOFP",
            "arquivo": docs[IDS["fcc_ret"]]["arquivo_relativo"],
            "paginas_manifesto": 2,
            "paginas_lidas": 2,
            "paginas_conteudo_programatico": [],
            "topicos_extraidos": 0,
            "topicos_por_cargo": {},
            "especialidades": [],
            "pendencias": 0,
            "amostras_visuais_revisadas": [],
            "observacoes": [
                "Retificação 02/2026 altera prazos de recurso e cronograma; não retifica o conteúdo programático. Não gera tópicos duplicados; tipo_publicacao do documento identificado como retificacao."
            ],
        }
    )
    (config().run_dir / "lotes" / "fcc_vunesp.topicos.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (config().run_dir / "lotes" / "fcc_vunesp.topicos.jsonl").write_text(
        "".join((json.dumps(x, ensure_ascii=False) + "\n" for x in rows)), encoding="utf-8"
    )
    report = {
        "grupo": "fcc_vunesp_editais",
        "agente": AGENT,
        "metodo": "cache de linhas e bbox pdfplumber; escopos, cabeçalhos e blocos semânticos lidos no contexto dos editais; itens numerados separados quando explícitos; texto integral de cada bloco mantido; nenhum cronograma, requisito ou atribuição tratado como conteúdo programático",
        "total_documentos": 4,
        "total_topicos": len(rows),
        "documentos": reports,
    }
    (config().run_dir / "lotes" / "fcc_vunesp.editais.relatorio.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "documentos": 4,
                "topicos": len(rows),
                "saida": str(config().run_dir / "lotes" / "fcc_vunesp.topicos.jsonl"),
                "relatorio": str(config().run_dir / "lotes" / "fcc_vunesp.editais.relatorio.json"),
            },
            ensure_ascii=False,
        )
    )
