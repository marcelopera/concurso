"""Consulta local somente de leitura; termos usam a sintaxe MATCH do SQLite FTS5."""
import argparse,json,sqlite3,sys
from pathlib import Path

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('busca',help='Expressão FTS5, por exemplo: "restos a pagar"')
    parser.add_argument('--tipo',choices=['questoes','topicos'],default='questoes')
    parser.add_argument('--banca')
    parser.add_argument('--disciplina')
    parser.add_argument('--limite',type=int,default=20)
    args=parser.parse_args()
    uri=(Path(__file__).resolve().parent/'dados/conteudo.sqlite').as_uri()+'?mode=ro'
    db=sqlite3.connect(uri,uri=True);db.row_factory=sqlite3.Row
    if args.tipo=='questoes':
        sql='''SELECT v.*,bm25(questoes_fts) AS relevancia FROM questoes_fts
        JOIN vw_questoes v USING(questao_id) WHERE questoes_fts MATCH ?'''
    else:
        sql='''SELECT t.topico_id,t.numero_original,t.texto_original,t.disciplina_original,
        t.caminho_json,t.escopo_cargos_json,t.paginas_json,d.banca,d.concurso,d.arquivo_local,
        bm25(topicos_fts) AS relevancia FROM topicos_fts JOIN topicos t USING(topico_id)
        JOIN documentos d USING(documento_id) WHERE topicos_fts MATCH ?'''
    values=[args.busca]
    if args.banca:
        sql+=' AND '+('v' if args.tipo=='questoes' else 'd')+'.banca = ?';values.append(args.banca)
    if args.disciplina:
        sql+=' AND '+('v' if args.tipo=='questoes' else 't')+'.disciplina_original LIKE ?';values.append('%'+args.disciplina+'%')
    sql+=' ORDER BY relevancia LIMIT ?';values.append(max(1,min(args.limite,1000)))
    try:
        for r in db.execute(sql,values):print(json.dumps(dict(r),ensure_ascii=False))
    except sqlite3.OperationalError as exc:parser.error(str(exc))
    finally:db.close()

if __name__=='__main__':main()
