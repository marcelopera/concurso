"""Repara fronteiras de itens C/E usando recuo físico e linhas integrais do PDF."""

import json
import re
from collections import defaultdict


def reconstruct(run, questions, changed):
    groups = defaultdict(list)
    for q in questions:
        if q["formato"] == "certo_errado":
            groups[q["documento_id"]].append(q)
    for did, items in groups.items():
        cache = json.loads((run / "paginas" / (did + ".json")).read_text(encoding="utf-8"))
        stream = []
        for page in cache["paginas"]:
            lines = [
                line
                for line in page["linhas"]
                if line["bbox"][1] > 42 and line["texto"].strip() and (line["texto"].strip() != "Espaço livre")
            ]
            wide = any(
                (
                    re.match("^\\d{2,3}\\s+", line["texto"])
                    and line["bbox"][0] < 100
                    and (line["bbox"][2] > page["largura"] * 0.8)
                    for line in lines
                )
            )
            columns = (
                [lines]
                if wide
                else [
                    [line for line in lines if (line["bbox"][0] + line["bbox"][2]) / 2 < page["largura"] * 0.5],
                    [line for line in lines if (line["bbox"][0] + line["bbox"][2]) / 2 >= page["largura"] * 0.5],
                ]
            )
            for col in columns:
                groups = []
                for line in sorted(col, key=lambda line: (round(line["bbox"][1], 1), line["bbox"][0])):
                    if groups and abs(line["bbox"][1] - groups[-1][0]["bbox"][1]) < 1.6:
                        groups[-1].append(line)
                    else:
                        groups.append([line])
                merged = []
                for group in groups:
                    group.sort(key=lambda line: line["bbox"][0])
                    merged.append(
                        {
                            "texto": " ".join((line["texto"] for line in group)),
                            "bbox": [
                                min((line["bbox"][0] for line in group)),
                                min((line["bbox"][1] for line in group)),
                                max((line["bbox"][2] for line in group)),
                                max((line["bbox"][3] for line in group)),
                            ],
                            "pagina": page["numero"],
                        }
                    )
                stream.extend(merged)
        bynum = {int(q["numero_original"]): q for q in items}
        seen = set()
        segments = {}
        current = None
        context = []
        shared = []
        body = []
        base = 28.3

        def finish():
            if current is not None:
                segments[current] = (list(body), list(shared))

        for line in stream:
            text = line["texto"].strip()
            m = re.match("^(\\d{1,3})\\s+(\\S.*)$", text)
            num = int(m.group(1)) if m else None
            expected = min(set(bynum) - seen) if set(bynum) - seen else None
            if m and num == expected and (abs(line["bbox"][0] - (28.3 if line["bbox"][0] < 290 else 303.36)) < 4):
                finish()
                current = num
                seen.add(num)
                base = line["bbox"][0]
                if context:
                    shared = context
                    context = []
                body = [dict(line, texto=m.group(2))]
            elif current is not None and (not context) and (abs(line["bbox"][0] - (base + 17.88)) < 4):
                body.append(line)
            else:
                isheading = (
                    text == text.upper()
                    and len(text) > 5
                    and (not re.search("[\\d=+*]", text))
                    and bool(re.search("[A-ZÁÉÍÓÚ]{4}", text))
                )
                if isheading:
                    finish()
                    current = None
                    context = []
                    shared = []
                else:
                    context.append(line)
        finish()
        assert seen == set(bynum), (did, sorted(set(bynum) - seen))
        for num, (body, ctx) in segments.items():
            q = bynum[num]
            changed(
                q, "Itens C/E separados dos comandos seguintes pelo recuo impresso; textos-base completos recuperados"
            )
            text = "\n".join((line["texto"] for line in body)).strip()
            q["enunciado_original"] = text
            q["texto_original_completo"] = text
            q["regioes_fonte"] = [{"pagina": line["pagina"], "bbox": line["bbox"]} for line in body]
            q["paginas_pdf"] = sorted({line["pagina"] for line in body} | {line["pagina"] for line in ctx})
            q["contextos"] = (
                [
                    {
                        "texto": "\n".join((line["texto"] for line in ctx)),
                        "paginas_pdf": sorted({line["pagina"] for line in ctx}),
                        "regioes_fonte": [{"pagina": line["pagina"], "bbox": line["bbox"]} for line in ctx],
                    }
                ]
                if ctx
                else []
            )
            if len(text) < 25:
                q["status_extracao"] = "precisa_revisao"
                q.setdefault("alertas", []).append("Conferir fronteira curta após reconstrução por recuo")
