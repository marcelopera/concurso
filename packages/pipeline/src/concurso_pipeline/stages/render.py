import concurrent.futures
import json
import subprocess

from ..config import config, source_file


def render(d):
    folder = config().output_dir / "fontes-visuais" / d["documento_id"]
    folder.mkdir(parents=True, exist_ok=True)
    if len(list(folder.glob("pagina-*.png"))) == d["paginas"]:
        return {"documento_id": d["documento_id"], "paginas": d["paginas"], "status": "cache"}
    p = subprocess.run(
        [str("pdftoppm"), "-r", "100", "-png", str(source_file(d)), str(folder / "pagina")], capture_output=True
    )
    return {
        "documento_id": d["documento_id"],
        "paginas": len(list(folder.glob("pagina-*.png"))),
        "status": "ok" if p.returncode == 0 else "erro",
        "erro": p.stderr.decode("utf-8", errors="replace")[:500] if p.returncode else None,
    }


def main():
    config_value = config()
    docs = [
        d
        for d in json.loads((config().run_dir / "documentos.json").read_text(encoding="utf-8"))
        if d["tipo"] == "provas"
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda d: render_at(config_value, d), docs))
    (config().run_dir / "fontes-visuais.relatorio.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "documentos": len(rows),
                "paginas": sum((x["paginas"] for x in rows)),
                "falhas": [x for x in rows if x["status"] == "erro"],
            }
        )
    )


def render_at(settings, document):
    from ..config import execution

    with execution(settings):
        return render(document)
