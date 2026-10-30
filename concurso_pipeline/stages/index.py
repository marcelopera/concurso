import json
import os
from pathlib import Path
from urllib.parse import quote

from ..common import readjl
from ..config import config


def relative(p):
    return quote(os.path.relpath(config().library / p, config().output_dir).replace("\\", "/"), safe="/")


def main():
    docs = {
        d["documento_id"]: d for d in json.loads((config().canonical / "documentos.json").read_text(encoding="utf-8"))
    }
    report = json.loads((config().output_dir / "relatorio.json").read_text(encoding="utf-8"))
    rows = []
    for q in readjl(config().output_dir / "questoes.jsonl"):
        d = docs[q["documento_id"]]
        pages = q.get("paginas_pdf") or [1]
        images = {
            int(p.stem.split("-")[-1]): p
            for p in (config().output_dir / "fontes-visuais" / d["documento_id"]).glob("pagina-*.png")
        }
        rows.append(
            {
                "tipo": "Questão",
                "id": q["ocorrencia_id"],
                "banca": d["banca"],
                "concurso": d["concurso"],
                "titulo": d["titulo"],
                "numero": q["numero_original"],
                "disciplina": q.get("disciplina_original") or "",
                "texto": q["enunciado_original"],
                "contextos": [x.get("texto", "") for x in q.get("contextos", [])],
                "alternativas": q.get("alternativas", []),
                "habilidades": [x.get("descricao_operacional", "") for x in q.get("habilidades", [])],
                "assuntos": [x.get("assunto", "") for x in q.get("classificacoes", [])],
                "formato": q.get("formato"),
                "status": q["status_extracao"],
                "alertas": q.get("alertas", []),
                "gabaritos": [
                    dict(g, pdf=relative(docs[g["documento_id"]]["arquivo"]) + "#page=" + str(g["paginas_pdf"][0]))
                    for g in q.get("gabaritos", [])
                ],
                "gabarito_divergente": q.get("gabarito_divergente", False),
                "pdf": relative(d["arquivo"]) + "#page=" + str(pages[0]),
                "paginas": pages,
                "imagens": [relative(images[p]) for p in pages if p in images],
            }
        )
    for t in readjl(config().output_dir / "topicos.jsonl"):
        d = docs[t["documento_id"]]
        pages = t.get("paginas_pdf") or [1]
        rows.append(
            {
                "tipo": "Tópico",
                "id": t["topico_id"],
                "banca": d["banca"],
                "concurso": d["concurso"],
                "titulo": d["titulo"],
                "numero": t.get("numero_original") or "",
                "disciplina": t.get("disciplina_original") or "",
                "texto": t["texto_original"],
                "caminho": t.get("caminho_original", []),
                "escopo": t.get("escopo_cargos", []),
                "especialidades": t.get("escopo_especialidades", []),
                "status": t.get("status_extracao"),
                "alertas": t.get("alertas", []),
                "pdf": relative(d["arquivo"]) + "#page=" + str(pages[0]),
                "paginas": pages,
                "derivado": t.get("unidade_indexacao_derivada", False),
            }
        )
    data = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    page = (Path(__file__).resolve().parents[1] / "templates/index.html").read_text(encoding="utf-8")
    page = page.replace("DATA_PLACEHOLDER", data).replace(
        "REPORT_PLACEHOLDER", json.dumps(report, ensure_ascii=False).replace("<", "\\u003c")
    )
    (config().output_dir / "index.html").write_text(page, encoding="utf-8")
    print(json.dumps({"questoes_e_topicos": len(rows), "indice": str(config().output_dir / "index.html")}))
