"""Create a synthetic, redistributable catalog for a fresh installation."""

import hashlib
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def criar(destino: Path) -> None:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(destino, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise FileExistsError(f"O catálogo já existe: {destino}") from None
    os.close(fd)
    try:
        with closing(sqlite3.connect(destino)) as con, con:
            con.executescript((Path(__file__).parent / "esquema.sql").read_text(encoding="utf-8"))
            con.execute(
                "CREATE TABLE schema_meta (versao INTEGER NOT NULL, origem TEXT NOT NULL, "
                "gerado_em TEXT NOT NULL, commit_origem TEXT, hash_fontes TEXT NOT NULL)"
            )
            source_hash = hashlib.sha256(
                Path(__file__).read_bytes() + (Path(__file__).parent / "esquema.sql").read_bytes()
            ).hexdigest()
            con.execute(
                "INSERT INTO schema_meta VALUES (1, 'demonstracao sintetica', ?, NULL, ?)",
                (datetime.now(timezone.utc).isoformat(), source_hash),
            )
            con.execute("PRAGMA user_version=1")
            for n in range(1, 21):
                doc, prova, questao, ocorrencia, gab = (f"{p}{n}" for p in ("doc", "p", "q", "o", "g"))
                banco = "Banca Exemplo A" if n <= 10 else "Banca Exemplo B"
                texto = f"Questão de demonstração {n}: quanto é {n} + 1?"
                con.execute(
                    "INSERT INTO documentos(documento_id,sha256,tipo,banca,concurso,titulo,nome,arquivo_local) VALUES(?,?,?,?,?,?,?,?)",
                    (doc, f"demo-{n}", "provas", banco, "Demonstração", "Prova fictícia", "demo.pdf", "demo.pdf"),
                )
                con.execute(
                    "INSERT INTO provas(prova_id,documento_id,banca,concurso,titulo) VALUES(?,?,?,?,?)",
                    (prova, doc, banco, "Demonstração", "Prova fictícia"),
                )
                con.execute(
                    "INSERT INTO questoes(questao_id,formato,enunciado_original,texto_para_busca,hash_texto,registro_json) VALUES(?,?,?,?,?,?)",
                    (questao, "multipla_escolha", texto, texto, f"demo-hash-{n}", "{}"),
                )
                con.execute(
                    "INSERT INTO ocorrencias(ocorrencia_id,questao_id,prova_id,documento_id,numero_original,disciplina_original,paginas_json,status_extracao) VALUES(?,?,?,?,?,?,?,?)",
                    (ocorrencia, questao, prova, doc, str(n), "Matemática", "[]", "extraido"),
                )
                for ordem, (rotulo, resposta) in enumerate((("A", n + 1), ("B", n + 2))):
                    con.execute(
                        "INSERT INTO alternativas VALUES(?,?,?,?,?)",
                        (f"{questao}-{rotulo}", questao, rotulo, ordem, str(resposta)),
                    )
                con.execute(
                    "INSERT INTO gabaritos(gabarito_registro_id,documento_id,concurso,numero_original,resposta_publicada,situacao_item,natureza_gabarito) VALUES(?,?,?,?,?,?,?)",
                    (gab, doc, "Demonstração", str(n), "A", "valido", "definitivo"),
                )
                con.execute("INSERT INTO ocorrencia_gabarito VALUES(?,?,?,?)", (ocorrencia, gab, "associado", "demo"))
            if con.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Catálogo de demonstração inválido")
    except Exception:
        destino.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destino", type=Path)
    criar(parser.parse_args().destino)
