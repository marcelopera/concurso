"""Repara fronteiras de itens C/E usando recuo físico e linhas integrais do PDF."""
import json,re
from collections import defaultdict

def reconstruct(run, questions, changed):
    groups=defaultdict(list)
    for q in questions:
        if q['formato']=='certo_errado':groups[q['documento_id']].append(q)
    for did,items in groups.items():
        cache=json.loads((run/'paginas'/(did+'.json')).read_text(encoding='utf-8'))
        stream=[]
        for page in cache['paginas']:
            lines=[l for l in page['linhas'] if l['bbox'][1]>42 and l['texto'].strip() and l['texto'].strip()!='Espaço livre']
            wide=any(re.match(r'^\d{2,3}\s+',l['texto']) and l['bbox'][0]<100 and l['bbox'][2]>page['largura']*.8 for l in lines)
            columns=[lines] if wide else [[l for l in lines if (l['bbox'][0]+l['bbox'][2])/2<page['largura']*.5],[l for l in lines if (l['bbox'][0]+l['bbox'][2])/2>=page['largura']*.5]]
            for col in columns:
                groups=[]
                for l in sorted(col,key=lambda l:(round(l['bbox'][1],1),l['bbox'][0])):
                    if groups and abs(l['bbox'][1]-groups[-1][0]['bbox'][1])<1.6:groups[-1].append(l)
                    else:groups.append([l])
                merged=[]
                for group in groups:
                    group.sort(key=lambda l:l['bbox'][0])
                    merged.append({'texto':' '.join(l['texto'] for l in group),'bbox':[min(l['bbox'][0] for l in group),min(l['bbox'][1] for l in group),max(l['bbox'][2] for l in group),max(l['bbox'][3] for l in group)],'pagina':page['numero']})
                stream.extend(merged)
        bynum={int(q['numero_original']):q for q in items};seen=set();segments={};current=None;context=[];shared=[];body=[];base=28.3
        def finish():
            if current is not None:segments[current]=(list(body),list(shared))
        for line in stream:
            text=line['texto'].strip();m=re.match(r'^(\d{1,3})\s+(\S.*)$',text)
            num=int(m.group(1)) if m else None
            expected=min(set(bynum)-seen) if set(bynum)-seen else None
            if m and num==expected and abs(line['bbox'][0]-(28.3 if line['bbox'][0]<290 else 303.36))<4:
                finish();current=num;seen.add(num);base=line['bbox'][0]
                if context:shared=context;context=[]
                body=[dict(line,texto=m.group(2))]
            elif current is not None and not context and abs(line['bbox'][0]-(base+17.88))<4:
                body.append(line)
            else:
                # Títulos centralizados encerram o item anterior, mas não integram o texto-base.
                isheading=text==text.upper() and len(text)>5 and not re.search(r'[\d=+*]',text) and bool(re.search(r'[A-ZÁÉÍÓÚ]{4}',text))
                if isheading:
                    finish();current=None;context=[];shared=[]
                else:context.append(line)
        finish()
        assert seen==set(bynum),(did,sorted(set(bynum)-seen))
        for num,(body,ctx) in segments.items():
            q=bynum[num];changed(q,'Itens C/E separados dos comandos seguintes pelo recuo impresso; textos-base completos recuperados')
            text='\n'.join(l['texto'] for l in body).strip()
            q['enunciado_original']=text;q['texto_original_completo']=text
            q['regioes_fonte']=[{'pagina':l['pagina'],'bbox':l['bbox']} for l in body]
            q['paginas_pdf']=sorted({l['pagina'] for l in body}|{l['pagina'] for l in ctx})
            q['contextos']=[{'texto':'\n'.join(l['texto'] for l in ctx),'paginas_pdf':sorted({l['pagina'] for l in ctx}),'regioes_fonte':[{'pagina':l['pagina'],'bbox':l['bbox']} for l in ctx]}] if ctx else []
            if len(text)<25:
                q['status_extracao']='precisa_revisao';q.setdefault('alertas',[]).append('Conferir fronteira curta após reconstrução por recuo')
