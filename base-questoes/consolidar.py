from __future__ import annotations

import csv
from contextlib import closing
import hashlib
import html
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parent
RUN=BASE/'execucoes/2026-10-29'
OUT=BASE/'dados'
OUT.mkdir(exist_ok=True)

def js(v):return json.dumps(v,ensure_ascii=False,sort_keys=True)
def norm(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',str(s or ''))).strip()
def unaccent(s):return ''.join(c for c in unicodedata.normalize('NFD',norm(s)) if not unicodedata.combining(c)).upper()
def ident(prefix,*parts):return prefix+'_'+hashlib.sha256('\x1f'.join(norm(x) for x in parts).encode()).hexdigest()[:24]
def readjl(path):
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip():yield json.loads(line)
def writejl(path,rows):path.write_text(''.join(js(x)+'\n' for x in rows),encoding='utf-8')


def eligible(g,p,gdoc):
    if g['concurso']!=p['concurso']:return False
    c=p['concurso'];name=p['nome'];page=g['paginas_pdf'][0]
    y=g['regioes_fonte'][0]['bbox'][1];x=g['regioes_fonte'][0]['bbox'][0]
    title=unaccent(g['cargo_original']);last=title.split(' | ')[-1]
    version=g.get('versao_caderno')
    if c=='2024-MPO-APO':return gdoc['nome']==('p1-definitivo' if name.startswith('p1') else 'p2-definitivo')
    if p['banca']=='Cebraspe':return True
    if c=='2023-SMF-RJ-APO':return page==(1 if 'manha' in name else 2) and y<238
    if c=='2024-EPE-GESTAO-CORPORATIVA':return page==(8 if 'contabilidade' in name else 9) and version=='1'
    if c=='2024-STN-FINANCAS-E-CONTROLE':return page==((1 if name.startswith('contabil') else 2)+(0 if 'manha' in name else 5)) and version=='1'
    if c=='2016-IBGE-ANALISTA':return page==(13 if 'contabeis' in name else 28)
    if c=='2023-PBH-CIENCIAS-CONTABEIS':return (page==4 and y>383) or (page==5 and y<405)
    if c=='2023-CAMPREV-CONTADOR':return page==2 and 106<y<304
    if c=='2023-SAO-PAULO-AFTM':
        prefix=name[:2]
        return gdoc['nome'].startswith(prefix+'-') and (gdoc['nome']!='p3-preliminar-vunesp' or page==1)
    if c=='2009-SEFAZ-SP-APOFP':return (page==1 and 265<y<376) if name.startswith('p1') else (page==2 and 123<y<261)
    if c=='2010-SEFAZ-SP-APOFP':return (y<400)==name.startswith('p1')
    if c=='2013-SEFAZ-SP-APOFP':return (page==1 and 301<y<474) if name.startswith('p1') else (page==3 and 168<y<354)
    if c=='2015-MPOG-APO':return page==2 and y<230
    if c=='2013-STN-CONTABIL-FINANCEIRA':return page==2 and y<190
    if c=='2018-SPGG-RS-APOG':return page==1 and y<600
    if c=='2016-TERESINA-ORCAMENTO-FINANCAS':return page==29
    if c=='2014-ALEPE-ORCAMENTO':return True
    if c=='2023-COPERGAS-CONTADOR':return page==1 and 242<y<367
    if c=='2013-TJ-SP-CONTADOR':return True
    return False


# Critérios de exclusão conservadores: registros ficam recuperáveis na quarentena.
FRONTEIRA = re.compile(
    r"leia o texto.{0,60}(?:questões|questão)|"
    r"(?:atenção|instruções):.{0,100}(?:questões|questão)|"
    r"(?:informações|dados|enunciado).{0,100}(?:questões|questão)|"
    r"\bquestão\s+\d+\s+baseia-se|read text.{0,60}questions|"
    r"TODOS OS DIREITOS RESERVADOS|PROVA DISSERTATIVA|TABELAS UTILIZÁVEIS NA SOLUÇÃO",
    re.I)

def motivos_quarentena(q):
    if q.get('formato') != 'multipla_escolha': return []
    alts=q.get('alternativas') or []
    motivos=[]
    if len(alts) not in (4,5) or [str(a.get('rotulo','')).upper() for a in alts] != list('ABCDE')[:len(alts)]:
        motivos.append('alternativas ausentes, duplicadas ou fora de ordem')
    if any(not a.get('texto','').strip() for a in alts):
        motivos.append('alternativa sem texto extraído')
    if alts and FRONTEIRA.search(alts[-1].get('texto','')):
        motivos.append('alternativa contaminada por material externo à questão')
    if (q['documento_id'], str(q['numero_original'])) == ('doc_1efe6714afa2325e6998','60'):
        motivos.append('alternativa contaminada por instruções da prova discursiva')
    return motivos

def disciplina_confiavel(value):
    if not value: return value
    if (re.match(r'^477_',value) or re.match(r'^E(?:\)|\s+[$R])',value)
        or re.match(r'^V\.\s*\{',value) or value in {
            'ESPECÍFICOS --','ESPECIALIZADOS --','-- CONHECIMENTOS',
            'Y* = 1.200','(ESTADUAIS, SETORIAIS E TERRITORIAIS)',
            'DISPONIBILIZADAS NA INTERNET)','E ORÇAMENTO PÚBLICO',
            'ALIANÇAS COM O PÚBLICO E O PRIVADO','E ABC.'}):
        return None
    return value

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    docs=json.loads((RUN/'documentos.json').read_text(encoding='utf-8'));docmap={d['documento_id']:d for d in docs}
    build=OUT/'conteudo.novo.sqlite'
    if build.exists():build.unlink()
    db=sqlite3.connect(build)
    db.executescript((BASE/'esquema.sql').read_text(encoding='utf-8'))
    db.execute('INSERT INTO execucoes VALUES(?,?,?,?)',('2026-10-29','2026-10-29','v1',js({'modelos_agentes':['gpt-6-luna'],'origem':'biblioteca local','escopo':'conteudo; sem dados de alunos'})))
    for d in docs:
        db.execute('INSERT INTO documentos VALUES(?,?,?,?,?,?,?,?,?,?,?)',(d['documento_id'],d['sha256'],d['tipo'],d['banca'],d['concurso'],d['titulo'],d['nome'],d['arquivo'],d['paginas'],d['url'],js(d)))
        if d['tipo']=='provas':db.execute('INSERT INTO provas VALUES(?,?,?,?,?,?,?)',(d['documento_id'],d['documento_id'],d['banca'],d['concurso'],d['titulo'],d['nome'],js(d)))
        if d['tipo']=='provas':
            cache=json.loads((RUN/'paginas'/(d['documento_id']+'.json')).read_text(encoding='utf-8'))
            images={int(p.stem.split('-')[-1]):p for p in (OUT/'fontes-visuais'/d['documento_id']).glob('pagina-*.png')}
            for page in cache['paginas']:
                number=page['numero']
                if number in images:
                    db.execute('INSERT INTO fontes_visuais VALUES(?,?,?,?,?,?)',(ident('vis',d['documento_id'],number),d['documento_id'],number,str(images[number]),page['largura'],page['altura']))
    enriched={}
    corrections={(r['documento_id'],str(r['numero_original'])):r for r in readjl(RUN/'correcoes_questoes.jsonl')}
    for f in sorted((RUN/'lotes').glob('*.enriquecimento.jsonl')):
        for r in readjl(f):enriched[(r['documento_id'],str(r['numero_original']))]=r
    exported=[];quarantine=[];seen_q=set();seen_alt=set();seen_ctx=set();bydoc=Counter();pending=[]
    for f in sorted((RUN/'lotes').glob('*.questoes.jsonl')):
        for order,q in enumerate(readjl(f),1):
            doc=docmap[q['documento_id']]
            q=dict(corrections.get((q['documento_id'],str(q['numero_original'])),q));e=enriched.get((q['documento_id'],str(q['numero_original'])),{})
            if e:
                q['classificacoes']=e.get('classificacoes',q.get('classificacoes',[]))
                q['habilidades']=e.get('habilidades',q.get('habilidades',[]))
            motivos=motivos_quarentena(q)
            if motivos:
                quarantine.append({'documento_id':q['documento_id'],'numero_original':str(q['numero_original']),
                    'ocorrencia_id':ident('o',q['documento_id'],q.get('prova_id') or q['documento_id'],q['numero_original']),
                    'motivos':motivos,'registro':q})
                continue
            # ESAF registra o texto integral no campo de enunciado; separar as
            # opções apenas quando o primeiro marcador corresponde à opção A.
            if doc['banca']=='ESAF' and q.get('alternativas'):
                stem=q.get('enunciado_original','')
                marker=re.search(r'(?m)^\s*a\)\s+',stem,re.I)
                first=norm(q['alternativas'][0].get('texto','')).casefold()
                if marker and first and norm(stem[marker.end():]).casefold().startswith(first[:min(50,len(first))]):
                    q['enunciado_original']=stem[:marker.start()].strip()
                    q.setdefault('correcoes_indexacao',[]).append('Alternativas separadas do enunciado ESAF; transcrição integral preservada')
            disciplina=q.get('disciplina_original')
            if disciplina and not disciplina_confiavel(disciplina):
                q['disciplina_original_rejeitada']=disciplina
                q['disciplina_original']=None
            alts=q.get('alternativas') or []
            contexts=q.get('contextos') or []
            complete=q.get('texto_original_completo') or q.get('enunciado_original') or ''
            full='\n'.join([*(x.get('texto','') for x in contexts),complete])
            # Uma evidência proveniente de fronteira antiga não pode sustentar uma habilidade.
            rejected=[]
            for field in ['habilidades','classificacoes']:
                accepted=[]
                for candidate in q.get(field) or []:
                    evidence=norm(candidate.get('trecho_evidencia','')).casefold()
                    if evidence and evidence in norm(full).casefold():accepted.append(candidate)
                    else:rejected.append({'campo':field,'registro':candidate,'motivo':'Evidencia nao encontrada no conteudo corrigido'})
                q[field]=accepted
            if rejected:q['enriquecimento_rejeitado']=rejected
            qid=ident('q',q.get('formato'),norm(complete),js(alts),js([norm(x.get('texto','')) for x in contexts]))
            regions=q.get('regioes_fonte') or []
            oid=ident('o',q['documento_id'],q.get('prova_id') or q['documento_id'],q['numero_original'])
            q.update(questao_id=qid,ocorrencia_id=oid,banca=doc['banca'],concurso=doc['concurso'],titulo_concurso=doc['titulo'],arquivo_pdf=doc['arquivo'],texto_para_busca=norm(full))
            if not q.get('formato'):
                q['status_extracao']='precisa_revisao';q.setdefault('alertas',[]).append('FORMATO_NAO_IDENTIFICADO')
            if qid not in seen_q:
                db.execute('INSERT INTO questoes VALUES(?,?,?,?,?,?,?)',(qid,q.get('formato'),q.get('enunciado_original') or complete,norm(full),hashlib.sha256(norm(full).encode()).hexdigest(),q['status_extracao'],js(q)))
                seen_q.add(qid)
                for i,a in enumerate(alts,1):
                    aid=ident('alt',qid,i)
                    db.execute('INSERT INTO alternativas VALUES(?,?,?,?,?)',(aid,qid,a.get('rotulo'),i,a.get('texto','')))
                for i,c in enumerate(contexts,1):
                    cid=ident('ctx',norm(c.get('texto','')))
                    if cid not in seen_ctx:
                        db.execute('INSERT INTO contextos VALUES(?,?,?)',(cid,c.get('texto',''),js(c)));seen_ctx.add(cid)
                    db.execute('INSERT OR IGNORE INTO questao_contexto VALUES(?,?,?)',(qid,cid,i))
                for i,c in enumerate(q.get('classificacoes') or []):
                    db.execute('INSERT INTO classificacoes VALUES(?,?,?,?,?,?,?,?,?,?,?)',(ident('cl',qid,i),qid,c.get('disciplina'),c.get('assunto'),c.get('subassunto'),c.get('papel'),c.get('trecho_evidencia'),c.get('origem'),c.get('confianca'),'pendente',js(c)))
                for i,h in enumerate(q.get('habilidades') or []):
                    desc=h.get('descricao_operacional','').strip()
                    if not desc:continue
                    hid=ident('h',unaccent(desc))
                    db.execute('INSERT OR IGNORE INTO habilidades VALUES(?,?,?,?,?,?,?)',(hid,desc,h.get('acao'),h.get('objeto_conhecimento'),h.get('tipo_demanda'),'v1','pendente'))
                    db.execute('INSERT INTO questao_habilidade VALUES(?,?,?,?,?,?,?,?,?)',(ident('qh',qid,i),qid,hid,h.get('papel'),h.get('trecho_evidencia'),h.get('origem'),h.get('confianca'),'pendente',js(h)))
                classes=q.get('classificacoes') or []
                search_labels=' '.join([*(c.get('assunto','') or '' for c in classes),*(h.get('descricao_operacional','') for h in q.get('habilidades') or [])])
                db.execute('INSERT INTO questoes_fts VALUES(?,?,?,?)',(qid,norm(full+' '+' '.join(a.get('texto','') for a in alts)),q.get('disciplina_original') or ' '.join(c.get('disciplina','') or '' for c in classes),search_labels))
            db.execute('INSERT INTO ocorrencias VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(oid,qid,q.get('prova_id') or q['documento_id'],q['documento_id'],str(q['numero_original']),q.get('bloco_original'),q.get('disciplina_original'),js(q.get('paginas_pdf',[])),js(regions),q['status_extracao'],js(q.get('alertas',[])),q.get('metodo_extracao'),q.get('agente'),'2026-10-29'))
            if q['status_extracao']!='extraido':pending.append({'tipo':'questao','entidade_id':oid,'documento_id':q['documento_id'],'descricao':'; '.join(q.get('alertas',[])) or 'Revisao indicada pelo extrator'})
            if not q.get('habilidades'):pending.append({'tipo':'habilidade','entidade_id':qid,'documento_id':q['documento_id'],'descricao':'Habilidade ainda nao classificada individualmente'})
            bydoc[q['documento_id']]+=1
            exported.append(q)
    gabs=[];gindex=defaultdict(list)
    for i,g in enumerate(readjl(RUN/'lotes/gabaritos.jsonl')):
        gid=ident('g',g['documento_id'],g['numero_original'],js(g['regioes_fonte']),g['resposta_publicada'])
        g=dict(g,gabarito_registro_id=gid)
        db.execute('INSERT OR IGNORE INTO gabaritos VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(gid,g['documento_id'],g['concurso'],str(g['numero_original']),g['resposta_publicada'],g['situacao_item'],g['natureza_gabarito'],g.get('versao_caderno'),g['cargo_original'],js(g['paginas_pdf']),js(g['regioes_fonte']),js(g)))
        gindex[g['concurso']].append(g);gabs.append(g)
    linked=0
    for q in exported:
        if q['formato']=='discursiva':continue
        p=docmap[q['documento_id']]
        try:num=int(q['numero_original'])
        except ValueError:continue
        candidates=[g for g in gindex[p['concurso']] if int(g['numero_original'])==num and eligible(g,p,docmap[g['documento_id']])]
        # Uma publicação deve produzir no máximo uma resposta por prova/versão/item.
        perdoc=defaultdict(list)
        for g in candidates:perdoc[g['documento_id']].append(g)
        valid=[]
        for did,records in perdoc.items():
            if len({g['resposta_publicada'] for g in records})==1:
                valid.append(records[0])
            else:pending.append({'tipo':'gabarito','entidade_id':q['ocorrencia_id'],'documento_id':did,'descricao':'Mais de uma resposta candidata no mesmo documento; associacao recusada'})
        for g in valid:
            db.execute('INSERT OR IGNORE INTO ocorrencia_gabarito VALUES(?,?,?,?)',(q['ocorrencia_id'],g['gabarito_registro_id'],'associado_por_escopo','Concurso, caderno, versao, cargo/area, pagina e bloco verificados na regra especifica de consolidacao'))
        q['gabaritos']=[{'gabarito_registro_id':g['gabarito_registro_id'],'resposta':g['resposta_publicada'],'situacao':g['situacao_item'],'natureza':g['natureza_gabarito'],'documento_id':g['documento_id'],'paginas_pdf':g['paginas_pdf']} for g in valid]
        final=[g for g in valid if g['natureza_gabarito']=='definitivo']
        reference=final or valid
        answers={(g['resposta_publicada'],g['situacao_item']) for g in reference}
        q['gabarito_referencia']=reference[0]['resposta_publicada'] if len(answers)==1 else None
        q['gabarito_divergente']=len(answers)>1
        if len(answers)>1:
            pending.append({'tipo':'gabarito_divergente','entidade_id':q['ocorrencia_id'],'documento_id':q['documento_id'],'descricao':'Publicacoes associadas divergem sem precedencia definitiva confirmada; nao usar para corrigir respostas automaticamente'})
        if valid:linked+=1
        else:pending.append({'tipo':'gabarito','entidade_id':q['ocorrencia_id'],'documento_id':q['documento_id'],'descricao':'Sem gabarito associado com escopo inequivoco'})
    topics=[]
    for f in sorted((RUN/'lotes').glob('*.topicos.jsonl')):topics.extend(readjl(f))
    tmap={}
    for i,t in enumerate(topics):tmap[(t['documento_id'],str(t.get('topico_id_local',t.get('topico_id',i))))]=ident('t',t['documento_id'],str(t.get('topico_id_local',t.get('topico_id',i))))
    for i,t in enumerate(topics):
        local=str(t.get('topico_id_local',t.get('topico_id',i)));tid=tmap[(t['documento_id'],local)]
        pid=tmap.get((t['documento_id'],str(t.get('topico_pai_id_local')))) if t.get('topico_pai_id_local') else None
        t['topico_id']=tid;t['topico_pai_id']=pid
        db.execute('INSERT INTO topicos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(tid,t['documento_id'],pid,t.get('numero_original'),t.get('ordem_original',i),t.get('texto_original',''),norm(t.get('texto_original','')),t.get('disciplina_original'),js(t.get('caminho_original',[])),js(t.get('escopo_cargos',[])),js(t.get('escopo_especialidades',[])),t.get('bloco'),t.get('tipo_publicacao'),t.get('estado_na_versao'),js(t.get('paginas_pdf',[])),js(t.get('regioes_fonte',[])),t.get('status_extracao'),js(t.get('alertas',[])),js(t)))
        db.execute('INSERT INTO topicos_fts VALUES(?,?,?)',(tid,norm(t.get('texto_original','')),t.get('disciplina_original') or ''))
        if t.get('status_extracao')!='extraido':pending.append({'tipo':'topico','entidade_id':tid,'documento_id':t['documento_id'],'descricao':'; '.join(t.get('alertas',[])) or 'Revisao indicada pelo extrator'})
    for i,p in enumerate(pending):db.execute('INSERT OR IGNORE INTO pendencias VALUES(?,?,?,?,?,?)',(ident('pen',p['tipo'],p['entidade_id'],p['descricao']),p['tipo'],p['entidade_id'],p['documento_id'],p['descricao'],'aberta'))
    integrity=db.execute('PRAGMA integrity_check').fetchone()[0];fk=db.execute('PRAGMA foreign_key_check').fetchall()
    assert integrity=='ok' and not fk,(integrity,fk)
    db.commit();db.close()
    target=OUT/'conteudo.sqlite'
    try:
        build.replace(target)
    except PermissionError:
        # No Windows, leitores mantêm o arquivo aberto e impedem rename.
        # A API de backup do SQLite atualiza o destino transacionalmente.
        with closing(sqlite3.connect(build)) as source, closing(sqlite3.connect(target, timeout=30)) as destination:
            source.backup(destination)
        build.unlink()
    writejl(OUT/'quarentena_questoes.jsonl',quarantine);writejl(OUT/'questoes.jsonl',exported);writejl(OUT/'topicos.jsonl',topics);writejl(OUT/'gabaritos.jsonl',gabs);writejl(OUT/'pendencias.jsonl',pending)
    queues=OUT/'filas';queues.mkdir(exist_ok=True)
    writejl(queues/'questoes_sem_habilidade.jsonl',[q for q in exported if not q.get('habilidades')])
    writejl(queues/'questoes_revisao.jsonl',[q for q in exported if q['status_extracao']!='extraido'])
    writejl(queues/'gabaritos_divergentes.jsonl',[q for q in exported if q.get('gabarito_divergente')])
    with (OUT/'questoes.csv').open('w',encoding='utf-8-sig',newline='') as f:
        cols=['questao_id','ocorrencia_id','banca','concurso','numero_original','formato','disciplina_original','enunciado_original','status_extracao','paginas_pdf','arquivo_pdf']
        w=csv.DictWriter(f,fieldnames=cols,delimiter=';',extrasaction='ignore');w.writeheader();w.writerows(exported)
    report={'execucao':'2026-10-29','documentos':len(docs),'provas':len(bydoc),'ocorrencias_questoes':len(exported),'questoes_em_quarentena':len(quarantine),'questoes_unicas':len(seen_q),'formatos':dict(Counter(q['formato'] for q in exported)),'status_questoes':dict(Counter(q['status_extracao'] for q in exported)),'gabaritos_extraidos':len(gabs),'ocorrencias_com_gabarito':linked,'topicos':len(topics),'editais_com_topicos':len({t['documento_id'] for t in topics}),'habilidades_vinculadas':sum(bool(q.get('habilidades')) for q in exported),'pendencias_por_tipo':dict(Counter(p['tipo'] for p in pending)),'por_documento':[{'documento_id':d['documento_id'],'titulo':d['titulo'],'nome':d['nome'],'questoes':bydoc[d['documento_id']]} for d in docs if d['tipo']=='provas'],'integridade_sqlite':integrity,'foreign_keys':fk}
    (OUT/'relatorio.json').write_text(js(report),encoding='utf-8')
    print(js({k:v for k,v in report.items() if k!='por_documento'}))


if __name__=='__main__':main()
