"""Enriquecimento lexical rastreável para o lote Cebraspe/Fundatec.

Regras usam indicadores específicos no enunciado; casos sem evidência suficiente
ficam sem tags e são contados como pendentes no relatório, sem completar por default.
"""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"base-questoes/execucoes/2026-10-29/lotes"
SOURCE=BASE/"cebraspe_fundatec.questoes.jsonl"
TARGET=BASE/"cebraspe_fundatec.enriquecimento.jsonl"
REPORT=BASE/"cebraspe_fundatec.enriquecimento.relatorio.json"
ORIGIN="heuristica_regras_luna"

# (regex, discipline, subject, subsubject, action, object, demand type, confidence)
RULES=[
 (r"(legitima[cç][aã]o pelo procedimento|interpreta[cç][aã]o jur[ií]dica|imunidade de jurisdi[cç][aã]o|atos de imp[eé]rio|quinto constitucional|mes[aá]rios|agentes de colabora[cç][aã]o|pejotiza[cç][aã]o)","Direito Público","Instituições e categorias jurídicas","Legitimidade, agentes e relações de trabalho","aplicar ou distinguir","categoria jurídica ou consequência institucional indicada","interpretação conceitual ou normativa","media"),
 (r"(cr[eé]dito extraordin[aá]rio|or[cç]amento[- ]programa|or[cç]amento base[- ]zero|or[cç]amento sens[ií]vel ao g[eê]nero|classifica[cç][aã]o program[aá]tica|classifica[cç][aã]o da despesa|despesa p[uú]blica|despesa corrente|despesa n[aã]o efetiva|super[aá]vit financeiro|emenda.*projeto de lei do or[cç]amento|liquida[cç][aã]o.*credor|restos a pagar|est[aá]gios da despesa|princ[ií]pio.*or[cç]ament)","Planejamento e orçamento público","Orçamento público","Técnicas, classificações e execução da despesa","identificar ou aplicar","técnica orçamentária, classificação ou estágio de execução","interpretação normativa","media"),
 (r"(planejamento para o desenvolvimento|plano plurianual|mensagem presidencial|prioridades.*ppa|plano de metas|planejamento.*ind[uú]stria|indicador tem[aá]tico|or[cç]amento-programa|produtos finais|med[ií]ç[aã]o do trabalho)","Planejamento governamental","Planejamento e orçamento","Instrumentos e evolução do planejamento público","relacionar","instrumento de planejamento à finalidade ou ao contexto histórico descrito","interpretação conceitual","media"),
 (r"(grupo de controle|grupo de tratamento|randomiza[cç][aã]o|avalia[cç][aã]o de impacto|[aá]rvore do problema|diagn[oó]stico de um problema|ciclo das pol[ií]ticas|constru[cç][aã]o de agenda|monitoramento.*processo cont[ií]nuo|teoria do equil[ií]brio pontuado)","Políticas públicas","Avaliação e ciclo de políticas","Diagnóstico, desenho, avaliação e monitoramento","identificar ou avaliar","etapa ou método de análise e avaliação de política pública","aplicação conceitual","media"),
 (r"(reforma da previd[eê]ncia|or[cç]amento sens[ií]vel|mercado de trabalho|ocupa[cç][oõ]es informais|desigualdade|agricultura familiar|mudan[cç]as clim[aá]ticas|combust[ií]veis f[oó]sseis|coleta de esgoto|[aá]gua tratada|sistema prisional|pluralismo pol[ií]tico)","Realidade brasileira","Sociedade, economia e políticas sociais","Indicadores sociais e temas contemporâneos","analisar","afirmação sobre fenômeno social ou política brasileira","interpretação contextual","baixa"),
 (r"(c[oó]digo.*execu[cç][aã]o|vari[aá]vel x|sinal de cerquilha|coment[aá]rio.*linha|linguagem r|int x:|intelig[eê]ncia artificial)","Tecnologia da informação","Programação e inteligência artificial","Fundamentos de programação e IA","interpretar","efeito de código ou conceito computacional expresso","aplicação técnica","media"),
 (r"(vari[aá]veis qualitativas|categorias.*classifica[cç][aã]o dos indiv[ií]duos|dados abertos|atributo da inclus[aã]o|portal de dados)","Análise de dados","Dados e informação","Tipos de variáveis e dados abertos","identificar","propriedade de variável ou princípio de disponibilização de dados","interpretação conceitual","media"),
 (r"(perda por redu[cç][aã]o ao valor recuper[aá]vel|unidade geradora de caixa|reserva de reavalia[cç][aã]o|deprecia[cç][aã]o anual|valor recuper[aá]vel|provis[aã]o.*valor esperado|restitui[cç][aã]o.*tribut|caracter[ií]sticas qualitativas.*informa[cç][aã]o de custos|estoques.*menor valor|goodwill|contrato.*item n[aã]o financeiro|custo indireto de fabrica[cç][aã]o|mat[eé]ria-prima.*investimento|centro de custos|unidade.*modelo de gerenciamento de custos)","Contabilidade","Contabilidade patrimonial e de custos","Mensuração, impairment, provisões, estoques e custos","calcular ou aplicar","critério contábil ou valor de mensuração aplicável ao caso","aplicação contábil ou cálculo","media"),
 (r"(prazo m[aá]ximo de restri[cç][aã]o de acesso|lei n[ºo.]?\s*12\.527|lei de acesso [àa] informa[cç][aã]o|classifica[cç][aã]o de informa[cç][aã]o|sisp|sistema de administra[cç][aã]o dos recursos de tecnologia|decreto n[ºo.]?\s*7\.579|pol[ií]tica de tecnologia da informa[cç][aã]o|identifica[cç][aã]o digital)","Administração pública","Governo digital e transparência","Acesso à informação e governança de TIC","aplicar","regra de acesso à informação ou de governança de tecnologia pública","interpretação normativa","media"),
 (r"(modelo de desenvolvimento de solow|keynesian|cl[aá]ssic|demanda agregada|produto e o n[ií]vel de pre[cç]os|economia apresenta propriedades)","Economia","Macroeconomia","Modelos keynesiano e clássico","analisar","efeito de política ou variável sobre produto e preços","análise econômica","media"),
 (r"(governan[cç]a p[uú]blica|capacidade de governan[cç]a|referencial b[aá]sico de governan[cç]a|accountability|transpar[eê]ncia|prestac[aã]o de contas|controle externo|tribunal de contas|tcu)","Administração pública","Governança, controle e accountability","Mecanismos de direção e controle público","identificar ou avaliar","princípio, competência ou mecanismo de governança pública","interpretação conceitual ou normativa","media"),
 (r"(modelo de gest[aã]o (?:burocr[aá]tica|patrimonialista|gerencial)|administra[cç][aã]o p[uú]blica brasileira|reforma gerencial|burocracia|capacidade administrativa do estado|soberania|agentes pol[ií]ticos)","Administração pública","Estado e modelos de gestão","Evolução do Estado e modelos administrativos","distinguir","características do modelo estatal ou administrativo descrito","interpretação conceitual","media"),
 (r"(agente p[uú]blico|servidor p[uú]blico|ministro de estado|poder regulamentar|abuso de poder|excesso de poder|ato administrativo|administra[cç][aã]o direta|licen[cç]a.*ato|princ[ií]pio licitat[oó]rio|vincula[cç][aã]o ao edital|segrega[cç][aã]o de fun[cç][oõ]es)","Direito Público","Direito administrativo","Agentes, atos, poderes e licitações","aplicar","regra ou característica do instituto administrativo descrito","interpretação normativa","media"),
 (r"(federalismo|descentraliza[cç][aã]o de pol[ií]ticas|distrito federal|quinto constitucional|poder judici[aá]rio|poder legislativo|presidente da rep[uú]blica|organiza[cç][aã]o federativa|compet[eê]ncia do judici[aá]rio)","Direito Público","Direito constitucional","Organização do Estado e dos Poderes","aplicar","regra constitucional de competência, organização ou controle","interpretação normativa","media"),
 (r"(governo digital|digitaliza[cç][aã]o.*administra[cç][aã]o|burocrata de n[ií]vel|tomada de decis[aã]o|implementa[cç][aã]o de pol[ií]ticas|colabora[cç][aã]o p[uú]blico[- ]privada|parceria p[uú]blico[- ]privada|governan[cç]a e gest[aã]o p[uú]blica)","Administração pública","Governança e implementação","Capacidades estatais, decisão e colaboração","analisar","capacidade ou mecanismo de implementação pública descrito","interpretação conceitual","media"),
 (r"(realidade pol[ií]tica|realidade econ[oô]mica|realidade social|realidade ambiental|estrutura fundi[aá]ria|agricultura familiar|amaz[oô]nia legal|informalidade ocupacional|saneamento b[aá]sico|transi[cç][aã]o energ[eé]tica|g20|g7|mercado de trabalho|pol[ií]tica partid[aá]ria)","Realidade brasileira","Sociedade, economia, política e ambiente","Indicadores e desafios contemporâneos do Brasil","interpretar","afirmação contextual sobre a realidade brasileira","interpretação de conteúdo e dados","baixa"),
 (r"(princ[ií]pios.*lei n\.?(?:º|\s)?\s*9\.784|processo administrativo|regime disciplinar|suspens[aã]o.*servidor|improbidade administrativa|conduta do servidor)","Ética no setor público","Integridade e regime de servidores","Normas de conduta e processo administrativo","aplicar","princípio ou consequência normativa para agente público","interpretação normativa","media"),
 (r"(regress[aã]o|correla[cç][aã]o|desvio[- ]padr[aã]o|mediana|quartil|vari[aâ]ncia|amostra|hip[oó]tese estat[ií]stica)","Análise de dados","Estatística","Análise estatística de dados","interpretar","medidas, associações ou resultados estatísticos","interpretação quantitativa","media"),
 (r"(anonimiza[cç][aã]o|dado pessoal|lgpd|controlador|operador de dados|base legal|tratamento de dados)","Análise de dados","Governança de dados","Proteção de dados pessoais","identificar","regras de tratamento e proteção de dados pessoais","aplicação conceitual","media"),
 (r"(sql|banco de dados|data warehouse|etl|minera[cç][aã]o de dados|aprendizado de m[aá]quina|classificador|acur[aá]cia|precis[aã]o e revoca[cç][aã]o)","Análise de dados","Tecnologia e análise de dados","Dados, modelos ou consulta","analisar","estrutura, consulta ou desempenho de solução de dados","aplicação técnica","media"),
 (r"(direitos humanos|declara[cç][aã]o universal|conven[cç][aã]o|discrimina[cç][aã]o racial|estatuto da igualdade racial|refugiados)","Direitos Humanos","Proteção internacional e igualdade","Instrumentos e garantias de direitos humanos","identificar","alcance de instrumento ou garantia de direitos humanos","interpretação normativa","media"),
 (r"(constitui[cç][aã]o federal|direito fundamental|direitos e garantias fundamentais|poder constituinte|controle de constitucionalidade|organiza[cç][aã]o do estado)","Direito Público","Direito constitucional","Constituição e direitos fundamentais","aplicar","norma constitucional ao caso apresentado","interpretação normativa","media"),
 (r"(ato administrativo|licita[cç][aã]o|contrato administrativo|servidor p[uú]blico|improbidade|responsabilidade civil do estado|poder de pol[ií]cia|descentraliza[cç][aã]o administrativa)","Direito Público","Direito administrativo","Regime jurídico-administrativo","aplicar","instituto ou regra de direito administrativo ao caso","interpretação normativa","media"),
 (r"(tribut[aá]ri|imposto|taxa|contribui[cç][aã]o de melhoria|cr[eé]dito tribut[aá]rio|obriga[cç][aã]o tribut[aá]ria|compet[eê]ncia tribut[aá]ria|lan[cç]amento tribut[aá]rio)","Direito Público","Direito tributário","Tributos e obrigação tributária","aplicar","regra tributária à situação descrita","interpretação normativa","media"),
 (r"(or[cç]amento p[uú]blico|or[cç]ament[aá]ri|cr[eé]dito adicional|lei 4\.320|loa|ppa|ldo|empenho|liquida[cç][aã]o da despesa|restos a pagar|receita corrente|receita de capital)","Planejamento e orçamento público","Orçamento público","Ciclo, classificações e execução orçamentária","identificar","regra, estágio ou classificação orçamentária aplicável","interpretação normativa","media"),
 (r"(responsabilidade fiscal|relat[oó]rio de gest[aã]o fiscal|anexo de riscos fiscais|limite de despesa com pessoal|resultado prim[aá]rio|d[ií]vida consolidada|ren[uú]ncia de receita)","Finanças públicas","Responsabilidade fiscal","Regras fiscais e demonstrativos","interpretar","limite, demonstrativo ou regra de responsabilidade fiscal","interpretação normativa","media"),
 (r"(pol[ií]tica p[uú]blica|avalia[cç][aã]o ex[- ]?(ante|post)|grupo de tratamento|indicador de impacto|teoria do equil[ií]brio pontuado|ciclo de pol[ií]ticas|abordagem estadoc[eê]ntrica|multic[eê]ntrica)","Políticas públicas","Formulação e avaliação","Modelos, atores e avaliação de políticas","analisar","modelo ou método de análise de política pública","interpretação conceitual","media"),
 (r"(indicador|metas?|efici[eê]ncia|efic[aá]cia|efetividade|gest[aã]o para resultados|ppa 20\d\d|planejamento estrat[eé]gico)","Planejamento governamental","Gestão para resultados","Indicadores, metas e desempenho","interpretar","relação entre indicador, meta e resultado governamental","interpretação conceitual","media"),
 (r"(parceria p[uú]blico[- ]privada|concess[aã]o|fundo estadual|fecop|opera[cç][aã]o de cr[eé]dito|alian[cç]a com o setor privado)","Gestão pública","Arranjos de implementação","Parcerias e instrumentos de financiamento","avaliar","condições legais ou institucionais do arranjo descrito","interpretação normativa","media"),
 (r"(bpmn|scrum|sprint|design thinking|sistema de informa[cç][aã]o|identifica[cç][aã]o digital|compartilhamento de dados|pol[ií]tica de tecnologia da informa[cç][aã]o|infraestrutura de tic|processo de aquisi[cç][aã]o.*tic)","Governança e gestão de TIC","Processos, métodos e governança de tecnologia","Modelagem, métodos ágeis e governança de TIC","identificar ou aplicar","elemento, regra ou prática do processo de tecnologia descrito","aplicação técnica ou normativa","media"),
 (r"(elasticidade[- ]pre[cç]o|elasticidade da demanda|equil[ií]brio de mercado|excedente do consumidor|pareto|externalidade|bem p[uú]blico|monop[oó]lio|concorr[eê]ncia perfeita)","Economia","Microeconomia","Mercados, eficiência e falhas de mercado","analisar","equilíbrio ou efeito econômico no cenário apresentado","análise econômica","media"),
 (r"(multiplicador monet[aá]rio|base monet[aá]ria|agregado monet[aá]rio|modelo de solow|crescimento econ[oô]mico|infla[cç][aã]o|plano de metas|balan[cç]o de pagamentos|taxa de c[aâ]mbio)","Economia","Macroeconomia","Moeda, crescimento e setor externo","analisar","efeito de variável macroeconômica sobre o resultado indicado","análise econômica","media"),
 (r"(reconhecimento|mensura[cç][aã]o|evidencia[cê]ncia|varia[cç][aã]o patrimonial|ativo imobilizado|passivo|receita sem contrapresta[cç][aã]o|mcasp|plano de contas|demonstra[cç][oõ]es cont[aá]beis)","Contabilidade","Contabilidade pública","Reconhecimento e mensuração patrimonial","aplicar","critério contábil ao fato ou fluxo de registros descrito","aplicação contábil","media"),
 (r"(custo vari[aá]vel|custeio por absor[cç][aã]o|custeio vari[aá]vel|margem de contribui[cç][aã]o|ponto de equil[ií]brio|rateio|custo indireto)","Contabilidade","Contabilidade de custos","Classificação e métodos de custeio","calcular ou classificar","custo, margem ou resultado conforme o método indicado","cálculo ou classificação","media"),
 (r"(simples nacional|lucro real|lucro presumido|icms|iss|itd|ipva|ipi|pis|cofins|irpj|csll|substitui[cç][aã]o tribut[aá]ria)","Direito Público","Legislação tributária","Tributos e regimes de apuração","aplicar","regra do tributo ou regime fiscal ao caso apresentado","interpretação normativa","media"),
 (r"(custos? dos servi[cç]os p[uú]blicos|sistema de informa[cç][oõ]es de custos|economicidade|custo do servi[cç]o|siafi)","Contabilidade","Custos no setor público","Sistema de custos e economicidade","avaliar","informação de custo ou dimensão de desempenho público","aplicação contábil","media"),
 (r"(interpreta[cç][aã]o de texto|sentido de|voc[aá]bulo|sin[oô]nimo|substitui[cç][aã]o de|refer[eê]ncia do pronome|conectivo|pontua[cç][aã]o|concord[aâ]ncia|reg[eê]ncia|lacunas? das linhas)","Língua Portuguesa","Compreensão e gramática","Sentido, coesão e correção linguística","interpretar","sentido ou emprego linguístico no contexto textual","análise linguística","media"),
 (r"(according to the text|according to the passage|the text|the passage|in the context|synonym|meaning of|it can be inferred|the author)","Língua Inglesa","Compreensão textual","Inferência e sentido contextual","inferir","informação ou sentido expresso no texto em inglês","leitura em língua estrangeira","media"),
 (r"(seg[uú]n el texto|de acuerdo con el texto|el texto|el autor|se puede inferir|significado de|en el contexto)","Língua Espanhola","Compreensão textual","Inferência e sentido contextual","inferir","informação ou sentido expresso no texto em espanhol","leitura em língua estrangeira","media"),
 (r"(n[uú]mero primo|conjunto|subconjunto|probabilidade|permut[aá]|combina[cç][aã]o|l[oó]gica proposicional|tautologia|equival[eê]ncia l[oó]gica|divisores)","Raciocínio lógico-matemático","Lógica, conjuntos e probabilidade","Propriedades e operações formais","resolver","propriedade lógica, cardinalidade ou probabilidade solicitada","raciocínio formal ou cálculo","media"),
 (r"(regress[aã]o|vari[aâ]ncia|m[eé]dia aritm[eé]tica|mediana|probabilidade|amostra|coeficiente|tabela|gr[aá]fico|crescimento da popula[cç][aã]o|taxa de natalidade)","Análise quantitativa","Estatística e leitura de dados","Cálculo ou interpretação de dados","interpretar ou calcular","medida ou tendência apresentada em dados","raciocínio quantitativo","baixa"),
]

def norm(s): return re.sub(r"\s+"," ",s or "").strip()
def evidence(text, match):
 a=max(0,match.start()-80); b=min(len(text),match.end()+130)
 return norm(text[a:b])[:220]

def classify(q):
 stem=norm(q.get("enunciado_original")); alts=" ".join(a.get("texto","") for a in q.get("alternativas",[]) if isinstance(a,dict))
 full=norm(" ".join((stem,alts,q.get("texto_original_completo", ""))))
 # suppress duplicated, OCR-polluted original discipline labels; use only as a
 # strong prior for Fundatec section identifiers printed in the source.
 doc=q["documento_id"]
 disc=q.get("disciplina_original") or ""
 fundatec_prior=None
 if doc=="doc_97655bcdd13752ea40eb":
  code=re.search(r"477_(LP|RL|DAC|GG|EFP|OP|PLAN)_",disc)
  fundatec_prior={"LP":"Língua Portuguesa","RL":"Raciocínio lógico-matemático","DAC":"Direito Administrativo e Constitucional","GG":"Governança e Gestão","EFP":"Economia e Finanças Públicas","OP":"Orçamento Público","PLAN":"Planejamento e Políticas Públicas"}.get(code.group(1)) if code else None
  if disc=="PROVA DISSERTATIVA": fundatec_prior="Planejamento e Gestão Pública"
 # Use a textual rule first. An explicitly identified Fundatec section only
 # supplies discipline when no more specific lexical rule matched.
 for pat,d,a,s,act,obj,demand,conf in RULES:
  m=re.search(pat,full,re.I)
  if not m: continue
  if fundatec_prior and d in {"Raciocínio lógico-matemático","Língua Portuguesa","Direito Público","Economia","Planejamento e orçamento público"}:
   d=fundatec_prior
  phrase=evidence(full,m)
  return [{"disciplina":d,"assunto":a,"subassunto":s,"papel":"conteudo_avaliado","trecho_evidencia":phrase,"origem":ORIGIN,"confianca":conf}], [{"descricao_operacional":f"{act.capitalize()} {obj}.","acao":act,"objeto_conhecimento":obj,"tipo_demanda":demand,"papel":"demanda_cognitiva_inferida","trecho_evidencia":phrase,"origem":ORIGIN,"confianca":conf}]
 # No caderno MPO P1 as questões 1–5 e 6–10 correspondem a inglês e espanhol.
 # A associação decorre do bloco impresso e do intervalo contíguo de cada idioma.
 if doc=="doc_0f507fed95bdb203fb43":
  n=str(q.get("numero_original", ""))
  language="Língua Inglesa" if n in {"1","2","3","4","5"} else ("Língua Espanhola" if n in {"6","7","8","9","10"} else None)
  if language:
   phrase=norm(stem)[:220]
   return [{"disciplina":language,"assunto":"Compreensão textual","subassunto":"Avaliação de proposições sobre texto-base","papel":"conteudo_avaliado","trecho_evidencia":phrase,"origem":ORIGIN,"confianca":"baixa"}], [{"descricao_operacional":"Inferir do texto-base se a afirmação proposta é compatível com a informação apresentada.","acao":"inferir","objeto_conhecimento":"proposições sobre texto-base em língua estrangeira","tipo_demanda":"leitura em língua estrangeira","papel":"demanda_cognitiva_inferida","trecho_evidencia":phrase,"origem":ORIGIN,"confianca":"baixa"}]
 if fundatec_prior:
  return ([{"disciplina":fundatec_prior,"assunto":fundatec_prior,"subassunto":None,"papel":"disciplina_identificada_no_caderno","trecho_evidencia":norm(disc),"origem":ORIGIN,"confianca":"baixa"}],[])
 return [],[]

def main():
 rows=[json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
 out=[]; counts={}; pending=[]
 for q in rows:
  cls,skills=classify(q)
  record={"documento_id":q["documento_id"],"numero_original":q["numero_original"],"classificacoes":cls,"habilidades":skills}
  out.append(json.dumps(record,ensure_ascii=False))
  key=q["documento_id"]; c=counts.setdefault(key,{"total":0,"classificadas":0,"com_habilidade":0,"pendentes":[]})
  c["total"]+=1
  if cls:c["classificadas"]+=1
  if skills:c["com_habilidade"]+=1
  if not cls or not skills:c["pendentes"].append(q["numero_original"])
 TARGET.write_text("\n".join(out)+"\n",encoding="utf-8")
 report={"metodo":ORIGIN,"regras":len(RULES),"total_registros":len(out),"documentos":counts,
  "nota":"Heurística contextual por padrões explícitos; confiança baixa ou média não é probabilidade calibrada. Nenhum rótulo padrão foi preenchido nos itens sem evidência suficiente; eles aparecem nas listas pendentes.",
  "campos_pendentes":"classificacoes ou habilidades vazias quando a regra não encontrou evidência textual específica."}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"total":len(out),"documentos":{k:{x:v for x,v in c.items() if x!="pendentes"} for k,c in counts.items()},"pendentes":sum(len(c["pendentes"]) for c in counts.values())},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
