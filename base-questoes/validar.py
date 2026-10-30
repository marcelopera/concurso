"""Verificações estruturais e de acesso; não substituem revisão integral de conteúdo."""
import collections,json,re,sqlite3
from pathlib import Path
from urllib.parse import unquote

BASE=Path(__file__).resolve().parent
OUT=BASE/'dados'
RUN=BASE/'execucoes/2026-10-29'
def read(p):return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
def norm(s):return re.sub(r'\s+',' ',s).lower().strip()
def main():
    qs=read(OUT/'questoes.jsonl');ts=read(OUT/'topicos.jsonl');isoladas=read(OUT/'quarentena_questoes.jsonl')
    assert not ({q['ocorrencia_id'] for q in qs} & {q['ocorrencia_id'] for q in isoladas})
    docs={d['documento_id']:d for d in json.loads((RUN/'documentos.json').read_text(encoding='utf-8'))}
    assert len({(q['documento_id'],q['numero_original']) for q in qs})==len(qs)
    for q in qs:
        assert q['enunciado_original'].strip() and q['paginas_pdf']
        if q['formato']=='multipla_escolha':
            assert len(q['alternativas']) in [4,5]
            assert [a['rotulo'].upper() for a in q['alternativas']]==list('ABCDE')[:len(q['alternativas'])]
            assert all(a.get('texto','').strip() for a in q['alternativas'])
            from consolidar import motivos_quarentena
            assert not motivos_quarentena(q), (q['documento_id'],q['numero_original'])
    for r in qs+ts:
        d=docs[r['documento_id']]
        assert all(1<=n<=d['paginas'] for n in r['paginas_pdf'])
        assert Path(d['arquivo']).is_file()
        assert all(1<=b['pagina']<=d['paginas'] for b in r.get('regioes_fonte',[]))
    db=sqlite3.connect(OUT/'conteudo.sqlite')
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    for table in ['questoes','topicos']:
        assert db.execute(f'select count(*) from {table}_fts').fetchone()[0]==db.execute(f'select count(*) from {table}').fetchone()[0]
        assert db.execute(f'select count(*) from {table}_fts where {table}_fts match ?',('"restos a pagar"',)).fetchone()[0]>0
    assert db.execute('select count(*) from questoes_fts where questoes_fts match ?', ('"parcimonia"',)).fetchone()[0]>0
    html=(OUT/'index.html').read_text(encoding='utf-8')
    data=json.loads(re.search(r'<script type="application/json" id="dados">(.*?)</script>',html,re.S)[1])
    (RUN/'indice.verificacao.js').write_text(re.findall(r'<script>(.*?)</script>',html,re.S)[-1],encoding='utf-8')
    links={link for r in data for link in [r['pdf'],*r.get('imagens',[]),*(g['pdf'] for g in r.get('gabaritos',[]))]}
    broken=[s for s in links if not (OUT/unquote(s.split('#')[0])).is_file()]
    assert not broken,broken
    missing=[]
    for q in qs:
        text=norm('\n'.join([q['enunciado_original'],*[a['texto'] for a in q['alternativas']],*[c['texto'] for c in q['contextos']]]))
        for h in q.get('habilidades',[]):
            if h.get('trecho_evidencia') and norm(h['trecho_evidencia']) not in text:
                missing.append({'documento_id':q['documento_id'],'numero':q['numero_original'],'evidencia':h['trecho_evidencia'],'origem':h.get('origem')})
    report={'integridade':'ok','questoes':len(qs),'questoes_em_quarentena':len(isoladas),'topicos':len(ts),'alternativas':'4 ou 5, rótulos únicos sequenciais','paginas_e_documentos':'válidos','links_locais_verificados':len(links),'links_quebrados':broken,'paginas_originais_renderizadas':db.execute('select count(*) from fontes_visuais').fetchone()[0],'gabaritos_divergentes':sum(q.get('gabarito_divergente',False) for q in qs),'evidencias_habilidades_nao_literais':missing,'habilidades_por_origem':dict(collections.Counter(h.get('origem') for q in qs for h in q.get('habilidades',[]))),'nota':__doc__}
    (OUT/'validacao.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='evidencias_habilidades_nao_literais'},ensure_ascii=True));print('Evidências não literais:',len(missing))
    db.close()
if __name__=='__main__':main()
