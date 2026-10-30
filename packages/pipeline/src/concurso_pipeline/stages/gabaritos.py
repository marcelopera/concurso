import json
import re

from ..common import unaccent
from ..config import config


def scope(page, y, x):
    heads = []
    for line in page["linhas"]:
        t = line["texto"].strip()
        if re.search(
            "(?i)analista|auditor|contador|tecnico|cargo|tipo\\s*\\d|vers[aã]o\\s*\\d|gabarito\\s*\\d|prova\\s*[123]|conhec.*(?:gerais|espec|basicos)|[áa]rea\\s*:",
            t,
        ) and (not re.search("^\\d+\\s*[-–]", t)):
            heads.append(line)
    above = [line for line in heads if line["bbox"][1] < y]
    grouped = {}
    for line in above:
        key = round(line["bbox"][1] / 2)
        center = (line["bbox"][0] + line["bbox"][2]) / 2
        if key not in grouped or abs(center - x) < abs((grouped[key]["bbox"][0] + grouped[key]["bbox"][2]) / 2 - x):
            grouped[key] = line
    above = sorted(grouped.values(), key=lambda line: line["bbox"][1])
    if above:
        return " | ".join((line["texto"] for line in above[-4:]))
    return " | ".join((line["texto"] for line in sorted(heads, key=lambda line: line["bbox"][1])[:5]))


def extract(d):
    cached = json.loads((config().run_dir / "paginas" / (d["documento_id"] + ".json")).read_text(encoding="utf-8"))
    all_text = unaccent("\n".join((line["texto"] for p in cached["paginas"] for line in p["linhas"])))
    out = []
    page_reports = []
    for page in cached["paginas"]:
        if d["concurso"] == "2018-SPGG-RS-APOG" and page["numero"] > 1:
            continue
        records = []
        text = "\n".join((line["texto"] for line in page["linhas"]))
        nt = unaccent(text)
        nature = (
            "definitivo"
            if re.search("DEFINITIV|APOS RECURSOS|DEPOIS DOS RECURSOS", all_text)
            else "preliminar"
            if "PRELIMINAR" in all_text or "ANTES DOS RECURSOS" in all_text or "PRELIMINAR" in unaccent(d["nome"])
            else "nao_identificado"
        )
        for line in page["linhas"]:
            for match in re.finditer("(?<!\\d)(\\d{1,3})\\s*[-–]\\s*(NULA|[A-Ea-eXxNn*])(?![A-Za-z])", line["texto"]):
                num, answer = match.groups()
                if int(num) > 0:
                    records.append((num, answer.upper(), line["bbox"], "pares_impressos"))
        words = [w for line in page["linhas"] for w in line["palavras"]]
        numbers = [w for w in words if re.fullmatch("\\d{1,3}", w["texto"]) and 1 <= int(w["texto"]) <= 200]
        answers = [w for w in words if re.fullmatch("[A-EXN*]|NULA|ANULADA|ANULADO", w["texto"], re.I)]
        for n in numbers:
            if len(records) > 5 and records[0][3] == "pares_impressos":
                break
            x0, y0, x1, y1 = n["bbox"]
            center = (x0 + x1) / 2
            row = [v for v in numbers if abs(v["bbox"][1] - y0) < 2]
            choices = []
            for a in answers:
                ax0, ay0, ax1, ay1 = a["bbox"]
                dx = abs((ax0 + ax1) / 2 - center)
                dy = ay0 - y0
                if len(row) >= 2 and 4 < dy < 30 and (dx < 9):
                    choices.append((dy + dx * 0.25, a))
            if choices:
                a = min(choices, key=lambda z: z[0])[1]
                ab = a["bbox"]
                records.append(
                    (
                        n["texto"],
                        a["texto"].upper(),
                        [min(x0, ab[0]), y0, max(x1, ab[2]), ab[3]],
                        "tabela_alinhada_por_coordenadas",
                    )
                )
            horizontal = []
            for a in answers:
                ax0, ay0, ax1, ay1 = a["bbox"]
                if abs(ay0 - y0) < 3 and 3 < ax0 - x1 < 75:
                    between = [v for v in row if x1 < v["bbox"][0] < ax0]
                    if not between:
                        horizontal.append((ax0 - x1, a))
            if horizontal:
                a = min(horizontal, key=lambda z: z[0])[1]
                ab = a["bbox"]
                records.append(
                    (
                        n["texto"],
                        a["texto"].upper(),
                        [x0, min(y0, ab[1]), ab[2], max(y1, ab[3])],
                        "tabela_vertical_por_coordenadas",
                    )
                )
        seen = set()
        for num, answer, bbox, method in sorted(records, key=lambda z: (z[2][1], z[2][0])):
            key = (num, answer, round(bbox[0] / 5), round(bbox[1] / 5))
            if key in seen:
                continue
            seen.add(key)
            s = scope(page, bbox[1], (bbox[0] + bbox[2]) / 2)
            versions = re.findall("(?:TIPO|VERSAO|GABARITO)\\s*[:\\-]?\\s*(\\d+)", unaccent(s))
            annulled = answer in ["X", "*", "N", "NULA", "ANULADA", "ANULADO"]
            alerts = []
            if annulled and answer == "N" and ("NULA" not in nt) and ("ANULAD" not in nt):
                alerts.append("MARCADOR_N_SEM_LEGENDA_LOCAL")
            out.append(
                {
                    "documento_id": d["documento_id"],
                    "concurso": d["concurso"],
                    "cargo_original": s,
                    "especialidade_original": None,
                    "prova_original": s,
                    "codigo_caderno": None,
                    "versao_caderno": versions[-1] if versions else None,
                    "numero_original": num,
                    "resposta_publicada": answer,
                    "situacao_item": "anulado" if annulled else "valido",
                    "natureza_gabarito": nature,
                    "paginas_pdf": [page["numero"]],
                    "regioes_fonte": [{"pagina": page["numero"], "bbox": bbox}],
                    "texto_evidencia": f"{s}\n{num} - {answer}",
                    "status_extracao": "precisa_revisao" if alerts else "extraido",
                    "alertas": alerts,
                    "metodo_extracao": method,
                    "agente": "coordenador_extracao_deterministica",
                }
            )
        page_reports.append(
            {
                "pagina": page["numero"],
                "respostas": len(seen),
                "cabecalhos": [
                    line["texto"]
                    for line in page["linhas"]
                    if re.search(
                        "(?i)analista|auditor|contador|cargo|prova [123]|tipo\\s*\\d|vers[aã]o\\s*\\d", line["texto"]
                    )
                    and len(line["texto"]) < 240
                ],
            }
        )
    if d["documento_id"] == "doc_56f79f813ad7f390c178":
        for r in out:
            if r["paginas_pdf"] == [2] and r["regioes_fonte"][0]["bbox"][1] < 190 and (r["numero_original"] == "7"):
                r.update(
                    resposta_publicada="B",
                    situacao_item="valido",
                    metodo_extracao="correcao_visual_de_resposta_substituida",
                    texto_evidencia="Área Contábil, questão 7: E riscado e B em vermelho; resposta publicada corrigida B.",
                )
    if d["documento_id"] == "doc_db7d0f53eeaaf5f32093":
        columns = [
            "DEBAACE CAD".replace(" ", ""),
            "CBADCACAEC",
            "DDEABCEBDD",
            "BADBDCEDEE",
            "DBDADDBCEB",
            "DDBBDDAC EA".replace(" ", ""),
            "DBACC EBCDB".replace(" ", ""),
            "BCCC DDADDA".replace(" ", ""),
            "BAEDBACECE",
            "BABECDBEAD",
        ]
        assert all((len(c) == 10 for c in columns))
        out = []
        for ci, col in enumerate(columns):
            for ri, a in enumerate(col):
                num = str(ci * 10 + ri + 1)
                out.append(
                    {
                        "documento_id": d["documento_id"],
                        "concurso": d["concurso"],
                        "cargo_original": "AN LEG - ESP CON LEG - ÁREA ORÇ PÚB E DES.ECONÔMICO",
                        "especialidade_original": "Orçamento Público e Desenvolvimento Econômico",
                        "prova_original": "CONHECIMENTOS GERAIS/CONHECIMENTOS ESPECÍFICOS; Cargo G07; Tipo gabarito 1",
                        "codigo_caderno": "G07",
                        "versao_caderno": "1",
                        "numero_original": num,
                        "resposta_publicada": a,
                        "situacao_item": "valido",
                        "natureza_gabarito": "nao_identificado",
                        "paginas_pdf": [1],
                        "regioes_fonte": [
                            {"pagina": 1, "bbox": [39 + ci * 51, 303 + ri * 11.5, 90 + ci * 51, 315 + ri * 11.5]}
                        ],
                        "texto_evidencia": f"{num.zfill(3)} - {a}",
                        "status_extracao": "extraido",
                        "alertas": ["CODIFICACAO_FONTE_CORROMPIDA_TRANSCRICAO_VISUAL"],
                        "metodo_extracao": "transcricao_visual_coordenador",
                        "agente": "coordenador",
                    }
                )
    return (
        out,
        {"documento_id": d["documento_id"], "concurso": d["concurso"], "registros": len(out), "paginas": page_reports},
    )


def main():
    docs = json.loads((config().run_dir / "documentos.json").read_text(encoding="utf-8"))
    all_rows = []
    reports = []
    for d in docs:
        if d["tipo"] == "gabaritos":
            rows, report = extract(d)
            all_rows.extend(rows)
            reports.append(report)
    (config().run_dir / "lotes/gabaritos.jsonl").write_text(
        "".join((json.dumps(x, ensure_ascii=False) + "\n" for x in all_rows)), encoding="utf-8"
    )
    (config().run_dir / "lotes/gabaritos.relatorio.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "registros": len(all_rows),
                "documentos": len(reports),
                "por_documento": [(r["concurso"], r["registros"]) for r in reports],
            }
        )
    )
