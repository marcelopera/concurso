"""Audit every local occurrence and add evidence-backed links to the A01 roadmap.

Default is a dry run. Content SQLite is always read-only. --apply backs up and
adds links to study SQLite; it never replaces manual selections or study history.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from question_mapping_rules import COMPILED, language_question, normalize

ROOT = Path(__file__).resolve().parent
import os
CONTENT = Path(os.environ.get('ESTUDO_CONTENT_DB', ROOT/'dados'/'conteudo.sqlite'))
STUDY = ROOT/'dados'/'estudo.sqlite'
PLAN = ROOT/'roadmaps'/'apofp-2026'/'roadmap.json'
OUTPUT = ROOT/'dados'/'vinculacao'
METHOD = 'regras-tematicas-evidencia-v1'

# Exact occurrence overrides are written only after reading the item. A list of
# lesson keys accepts it; [] records an explicit exclusion. Optional notes explain
# historical or partial correspondence. No answer or grading data is changed.
OVERRIDES = OUTPUT/'revisoes.json'

# Broad foundation rules act only as a fallback, not as incidental second links.
FOUNDATIONS = {'adm_01','da_01','dc_01','eco_03','con_01','con_06','con_07','df_01','afo_01','dad_01'}
SUBJECTS = {'adm','da','dc','eco','por','mat','afo','con','df','dad','a01'}
RELATED = [ {'adm','da','dc'}, {'afo','con','df','a01','dc'}, {'eco','mat','df','a01'}, {'dad','mat'} ]


def init_schema(con):
    con.executescript('''
        CREATE TABLE IF NOT EXISTS question_mapping_runs (
            run_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            report_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS lesson_question_mappings (
            lesson_id TEXT NOT NULL,
            occurrence_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            confidence TEXT NOT NULL,
            method TEXT NOT NULL,
            score REAL NOT NULL,
            evidence_json TEXT NOT NULL,
            syllabus_excerpt TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL REFERENCES question_mapping_runs(run_id),
            PRIMARY KEY(lesson_id, occurrence_id),
            FOREIGN KEY(lesson_id, occurrence_id) REFERENCES lesson_questions(lesson_id, occurrence_id) ON DELETE CASCADE
        );
    ''')


def load_questions():
    with closing(sqlite3.connect(f'file:{CONTENT.as_posix()}?mode=ro',uri=True)) as con:
        con.row_factory=sqlite3.Row
        questions = [dict(r) for r in con.execute('''
            SELECT v.*,q.hash_texto,r.estado AS answer_state,r.situacao_referencia AS answer_situation,
                   r.possui_publicacao_definitiva AS definitive
            FROM vw_questoes v JOIN questoes q USING(questao_id)
            LEFT JOIN vw_gabaritos_referencia r USING(ocorrencia_id)
            ORDER BY v.banca,v.concurso,v.ocorrencia_id''')]
        alternatives=defaultdict(list)
        for r in con.execute('SELECT questao_id,rotulo,texto_original FROM alternativas ORDER BY ordem'):
            alternatives[r['questao_id']].append(dict(r))
        contexts=defaultdict(list)
        for r in con.execute('SELECT qc.questao_id,c.texto_original FROM questao_contexto qc JOIN contextos c USING(contexto_id) ORDER BY qc.ordem'):
            contexts[r['questao_id']].append(r['texto_original'])
        for q in questions:
            q['alternatives']=alternatives[q['questao_id']]
            q['contexts']=contexts[q['questao_id']]
    return questions


def eligible(q):
    return q['status_extracao']=='extraido' and q['answer_state']=='concordante' and q['answer_situation']=='valido' and bool(q['definitive'])


def snippet(text, match):
    return text[max(0,match.start()-65):min(len(text),match.end()+100)]


def classify(q, overrides):
    # Some legacy parsers attached the introduction of the next question to the
    # current item. Exclude those known boundaries from thematic matching only.
    boundary=re.compile(r'as informac(?:oes|ao) que se seguem|a questao \d+ baseia|a questao \d+ refere|as informacoes.{0,35}responder as questoes|no 2o paragrafo, o adjetivo')
    raw_command=re.split(r'(?m)^\s*\(?[aA][).]\s+',q['enunciado_original'],maxsplit=1)[0]
    stem=boundary.split(normalize(raw_command),maxsplit=1)[0]
    alternatives=' '.join(boundary.split(normalize(a['texto_original']),maxsplit=1)[0] for a in q['alternatives'])
    alt=normalize(alternatives)
    disc=normalize(q.get('disciplina_original'))
    lang=language_question(stem,disc) if q['formato']!='discursiva' else None
    if q['ocorrencia_id'] in overrides:
        review=overrides[q['ocorrencia_id']]
        return [dict(key=k,score=100,confidence='revisada',relation=review.get('relation','direta'),
                     evidence=review.get('evidence',[dict(field='enunciado_original',text=q['enunciado_original'][:500])]),
                     method='leitura-individual',note=review.get('note','')) for k in review['lessons']], review.get('reason','revisao_individual')
    if lang=='foreign':
        return [],'lingua_estrangeira_fora_do_edital'
    if len(stem)<9:
        return [],'enunciado_incompleto_requer_conferencia_da_fonte'
    if re.search(r'metodo de custeio|custeio por|custeio direto|custo padrao|conceito de custo (variavel|fixo)|margem de contribuicao|custos indiretos de fabricacao|custos industriais|alavancagem operacional|alavancagem financeira|custos dos produtos fabricados',stem):
        return [],'contabilidade_de_custos_especializada_fora_do_programa_a01'
    candidates=[]
    for key,patterns in COMPILED.items():
        if lang=='portuguese' and not key.startswith('por_'):
            continue
        if lang!='portuguese' and key.startswith('por_'):
            continue
        evidences=[]
        score=0
        stem_count=0
        for pattern in patterns:
            match=pattern.search(stem)
            if match:
                stem_count+=1
                score+=4
                evidences.append(dict(field='enunciado_original',text=snippet(stem,match),matched=match.group(),pattern=pattern.pattern))
            else:
                match=pattern.search(alt)
                if match:
                    score+=1.8
                    evidences.append(dict(field='alternativas',text=snippet(alt,match),matched=match.group(),pattern=pattern.pattern))
        if not evidences:
            continue
        # Terms such as an average interest rate or public property alone do not
        # turn an economics/law question into an exercise in statistics/welfare.
        if key=='mat_04' and not re.search(r'estatistic|amostr|media aritmetica|media geometrica|mediana|\bmoda\b|variancia|desvio|quartil|percentil|assimetria|curtose|covariancia|correlacao|frequencia|histograma|populacao|distribui|observaco|valores|dados|pesquisa|variaveis qualitativas|variaveis quantitativas',stem+' '+alt):
            continue
        if key=='mat_10' and not re.search(r'aprendizado|classificac|modelo|matriz de confusao|curva roc|f1.score|erro quadratico medio|erro absoluto medio|rmse|\bmse\b|\bmae\b',stem):
            continue
        if key in ('a01_05','a01_06') and not re.search(r'fontes? (de recursos|de receita)|destinacao.{0,20}recursos|recursos vinculados|recursos ordinarios|fundos (financeiros|especiais)',stem+' '+alt):
            continue
        if key=='a01_05' and not re.search(r'(fonte|destinacao).{0,35}(recursos|receita|despesa)|recursos.{0,25}(fonte|destinacao)',stem):
            continue
        if key.startswith('dad_') and re.search(r'ato administrativo|licitacao|improbidade|poder da administracao|constituicao federal|codigo tributario',stem) and not re.search(r'lgpd|dados pessoais|marco civil|protecao de dados',stem):
            continue
        if key=='eco_01' and re.search(r'licita|contrato administrativo|bens publicos|improbidade',stem) and not re.search(r'elasticidade|custo marginal|oferta e demanda|concorrencia perfeita',stem):
            continue
        if key=='da_06' and not stem_count and not re.search(r'servico publico|concessao|bens publicos|responsabilidade civil|parceria',stem):
            continue
        if score<3.6:
            continue
        candidates.append(dict(key=key,score=round(score,2),stem_count=stem_count,
                               confidence='alta' if stem_count>=2 else 'moderada',
                               relation='direta' if stem_count else 'correlata',
                               evidence=evidences[:4],method=METHOD,note=''))
    candidates.sort(key=lambda r:(not bool(r['stem_count']),-r['score'],-r['stem_count'],r['key']))
    if lang=='portuguese' and not candidates:
        return [dict(key='por_02',score=4,stem_count=1,confidence='moderada',relation='direta',
                     evidence=[dict(field='enunciado_original',text=stem[:450],matched='comando de leitura textual')],method=METHOD,note='')], 'comando_de_leitura'
    if not candidates:
        return [],'sem_correspondencia_tematica_segura'
    # A single term in a distractor is not sufficient. Prefer the actual command.
    max_score=candidates[0]['score']
    primary=candidates[0]['key'].rsplit('_',1)[0]
    selected=[]
    for c in candidates:
        subject=c['key'].rsplit('_',1)[0]
        if c['score']<max(1.8 if lang=='portuguese' else 4 if c['stem_count'] else 5.4,max_score*.42):
            continue
        if subject!=primary and not any({subject,primary}<=group for group in RELATED):
            continue
        if c['key'] in FOUNDATIONS and selected and c['score']<max_score*.9:
            continue
        if sum(x['key'].rsplit('_',1)[0]==subject for x in selected)>=2:
            continue
        if not c['stem_count'] and selected:
            continue
        if c['key']=='por_02' and any(x['key'].startswith('por_') and x['key']!='por_02' and x['stem_count'] for x in candidates) and not re.search(r'interpretacao|intertextualidade|metafora|metonimia|ironia|ironic|figuras de linguagem|denotacao|conotacao|discurso (direto|indireto)|sentido figurado',stem):
            continue
        selected.append(c)
        if lang=='portuguese' and len(selected)==2:
            break
        if len(selected)==5:
            break
    # Preserve historical terminology explicitly. It is source-exam practice;
    # applicability to today's statutes must be checked before using as doctrine.
    historic = re.search(r'8[. ]?666|10[. ]?520|4[. ]?536|facilitars|54[. ]?019',stem)
    if historic:
        for c in selected:
            c['note']='Questão histórica: há norma ou contexto específico de outra prova. Conferir aplicação ao edital atual; o gabarito se refere à prova de origem.'
            c['relation']='correlata'
    if q['formato']=='discursiva':
        for c in selected:
            c['note']='Proposta discursiva de outra prova: adaptar ao estudo de caso de até 30 linhas do APOFP. Não há correção discursiva automática nem espelho oficial nesta base.'
            c['relation']='correlata'
    for c in selected:
        if c['key'].startswith('con_') and not re.search(r'setor publico|ente publico|entidade publica|municipio|contabilidade publica|mcasp|pcasp|casp|rpg|rcpg|administracao publica',stem):
            c['relation']='correlata'
            c['note']=(c['note']+' ' if c['note'] else '')+'Exercício de contabilidade geral/empresarial para fundamentos; conferir as particularidades da contabilidade pública ao aplicar à aula.'
    return selected,'regra_tematica' if selected else 'evidencia_insuficiente'


def build():
    plan=json.loads(PLAN.read_text(encoding='utf-8'))
    units={u['lesson_id'].removeprefix('apofp26_'):u for s in plan['subjects'] for u in s['lessons']}
    assert set(COMPILED)==set(units)
    overrides=json.loads(OVERRIDES.read_text(encoding='utf-8')) if OVERRIDES.exists() else {}
    questions=load_questions()
    links=[]
    audits=[]
    for q in questions:
        mappings,reason=classify(q,overrides)
        audit=dict(occurrence_id=q['ocorrencia_id'],question_id=q['questao_id'],hash=q['hash_texto'],
                   bank=q['banca'],contest=q['concurso'],number=q['numero_original'],format=q['formato'],
                   correctable=eligible(q),status_extraction=q['status_extracao'],
                   answer_state=q['answer_state'],answer_situation=q['answer_situation'],definitive=bool(q['definitive']),
                   stem=q['enunciado_original'],alternatives=q['alternatives'],reason=reason,lessons=[])
        for m in mappings:
            unit=units[m['key']]
            lid=unit['lesson_id']
            assert m['evidence']
            link=dict(lesson_id=lid,occurrence_id=q['ocorrencia_id'],question_id=q['questao_id'],hash=q['hash_texto'],
                      bank=q['banca'],contest=q['concurso'],number=q['numero_original'],correctable=eligible(q),
                      lesson_title=unit['title'],syllabus_excerpt=unit['source_excerpt'],
                      **{k:v for k,v in m.items() if k not in ['key','stem_count']})
            links.append(link)
            audit['lessons'].append(dict(lesson_id=lid,title=unit['title'],score=m['score'],relation=m['relation'],evidence=m['evidence']))
        audits.append(audit)
    by_lesson=defaultdict(list)
    for l in links:
        by_lesson[l['lesson_id']].append(l)
    report=dict(method=METHOD,plan_id=plan['id'],created_at=datetime.now(timezone.utc).isoformat(),
                total_occurrences=len(questions),total_unique_questions=len({q['questao_id'] for q in questions}),
                linked_occurrences=len({l['occurrence_id'] for l in links}),
                linked_unique_questions=len({l['question_id'] for l in links}),links=len(links),
                unlinked_occurrences=sum(not a['lessons'] for a in audits),
                lessons_with_questions=len(by_lesson),lessons_without_questions=len(units)-len(by_lesson),
                correctable_linked_occurrences=len({l['occurrence_id'] for l in links if l['correctable']}),
                by_bank={b:dict(total=sum(q['banca']==b for q in questions),linked=len({l['occurrence_id'] for l in links if l['bank']==b})) for b in sorted({q['banca'] for q in questions})},
                reasons=dict(Counter(a['reason'] for a in audits if not a['lessons'])),
                lessons=[dict(lesson_id=u['lesson_id'],title=u['title'],questions=len(by_lesson[u['lesson_id']]),
                              unique_questions=len({l['question_id'] for l in by_lesson[u['lesson_id']]}),
                              correctable=sum(l['correctable'] for l in by_lesson[u['lesson_id']])) for u in units.values()])
    OUTPUT.mkdir(parents=True,exist_ok=True)
    for name,data in [('vinculos.jsonl',links),('auditoria-toda-base.jsonl',audits)]:
        (OUTPUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in data),encoding='utf-8')
    (OUTPUT/'relatorio.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Vinculação de questões ao APOFP A01', '',
           f"Analisadas {report['total_occurrences']} ocorrências ({report['total_unique_questions']} conteúdos distintos), em todas as seis bancas. {report['linked_occurrences']} ocorrências compatíveis, {report['links']} vínculos e {report['lessons_with_questions']} aulas com questões.", '',
           'As evidências e a correspondência com o trecho do edital são registradas por vínculo. Classificação temática por regras explícitas, com revisões individuais registradas em revisoes.json; não equivale a revisão humana integral. A mesma questão pode apoiar aulas de conteúdo comum e específico quando há sobreposição real. Cada ocorrência conserva sua prova de origem.', '',
           'A validade do vínculo temático não altera o estado da extração ou do gabarito. Apenas itens extraídos com gabarito definitivo, válido e concordante são corrigidos automaticamente. Questões sem definitivo, anuladas ou com divergência ficam identificadas para consulta. Referências normativas antigas exigem conferência com o edital atual.', '',
           '| Aula | Ocorrências | Conteúdos distintos | Corrigíveis |','|---|---:|---:|---:|']
    lines += [f"| {r['lesson_id']} · {r['title']} | {r['questions']} | {r['unique_questions']} | {r['correctable']} |" for r in report['lessons']]
    lines += ['', '## Sem vínculo', '',f"{report['unlinked_occurrences']} ocorrências ficaram fora das aulas por ausência de correspondência segura ou conteúdo fora do edital. A auditoria de todas as ocorrências, incluindo as excluídas, está em auditoria-toda-base.jsonl.", '',
              '## Reprodução', '', 'Execute `map_questions.py` para recalcular os arquivos sem alterar o banco. `map_questions.py --apply` faz backup SQLite e adiciona os vínculos no banco de estudo, mantendo seleções anteriores. O banco de conteúdo é aberto somente em modo de leitura.', '']
    (OUTPUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    return questions,links,report


def apply_links(links,report,db_path=STUDY):
    db_path=Path(db_path).resolve()
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup=db_path.with_name('estudo-antes-vinculacao-'+stamp+'.sqlite')
    run_id='mapping_'+stamp
    with closing(sqlite3.connect(db_path,timeout=30)) as con:
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('PRAGMA busy_timeout=30000')
        with closing(sqlite3.connect(backup)) as dest:
            con.backup(dest)
        init_schema(con)
        con.execute('BEGIN IMMEDIATE')
        con.execute('INSERT INTO question_mapping_runs VALUES(?,?,?)',(run_id,datetime.now(timezone.utc).isoformat(),json.dumps(report,ensure_ascii=False)))
        wanted={(l['lesson_id'],l['occurrence_id']) for l in links}
        managed=con.execute('''SELECT m.lesson_id,m.occurrence_id FROM lesson_question_mappings m
                               JOIN plan_units u USING(lesson_id) WHERE u.plan_id=?''',(report['plan_id'],)).fetchall()
        stale=[pair for pair in managed if tuple(pair) not in wanted]
        # Reclassification replaces only obsolete generated correspondences.
        # Manual selections have no row in this provenance table and survive.
        con.executemany('DELETE FROM lesson_questions WHERE lesson_id=? AND occurrence_id=?',stale)
        position={r[0]:r[1]+1 for r in con.execute('SELECT lesson_id,max(position) FROM lesson_questions GROUP BY lesson_id')}
        before=con.execute('SELECT count(*) FROM lesson_questions').fetchone()[0]
        # Prefer items that can be graded, then FCC, then newer exams and stronger
        # matches. All accepted occurrences are linked; order is not a filter.
        ordered=sorted(links,key=lambda l:(l['lesson_id'],not l['correctable'],l['bank']!='FCC',-int(l['contest'][:4]),-l['score'],l['occurrence_id']))
        for l in ordered:
            lid=l['lesson_id']
            cursor=con.execute('INSERT OR IGNORE INTO lesson_questions VALUES(?,?,?)',
                              (lid,l['occurrence_id'],position.get(lid,0)))
            if cursor.rowcount:
                position[lid]=position.get(lid,0)+1
            con.execute('''INSERT INTO lesson_question_mappings VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(lesson_id,occurrence_id) DO UPDATE SET relation=excluded.relation,
                confidence=excluded.confidence,method=excluded.method,score=excluded.score,
                evidence_json=excluded.evidence_json,syllabus_excerpt=excluded.syllabus_excerpt,
                note=excluded.note,run_id=excluded.run_id''',
                (lid,l['occurrence_id'],l['relation'],l['confidence'],l['method'],l['score'],
                 json.dumps(l['evidence'],ensure_ascii=False),l['syllabus_excerpt'],l['note'],run_id))
        assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
        con.commit()
        return dict(added=con.execute('SELECT count(*) FROM lesson_questions').fetchone()[0]-before,
                    removed_obsolete_generated=len(stale),
                    links=len(links),backup=str(backup),run_id=run_id)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    questions,links,report=build()
    print(json.dumps({k:v for k,v in report.items() if k!='lessons'},ensure_ascii=False,indent=2))
    if args.apply:
        print(json.dumps(apply_links(links,report),ensure_ascii=False))
