from __future__ import annotations
import json
import re
from pathlib import Path
from reparar_ce import reconstruct

BASE=Path(__file__).resolve().parent
RUN=BASE/'execucoes/2026-10-29'

def normal(s):return re.sub(r'\s+',' ',s or '').strip()
def clean(s):
    lines=s.splitlines()
    reject=re.compile(r'^\s*(?:Caderno de Prova|COPER-(?:Conhec|An\.)|EMPRESA DE PESQUISAS? ENERG[EÉ]TICAS?\s*[-–]|SECRETARIA DO TESOURO NACIONAL\s*$|FGV CONHECIMENTO\s*$|Confidencial at[eé] o momento da aplica[çc][aã]o\.?\s*$)',re.I)
    return '\n'.join(l for l in lines if not reject.search(l)).strip()

def main():
    allq=[]
    for f in sorted((RUN/'lotes').glob('*.questoes.jsonl')):
        allq.extend(json.loads(l) for l in f.read_text(encoding='utf-8').splitlines() if l.strip())
    bykey={(q['documento_id'],str(q['numero_original'])):q for q in allq}
    changes={}
    def changed(q,reason):
        key=(q['documento_id'],str(q['numero_original']))
        if key not in changes:
            q['texto_transcrito_bruto']=q['texto_original_completo']
            q['correcoes_coordenador']=[]
            changes[key]=q
        q['correcoes_coordenador'].append(reason)
    reconstruct(RUN,allq,changed)
    # A última página da SEPLAG é de largura inteira, diferente das anteriores.
    did='doc_0e7efafee31db5610fc6'
    page=json.loads((RUN/'paginas'/(did+'.json')).read_text(encoding='utf-8'))['paginas'][3]
    lines=[l for l in page['linhas'] if l['bbox'][1]>35 and l['texto'].strip()!='Espaço livre']
    marks=[(i,int(m.group(1))) for i,l in enumerate(lines) if (m:=re.match(r'^(14[5-9]|150)\s+',l['texto']))]
    for index,(start,num) in enumerate(marks):
        end=marks[index+1][0] if index+1<len(marks) else len(lines)
        chunk=lines[start:end]
        if num==146:chunk=chunk[:next((i for i,l in enumerate(chunk) if l['texto'].startswith('Com base nas Resolu')),len(chunk))]
        chunk=[l for l in chunk if l['texto'].strip() and not l['texto'].startswith('CEBRASPE')]
        text=re.sub(r'^\d+\s+','','\n'.join(l['texto'] for l in chunk)).strip()
        q=bykey[(did,str(num))];changed(q,'Página de coluna única reconstruída a partir das linhas completas do PDF')
        q['enunciado_original']=text;q['texto_original_completo']=text
        q['regioes_fonte']=[{'pagina':4,'bbox':[min(l['bbox'][0] for l in chunk),min(l['bbox'][1] for l in chunk),max(l['bbox'][2] for l in chunk),max(l['bbox'][3] for l in chunk)]}]
        command='Com relação à concessão de serviços públicos e às regras das organizações sociais, segundo a Lei estadual n.º 12.781/1997, julgue os itens subsequentes.' if num<147 else 'Com base nas Resoluções n.º 40/2001, n.º 43/2001 e n.º 48/2007 do Senado Federal, julgue os itens que se seguem.'
        q['contextos']=[{'texto':command,'paginas_pdf':[4],'regioes_fonte':[{'pagina':4,'bbox':[0,0,page['largura'],page['altura']]}]}]
    # Separar textos compartilhados que começaram depois das alternativas da questão anterior.
    pattern=re.compile(r'(?im)^.*(?:quest[õo]es|itens)(?:\s+de)?(?:\s+n[úu]meros?)?\s+0?(\d+)\s*(?:a|at[eé])\s*0?(\d+)\s*\.?')
    for q in allq:
        try:current=int(q['numero_original'])
        except ValueError:continue
        text=q['texto_original_completo']
        for m in pattern.finditer(text):
            low,high=map(int,m.groups())
            if current<low<=high and low-current<=2 and high-low<=30 and m.start()>text.find('(E)')>0:
                moved=clean(text[m.start():])
                changed(q,'Texto-base das questões seguintes separado das alternativas')
                q['texto_original_completo']=clean(text[:m.start()])
                for target in range(low,high+1):
                    other=bykey.get((q['documento_id'],str(target)))
                    if other and not any(normal(c.get('texto',''))==normal(moved) for c in other.get('contextos',[])):
                        changed(other,'Texto-base compartilhado vinculado à faixa impressa de questões')
                        other.setdefault('contextos',[]).append({'texto':moved,'paginas_pdf':q['paginas_pdf'],'regioes_fonte':q['regioes_fonte']})
                break
    # Correção visual da questão 85: os rótulos D/C internos significam débito/crédito.
    q=bykey[('doc_996cea21fa0a001ca696','85')]
    changed(q,'Cinco alternativas conferidas na imagem p.18; débitos/créditos internos preservados')
    q['alternativas']=[
        {'rotulo':'A','texto':'(D) Estoques $ 100.000 + (D) ICMS $ 18.000; (C) Fornecedores $ 118.000.'},
        {'rotulo':'B','texto':'(D) Estoques $ 100.000; (C) Fornecedores $ 82.000 + (C) ICMS a Recuperar $ 18.000.'},
        {'rotulo':'C','texto':'(D) Estoques $ 118.000: (C) Fornecedores $ 100.000 + (C) ICMS a Recuperar $ 118.000.'},
        {'rotulo':'D','texto':'(D) Estoques $ 118.000; (C) Fornecedores $ 118.000.'},
        {'rotulo':'E','texto':'(D) Estoques $ 82.000 + (D) ICMS $ 18.000; (C) Fornecedores $ 100.000.'},
    ]
    q['formato']='multipla_escolha'
    q['enunciado_original']=q['texto_original_completo'].split('(A)',1)[0].strip()
    q['texto_original_completo']=re.sub(r'\n18\s*$','',q['texto_original_completo'])
    q['alertas']=[x for x in q['alertas'] if not re.search(r'(?i)alternativ',x)]
    q['status_extracao']='extraido' if not q['alertas'] else 'precisa_revisao'
    # Trecho que antecede o número 4 na página seguinte pertence ao enunciado 4.
    q=bykey[('doc_f7b93f5f3007eed1d281','3')]
    marker='A nova linguagem do mar'
    if marker in q['texto_original_completo']:
        text=q['texto_original_completo'];start=text.index(marker);moved=text[start:]
        changed(q,'Citação de abertura da questão 4 separada da alternativa E da questão 3')
        q['texto_original_completo']=text[:start]
        q4=bykey[('doc_f7b93f5f3007eed1d281','4')]
        changed(q4,'Citação de abertura recuperada da página anterior ao marcador')
        q4.setdefault('contextos',[]).append({'texto':clean(moved),'paginas_pdf':[3],'regioes_fonte':[{'pagina':3,'bbox':[0,0,595.32,841.92]}]})
    # Higiene editorial sem remover números do conteúdo, valores, fórmulas ou tabelas.
    for q in allq:
        raw=q['texto_original_completo'];cleaned=clean(raw)
        if raw!=cleaned:
            changed(q,'Identificadores editoriais de cabeçalho/rodapé removidos do texto pesquisável')
            q['texto_original_completo']=cleaned
        if q.get('alternativas'):
            for a in q['alternativas']:
                text=a['texto'];new=clean(text)
                if q['documento_id']=='doc_f7b93f5f3007eed1d281' and q['numero_original']=='3' and a['rotulo']=='E':new='III, apenas.'
                if q['documento_id']=='doc_566b070aa3ceb1c6d27c' and q['numero_original']=='1' and a['rotulo']=='E':new='parcimônia.'
                if text!=new:
                    changed(q,'Limpeza de alternativa após conferência de fronteira editorial')
                    a['texto']=new
            # O enunciado fica separado das alternativas; a transcrição integral permanece disponível.
            first=re.search(r'(?m)^\s*\(?[Aa]\)\s*',q['texto_original_completo'])
            if first and '(A)' in q.get('enunciado_original',''):
                changed(q,'Enunciado separado das alternativas já estruturadas')
                q['enunciado_original']=q['texto_original_completo'][:first.start()].strip()
            elif q['documento_id']=='doc_566b070aa3ceb1c6d27c' and q['numero_original']=='1':
                q['enunciado_original']=q['texto_original_completo'].split('(A)',1)[0].strip()
    (RUN/'correcoes_questoes.jsonl').write_text(''.join(json.dumps(q,ensure_ascii=False)+'\n' for q in changes.values()),encoding='utf-8')
    print(json.dumps({'questoes_com_revisao_coordenador':len(changes),'correcoes':sum(len(q['correcoes_coordenador']) for q in changes.values())}))

if __name__=='__main__':main()
