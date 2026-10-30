"""Extração rastreável de provas Cebraspe e Fundatec para a base de questões."""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "base-questoes/execucoes/2026-10-29/documentos.json"
OUT = ROOT / "base-questoes/execucoes/2026-10-29/lotes"
OUT.mkdir(parents=True, exist_ok=True)
METHOD = "pdfplumber com coordenadas; segmentação por marcadores impressos e regras de formato. Classificações temáticas são inferências heurísticas por evidência lexical contextual; habilidades não preenchidas automaticamente."


def clean(s: str) -> str:
    s = s.replace("\u00ad", "")
    s = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def bbox_for_words(words):
    if not words:
        return None
    return [round(min(w["x0"] for w in words), 1), round(min(w["top"] for w in words), 1),
            round(max(w["x1"] for w in words), 1), round(max(w["bottom"] for w in words), 1)]


def page_blocks(page, pageno, two_columns=False):
    width = float(page.width)
    words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)
    def make_lines(ws):
        groups=[]
        for w in sorted(ws,key=lambda a:(a["top"],a["x0"])):
            if groups and abs(groups[-1][0]["top"]-w["top"])<=3: groups[-1].append(w)
            else: groups.append([w])
        result=[]
        for g in groups:
            g=sorted(g,key=lambda a:a["x0"])
            result.append((" ".join(w["text"] for w in g),[min(w["x0"] for w in g),min(w["top"] for w in g),max(w["x1"] for w in g),max(w["bottom"] for w in g)]))
        return result
    left=[w for w in words if (w["x0"]+w["x1"])/2 < width*.51]
    right=[w for w in words if (w["x0"]+w["x1"])/2 >= width*.51]
    if two_columns and left and right:
        return make_lines(left)+make_lines(right)
    return make_lines(words)


def extract_page_lines(pdf_path, two_columns=False):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i,p in enumerate(pdf.pages, 1):
            pages.append(page_blocks(p, i, two_columns=two_columns))
    return pages


def page_texts(lines):
    return ["\n".join(t for t,_ in pg) for pg in lines]


def normalize_lines(lines):
    out=[]
    for pi,pg in enumerate(lines,1):
        for text,bbox in pg:
            t=clean(text)
            if not t: continue
            if re.search(r"Página\s+\d+\s+de\s+\d+|www\.cebraspe|Cebraspe|Fundatec", t, re.I) and len(t)<120:
                continue
            out.append({"pagina":pi,"texto":t,"bbox":bbox})
    return out


def infer_discipline(text, concurso, section_hint=None):
    # Explicit headings are preferred. Otherwise leave unknown rather than guess.
    known = ["Língua Portuguesa", "Língua Inglesa", "Língua Espanhola", "Raciocínio Lógico", "Contabilidade Geral",
             "Contabilidade Pública", "Direito Administrativo", "Direito Constitucional", "Direito Tributário",
             "Direito Financeiro", "Administração Pública", "Economia", "AFO", "Auditoria", "Estatística", "Matemática Financeira"]
    hay=(section_hint or "")+" "+text[:500]
    for d in known:
        if re.search(re.escape(d),hay,re.I): return d
    return section_hint


TAXA = [
    ("orçamento público", ["orçamento", "loa", "ldo", "ppa", "crédito adicional", "receita pública", "despesa pública"]),
    ("contabilidade pública", ["mcasp", "restos a pagar", "ativo financeiro", "passivo financeiro", "variação patrimonial"]),
    ("contabilidade geral", ["balanço patrimonial", "estoque", "depreciação", "receita de equivalência", "demonstrações contábeis"]),
    ("direito tributário", ["tributo", "icms", "iss", "imposto", "crédito tributário", "obrigação tributária"]),
    ("administração pública", ["governança", "gestão pública", "política pública", "indicador", "planejamento estratégico"]),
    ("língua portuguesa", ["texto", "oração", "pronome", "concordância", "pontuação", "coesão"]),
    ("economia", ["inflação", "elasticidade", "oferta", "demanda", "produto interno bruto", "taxa de juros"]),
    ("direito administrativo", ["licitação", "servidor público", "ato administrativo", "administração pública"]),
]


def heuristic_classification(text, discipline):
    low=text.lower()
    hits=[]
    for assunto,terms in TAXA:
        found=[t for t in terms if t in low]
        if found:
            hits.append({"disciplina":discipline or assunto.title(),"assunto":assunto,"subassunto":None,"papel":"central",
                         "trecho_evidencia":next((s.strip()[:220] for s in re.split(r"(?<=[.!?])\s+",text) if any(t in s.lower() for t in found)),text[:220]),
                         "origem":"heuristica_codigo_lexical_contextual","confianca":"baixa"})
            if len(hits)>=2: break
    return hits


def answer_format(doc):
    if doc["banca"] == "Cebraspe" and doc["concurso"] == "2025-SEFAZ-RJ-FINANCAS": return "multipla_escolha"
    if doc["banca"] == "Fundatec": return "multipla_escolha"
    return "certo_errado"


def heading_before(raw, idx):
    for row in reversed(raw[max(0,idx-18):idx]):
        t=row["texto"].strip()
        if (4 <= len(t) <= 90 and t == t.upper() and re.search(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ]",t)
                and not re.search(r"CEBRASPE|FUNDATEC|PROVA|EXECUÇÃO|ANALISTA|EDITAL|ESPAÇO LIVRE|QUESTÃO",t)):
            return t
    return None


def build_questions(doc, lines):
    raw=normalize_lines(lines)
    joined="\n".join(x["texto"] for x in raw)
    banca=doc["banca"]
    questions=[]
    if banca=="Cebraspe" and doc["concurso"] != "2025-SEFAZ-RJ-FINANCAS":
        # Each numbered item is independent. Shared instructions and source texts are attached to all items in that block.
        starts=[]
        active=False
        for i,x in enumerate(raw):
            if re.search(r"julgue\s+(?:os|os seguintes|os próximos|os itens)|judge the following|juzgue los siguientes",x["texto"],re.I): active=True
            m=re.match(r"^(\d{1,3})\s+(\S.*)$",x["texto"])
            if active and m and int(m.group(1))<=200 and len(m.group(2))>4:
                starts.append((i,m.group(1),m.group(2)))
        for k,(idx,num,first) in enumerate(starts):
            end=starts[k+1][0] if k+1<len(starts) else len(raw)
            seg=raw[idx:end]
            if banca=="Fundatec":
                essay_at=next((j for j,z in enumerate(seg) if re.fullmatch(r"\s*PROVA\s+DISSERTATIVA\s*",z["texto"],re.I)),None)
                if essay_at is not None: seg=seg[:essay_at]
            text=clean("\n".join([first]+[x["texto"] for x in seg[1:]]))
            if len(text)<35: continue
            pages=sorted(set(x["pagina"] for x in seg))
            regs=[{"pagina":x["pagina"],"bbox":x["bbox"]} for x in seg if x["bbox"]]
            # Shared command/context immediately before sequence, bounded to 5 preceding lines.
            context=[]
            for prev in raw[max(0,idx-8):idx]:
                if re.search(r"Julgue|Com base|Considerando|A respeito|Texto|A seguir|Nas questões|itens seguintes",prev["texto"],re.I):
                    context.append({"texto":prev["texto"],"paginas_pdf":[prev["pagina"]],"regioes_fonte":[{"pagina":prev["pagina"],"bbox":prev["bbox"]}] if prev["bbox"] else []})
            if doc["concurso"]=="2024-MPO-APO" and doc["nome"]=="p1-conhecimentos-gerais" and num.isdigit() and int(num)<=10:
                anchor="The Scottish government" if int(num)<=5 else "El Bellas Artes se renueva"
                begin=next((j for j,z in enumerate(raw) if z["pagina"]==1 and anchor.lower() in z["texto"].lower()),None)
                finish=next((j for j in range(begin+1,len(raw)) if raw[j]["pagina"]==1 and "internet:" in raw[j]["texto"].lower()),None) if begin is not None else None
                if begin is not None and finish is not None:
                    shared=raw[begin:finish+1]
                    context.append({"texto":clean("\n".join(z["texto"] for z in shared)),"paginas_pdf":[1],"regioes_fonte":[{"pagina":1,"bbox":z["bbox"]} for z in shared if z["bbox"]]})
            item=make_item(doc,num,None,"certo_errado",text,[],context,pages,regs,discipline=heading_before(raw,idx))
            if doc["concurso"]=="2024-MPO-APO" and doc["nome"]=="p1-conhecimentos-gerais" and num.isdigit() and int(num)<=10:
                lang="Língua Inglesa" if int(num)<=5 else "Língua Espanhola"
                item["disciplina_original"]=lang; item["bloco_original"]=lang
            questions.append(item)
    else:
        # Multiple choice question starts commonly appear as "QUESTÃO 1", "1." or "1)".
        starts=[]
        for i,x in enumerate(raw):
            t=x["texto"]
            m=re.match(r"^QUEST.{0,4}?\s*(\d{1,3})\s*(?:[.)\-:–—]\s*)?(.*)$",t,re.I)
            if m and 1<=int(m.group(1))<=200:
                starts.append((i,m.group(1),m.group(2)))
            elif banca=="Cebraspe" and doc["concurso"]=="2025-SEFAZ-RJ-FINANCAS":
                m=re.match(r"^Quest.{0,4}?\s*(\d{1,3})\s*$",t,re.I)
                if m and 1<=int(m.group(1))<=200: starts.append((i,m.group(1),""))
        # Cebraspe 2025 has section / item numbering. Fundatec begins at 1 and has a discursiva near end.
        starts=starts
        for k,(idx,num,first) in enumerate(starts):
            end=starts[k+1][0] if k+1<len(starts) else len(raw)
            seg=raw[idx:end]
            text=clean("\n".join([first]+[x["texto"] for x in seg[1:]]))
            # Split alternatives while preserving printed labels.
            altpat=re.compile(r"(?m)(?:^|\n)\s*([A-E])\s*[\).]\s+" if banca=="Fundatec" else r"(?m)(?:^|\n)\s*([A-E])\s+")
            matches=list(altpat.finditer(text))
            if len(matches)>5:
                windows=[i for i in range(len(matches)-4) if [matches[j].group(1) for j in range(i,i+5)]==list("ABCDE")]
                if windows: matches=matches[windows[-1]:windows[-1]+5]
            alts=[]; stem=text
            if len(matches)>=3:
                stem=text[:matches[0].start()].strip()
                for j,m in enumerate(matches):
                    stop=matches[j+1].start() if j+1<len(matches) else len(text)
                    alts.append({"rotulo":m.group(1),"texto":text[m.end():stop].strip()})
            pages=sorted(set(x["pagina"] for x in seg)); regs=[{"pagina":x["pagina"],"bbox":x["bbox"]} for x in seg if x["bbox"]]
            fmt="multipla_escolha"
            contexts=[]
            if banca=="Fundatec" and num.isdigit() and int(num)<=10 and starts:
                first_index=starts[0][0]
                first_page=raw[first_index]["pagina"]
                shared=[z for zi,z in enumerate(raw) if (z["pagina"]==first_page-1 or (z["pagina"]==first_page and zi<first_index))]
                if shared:
                    contexts=[{"texto":clean("\n".join(z["texto"] for z in shared)),"paginas_pdf":sorted({z["pagina"] for z in shared}),
                               "regioes_fonte":[{"pagina":z["pagina"],"bbox":z["bbox"]} for z in shared if z["bbox"]]}]
            questions.append(make_item(doc,num,None,fmt,stem,alts,contexts,pages,regs,discipline=heading_before(raw,idx)))
        if banca=="Fundatec":
            # Explicitly include any essay prompt pages outside numeric question parsing.
            for i,x in enumerate(raw):
                if re.fullmatch(r"\s*PROVA\s+DISSERTATIVA\s*",x["texto"],re.I):
                    if not any(q["formato"]=="discursiva" for q in questions):
                        page=x["pagina"]; seg=[z for z in raw if z["pagina"]==page]
                        txt=clean("\n".join(z["texto"] for z in seg))
                        questions.append(make_item(doc,"D1",None,"discursiva",txt,[],[],sorted({z["pagina"] for z in seg}),[{"pagina":z["pagina"],"bbox":z["bbox"]} for z in seg if z["bbox"]],"PROVA DISSERTATIVA"))
                    break
    # Keep sequence in source order and assign inferred discipline conservatively.
    questions.sort(key=lambda q:(int(q["numero_original"]) if q["numero_original"].isdigit() else 9999,
                                 min(q["paginas_pdf"] or [0])))
    return questions, joined


def make_item(doc,num,block,fmt,stem,alts,contexts,pages,regions,discipline=None):
    full=stem + ("\n"+"\n".join(f"{a['rotulo']}) {a['texto']}" for a in alts) if alts else "")
    refs=[]
    for m in re.finditer(r"\b(?:art(?:igo)?\.?\s*\d+[ºo]?(?:,\s*§\s*\d+[ºo]?)?|Lei\s+(?:Complementar\s+)?n[ºo.]?\s*[\d.]+/\d{4}|Decreto\s+n[ºo.]?\s*[\d.]+/\d{4})\b",full,re.I): refs.append(m.group(0))
    alerts=[]
    if fmt=="multipla_escolha" and len(alts)!=5: alerts.append(f"Alternativas segmentadas: {len(alts)}; revisar contagem e limites.")
    if re.search(r"figura|gráfico|cartograma|imagem|tabela",full,re.I): alerts.append("Questão menciona figura, gráfico, cartograma, imagem ou tabela; conferir o elemento visual no PDF original.")
    return {"documento_id":doc["documento_id"],"prova_id":doc["documento_id"],"numero_original":str(num),"bloco_original":block,
            "formato":fmt,"disciplina_original":discipline,"enunciado_original":stem,"alternativas":alts,"contextos":contexts,
            "paginas_pdf":pages,"regioes_fonte":regions,"texto_original_completo":full,"status_extracao":"extraido" if len(full)>35 and not alerts else "precisa_revisao",
            "alertas":alerts,"classificacoes":heuristic_classification(full,discipline),"habilidades":[],"referencias_normativas_literais":list(dict.fromkeys(refs)),
            "metodo_extracao":METHOD,"agente":"Luna — extração determinística assistida por heurísticas"}


def main():
    docs=json.loads(MANIFEST.read_text(encoding="utf-8"))
    targets=[d for d in docs if d["tipo"]=="provas" and d["banca"] in ("Cebraspe","Fundatec")]
    allq=[]; reports=[]
    for doc in targets:
        pages=extract_page_lines(Path(doc["arquivo"]), two_columns=doc["banca"]=="Cebraspe")
        qs,text=build_questions(doc,pages)
        nums=[q["numero_original"] for q in qs]
        counts=Counter(nums); dups=[n for n,c in counts.items() if c>1]
        gaps=[]
        numeric=sorted({int(n) for n in nums if n.isdigit()})
        if numeric:
            expected=None
            if doc["banca"]=="Fundatec" and re.search(r"contém\s+100\b.*questões",text,re.I|re.S):
                expected={"objetivas":100,"discursivas":1} if re.search(r"contém\s+1\b.*dissertativa",text,re.I|re.S) else {"objetivas":100}
            expected_max=(expected.get("objetivas") if isinstance(expected,dict) else expected) if expected else max(numeric)
            gaps=[n for n in range(min(numeric),expected_max+1) if n not in numeric]
        else: expected=None
        alerts=[]
        if not qs: alerts.append("Nenhuma questão segmentada automaticamente; requer revisão manual.")
        if dups: alerts.append(f"Números repetidos no mesmo documento: {dups}")
        if gaps: alerts.append(f"Lacunas de numeração: {gaps}")
        visual_samples=([1,3,38] if doc["banca"]=="Fundatec" else [1,3] if doc["concurso"]=="2024-SEPLAG-CE-APO" else [1] if doc["concurso"] in ("2024-MPO-APO","2025-SEFAZ-RJ-FINANCAS") else [])
        reports.append({"documento_id":doc["documento_id"],"concurso":doc["concurso"],"arquivo":doc["arquivo_relativo"],"paginas_pdf":len(pages),
                        "questoes_extraidas":len(qs),"numeros_encontrados":nums,"quantidade_esperada_explicita":expected,"lacunas":gaps,"duplicacoes":dups,
                        "duvidas":alerts,"amostras_visuais_revisadas":visual_samples,"notas":"Classificação lexical automática é baixa confiança; habilidades deixadas vazias salvo revisão individual."})
        allq.extend(qs)
    outfile=OUT/"cebraspe_fundatec.questoes.jsonl"
    outfile.write_text("".join(json.dumps(q,ensure_ascii=False)+"\n" for q in allq),encoding="utf-8")
    report={"grupo":"cebraspe_fundatec","metodo":METHOD,"total_questoes":len(allq),"documentos":reports}
    (OUT/"cebraspe_fundatec.relatorio.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(outfile),"total":len(allq),"docs":[(r['concurso'],r['questoes_extraidas'],r['numeros_encontrados'][:4],r['numeros_encontrados'][-4:]) for r in reports]},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
