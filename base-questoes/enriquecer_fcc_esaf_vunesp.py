#!/usr/bin/env python3
"""Enriquecimento conservador por regras explícitas; pendências permanecem vazias."""
from __future__ import annotations
import json,re
from pathlib import Path
from collections import Counter

BASE=Path(__file__).resolve().parent
RUN=BASE/"execucoes"/"2026-10-29"
SRC=RUN/"lotes"/"fcc_esaf_vunesp.questoes.jsonl"
OUT=RUN/"lotes"/"fcc_esaf_vunesp.enriquecimento.jsonl"
ORIGIN="heuristica_regras_luna"

def rule(pattern,disc,subject,sub,action,obj,demand,desc,confidence="media"):
    return (re.compile(pattern,re.I|re.S),disc,subject,sub,action,obj,demand,desc,confidence)

# Esquema conceitual estreito, com evidência textual no próprio enunciado.
RULES=[
 rule(r"crase|sinal indicativo de crase", "Língua Portuguesa","Morfossintaxe","Crase","identificar","emprego do sinal indicativo de crase","identificar","Identificar a construção em que a crase é exigida ou vedada."),
 rule(r"concordância (?:verbal|nominal)|concordância", "Língua Portuguesa","Morfossintaxe","Concordância","aplicar","concordância verbal e nominal","aplicar","Aplicar regras de concordância ao período apresentado."),
 rule(r"regência (?:verbal|nominal)|regência", "Língua Portuguesa","Morfossintaxe","Regência","aplicar","regência verbal e nominal","aplicar","Relacionar a regência do termo à preposição exigida no contexto."),
 rule(r"pontua(?:ção|ção)|vírgula|dois-pontos|ponto e vírgula", "Língua Portuguesa","Morfossintaxe","Pontuação","interpretar","emprego e efeito de sinais de pontuação","interpretar","Interpretar ou corrigir a pontuação de um trecho conforme sua estrutura sintática."),
 rule(r"colocação pronominal|próclise|ênclise|mesóclise", "Língua Portuguesa","Morfossintaxe","Colocação pronominal","identificar","posição dos pronomes átonos","identificar","Identificar a colocação pronominal adequada à construção apresentada."),
 rule(r"sinônimo|antônimo|sentido (?:próprio|figurado)|conotação|denotação", "Língua Portuguesa","Semântica","Sentido lexical","interpretar","sentido de palavra ou expressão em contexto","interpretar","Interpretar o sentido contextual de palavra ou expressão."),
 rule(r"figura(?:s)? de linguagem|metáfora|metonímia|ironia", "Língua Portuguesa","Semântica","Figuras de linguagem","identificar","recurso expressivo do texto","identificar","Identificar o recurso expressivo empregado no trecho."),
 rule(r"de acordo com (?:o|esse|este) texto|segundo (?:o|esse|este) texto|(?:infere-se|depreende-se) (?:do|que)|(?:o|a) autor(?:a)? (?:afirma|defende|sustenta|argumenta|conclui|considera)|ideia central|tese (?:defendida|do texto)|principal objetivo do texto", "Língua Portuguesa","Compreensão e interpretação","Inferência textual","interpretar","ideias, relações e inferências do texto","interpretar","Inferir a conclusão ou relação argumentativa sustentada pelo texto.","baixa"),

 rule(r"créditos? (?:suplementares?|especiais?|extraordinários?)|abertura de créditos", "Administração Financeira e Orçamentária","Execução orçamentária","Créditos adicionais","aplicar","regras de abertura e fonte de créditos adicionais","aplicar","Aplicar regras de créditos adicionais aos dados orçamentários apresentados."),
 rule(r"restos a pagar", "Administração Financeira e Orçamentária","Execução orçamentária","Restos a pagar","classificar","inscrição, processamento ou pagamento de restos a pagar","classificar","Classificar a situação da despesa quanto a restos a pagar."),
 rule(r"empenho|liquidação|liquidar|pagamento da despesa", "Administração Financeira e Orçamentária","Execução da despesa","Estágios da despesa","distinguir","empenho, liquidação e pagamento","distinguir","Distinguir os estágios da despesa pública na situação descrita."),
 rule(r"previsão.{0,30}arrecadação|lançamento.{0,30}receita|recolhimento da receita|receita pública", "Administração Financeira e Orçamentária","Execução da receita","Estágios e classificação da receita","classificar","estágios ou natureza da receita pública","classificar","Classificar a receita pública conforme seu estágio ou natureza descritos."),
 rule(r"lei de diretrizes orçamentárias|\bLDO\b|lei orçamentária anual|\bLOA\b|plano plurianual|\bPPA\b", "Administração Financeira e Orçamentária","Planejamento e orçamento","Instrumentos de planejamento","distinguir","PPA, LDO e LOA","distinguir","Distinguir a função e o conteúdo do instrumento de planejamento citado."),
 rule(r"orçamento-programa|orçamento participativo|orçamento base zero|princípios orçamentários", "Administração Financeira e Orçamentária","Orçamento público","Técnicas e princípios orçamentários","identificar","técnica ou princípio orçamentário","identificar","Identificar a técnica ou o princípio orçamentário aplicável ao caso."),
 rule(r"receita corrente líquida|\bRCL\b|despesa com pessoal|limite.{0,30}pessoal", "Direito Financeiro e Finanças Públicas","Responsabilidade fiscal","Limites fiscais","calcular","RCL e limites de despesa com pessoal","calcular","Calcular ou verificar o limite fiscal de pessoal com os valores informados."),
 rule(r"precatório|requisição de pequeno valor|\bRPV\b", "Direito Financeiro e Finanças Públicas","Dívida pública","Precatórios","aplicar","regime constitucional de precatórios e RPV","aplicar","Aplicar a regra de pagamento ou classificação de precatório ao caso."),
 rule(r"necessidade de financiamento do setor público|resultado primário|resultado nominal|dívida pública", "Finanças Públicas","Resultado fiscal e dívida","Indicadores fiscais","calcular","resultado fiscal ou trajetória da dívida pública","calcular","Calcular ou interpretar o indicador fiscal descrito no enunciado."),

 rule(r"valor presente líquido|\bVPL\b|taxa interna de retorno|\bTIR\b", "Matemática Financeira","Avaliação de investimentos","VPL e TIR","calcular","valor presente líquido ou taxa interna de retorno","calcular","Avaliar o investimento por VPL ou TIR a partir dos fluxos e da taxa informados."),
 rule(r"juros compostos|capitalização composta|montante.{0,30}juros", "Matemática Financeira","Regimes de capitalização","Juros compostos","calcular","montante, juros e taxa em capitalização composta","calcular","Calcular montante ou juros sob capitalização composta."),
 rule(r"juros simples|capitalização simples", "Matemática Financeira","Regimes de capitalização","Juros simples","calcular","montante, juros e taxa em capitalização simples","calcular","Calcular montante ou juros sob capitalização simples."),
 rule(r"sistema (?:francês|price)|sistema de amortização constante|\bSAC\b|tabela price", "Matemática Financeira","Amortização","Sistemas de amortização","calcular","prestação, saldo ou amortização de financiamento","calcular","Calcular uma prestação, amortização ou saldo pelo sistema indicado."),
 rule(r"elasticidade (?:preço|renda|cruzada)|elasticidade da demanda|elasticidade da oferta", "Economia","Microeconomia","Elasticidades","calcular","elasticidade-preço, renda ou cruzada","calcular","Calcular ou interpretar a elasticidade indicada com base nas variações informadas."),
 rule(r"curva de demanda|curva de oferta|equilíbrio de mercado|preço de equilíbrio", "Economia","Microeconomia","Oferta, demanda e equilíbrio","analisar","deslocamentos de oferta e demanda e equilíbrio de mercado","analisar","Determinar como a mudança descrita altera oferta, demanda ou equilíbrio."),
 rule(r"externalidade|bens públicos|falha de mercado|monopólio natural", "Economia","Microeconomia","Falhas de mercado","analisar","falha de mercado e resposta econômica","analisar","Analisar a falha de mercado identificada e seus efeitos econômicos."),
 rule(r"produto interno bruto|\bPIB\b|contas nacionais|agregados macroeconômicos", "Economia","Macroeconomia","Contas nacionais e produto","calcular","produto, renda ou agregado macroeconômico","calcular","Calcular ou interpretar o agregado macroeconômico solicitado."),
 rule(r"inflação|curva de phillips|índice de preços", "Economia","Macroeconomia","Inflação e preços","interpretar","inflação, nível de preços e mercado de trabalho","interpretar","Interpretar o efeito da inflação ou da variação de preços no cenário apresentado."),
 rule(r"modelo IS.?LM|mundell.?fleming|política monetária|política fiscal", "Economia","Macroeconomia","Modelos e políticas macroeconômicas","analisar","equilíbrio macroeconômico sob política monetária ou fiscal","analisar","Analisar a mudança de equilíbrio causada pela política indicada."),
 rule(r"probabilidade condicional|teorema de bayes|variável aleatória|distribuição (?:normal|binomial|poisson)", "Estatística","Probabilidade","Probabilidade e distribuições","calcular","probabilidade ou parâmetro de distribuição","calcular","Calcular a probabilidade solicitada a partir da distribuição ou condição informada."),
 rule(r"amostragem|amostra aleatória|intervalo de confiança|estimação pontual", "Estatística","Inferência estatística","Amostragem e estimação","aplicar","plano amostral ou estimativa estatística","aplicar","Selecionar ou interpretar o procedimento de amostragem ou estimação adequado."),
 rule(r"hipótese nula|hipóteses? estatísticas?|valor.?p|erro tipo i|erro tipo ii|análise de variância|\bANOVA\b", "Estatística","Inferência estatística","Testes de hipóteses","interpretar","hipótese estatística, erro e valor-p","interpretar","Interpretar o resultado do teste e a decisão estatística correspondente."),
 rule(r"regressão linear|correlação|covariância|série temporal|\bARIMA\b", "Estatística","Modelagem estatística","Regressão, associação e séries temporais","analisar","relação entre variáveis ou comportamento temporal","analisar","Analisar a associação entre variáveis ou a estrutura da série apresentada."),

 rule(r"crédito tributário|obrigação tributária|lançamento tributário|código tributário nacional|\bCTN\b", "Direito Tributário","Obrigação e crédito tributário","Lançamento e crédito tributário","aplicar","regras do CTN sobre obrigação, lançamento ou crédito","aplicar","Aplicar a regra tributária indicada à situação descrita."),
 rule(r"ICMS|IPTU|IPVA|ISSQN|\bISS\b|IPI|ITBI|ITCMD", "Direito Tributário","Tributos","Impostos e incidência","identificar","incidência, competência ou característica do imposto citado","identificar","Identificar a regra de incidência ou competência do imposto referido."),
 rule(r"imunidade tributária|competência tributária|poder de tributar|limita(?:ção|ções) ao poder de tributar", "Direito Tributário","Sistema Tributário Nacional","Competência e limitações","distinguir","competência tributária, imunidade ou limitação","distinguir","Distinguir a competência ou limitação tributária aplicável ao caso."),
 rule(r"execução fiscal|dívida ativa|certidão (?:negativa|positiva)", "Direito Tributário","Administração tributária","Dívida ativa e cobrança","aplicar","inscrição, certidão ou cobrança da dívida ativa","aplicar","Aplicar a regra de inscrição ou cobrança da dívida ativa à situação apresentada."),
 rule(r"licita(?:ção|ções)|pregão|concorrência pública|lei nº? 14\.133", "Direito Administrativo","Licitações e contratos","Procedimento licitatório","aplicar","modalidade, fase ou regra de licitação pública","aplicar","Aplicar a regra de licitação ou contratação pública ao caso."),
 rule(r"ato administrativo|poder de polícia|poder regulamentar|poder hierárquico", "Direito Administrativo","Atos e poderes administrativos","Regime dos atos e poderes","distinguir","atributo, extinção ou poder administrativo","distinguir","Distinguir o atributo, a forma de extinção ou o poder administrativo pertinente."),
 rule(r"improbidade administrativa|agente público|servidor público|processo administrativo disciplinar", "Direito Administrativo","Agentes e responsabilização","Regime de agentes públicos","aplicar","deveres, responsabilização ou processo disciplinar","aplicar","Aplicar o regime jurídico do agente ou da responsabilização administrativa."),
 rule(r"controle constitucional|ação direta de inconstitucionalidade|\bADI\b|art(?:igo)?s?\.?\s*37", "Direito Constitucional","Constituição e controle","Normas e controle constitucional","aplicar","norma constitucional ou instrumento de controle","aplicar","Aplicar a norma constitucional ou o instrumento de controle indicado."),
 rule(r"direitos e garantias fundamentais|mandado de segurança|habeas corpus|habeas data", "Direito Constitucional","Direitos fundamentais","Garantias e remédios constitucionais","identificar","direito fundamental ou remédio constitucional","identificar","Identificar o direito ou remédio constitucional adequado ao caso."),
 rule(r"sistema tributário nacional|repartição (?:das )?receitas tributárias|art(?:igo)?s?\.? 157 a 162", "Direito Constitucional","Organização tributária","Repartição de receitas","aplicar","competência e repartição constitucional de receitas","aplicar","Aplicar as regras constitucionais de repartição de receitas ao ente indicado."),
 rule(r"constituição federal.{0,40}orçamento|processo legislativo orçamentário|regra de ouro", "Direito Financeiro","Orçamento constitucional","PPA, LDO, LOA e vedações","aplicar","disciplina constitucional do orçamento","aplicar","Aplicar a regra constitucional orçamentária ao procedimento ou situação apresentados."),
 rule(r"seguridade social|regime próprio de previdência|\bRPPS\b|salário de contribuição|benefício previdenciário", "Direito Previdenciário","Regimes e benefícios","Seguridade e previdência","distinguir","regime, beneficiário ou benefício previdenciário","distinguir","Distinguir o regime ou benefício previdenciário aplicável à situação."),
 rule(r"código penal|crime contra a administração|peculato|falsidade documental|crime contra o sistema financeiro", "Direito Penal","Crimes em espécie","Crimes contra a Administração ou ordem econômica","identificar","elementos ou enquadramento do crime descrito","identificar","Identificar os elementos do tipo penal descrito no enunciado."),
 rule(r"direito do trabalho|jornada de trabalho|horas extras|justa causa|reclamação trabalhista", "Direito do Trabalho","Relação e processo do trabalho","Normas trabalhistas","aplicar","regra material ou processual trabalhista","aplicar","Aplicar a regra trabalhista pertinente à situação apresentada."),

 rule(r"procedimentos de auditoria|papéis de trabalho|evidências de auditoria|amostragem estatística|pareceres? de auditoria", "Auditoria","Procedimentos e evidências","Auditoria e documentação","analisar","procedimento, evidência ou documentação de auditoria","analisar","Avaliar qual procedimento ou evidência de auditoria atende ao objetivo descrito."),
 rule(r"análise das demonstrações|índice de liquidez|índice de endividamento|quociente patrimonial", "Contabilidade","Análise das demonstrações","Indicadores contábeis","calcular","índice ou quociente a partir das demonstrações","calcular","Calcular ou interpretar o indicador contábil com os dados apresentados."),
 rule(r"demonstração dos fluxos de caixa|fluxo de caixa das atividades|\bDFC\b", "Contabilidade","Demonstrações contábeis","Fluxos de caixa","classificar","fluxos de caixa operacionais, de investimento ou financiamento","classificar","Classificar o fluxo de caixa na atividade contábil adequada."),
 rule(r"demonstração do resultado|\bDRE\b|lucro líquido|resultado do exercício", "Contabilidade","Demonstrações contábeis","Resultado do exercício","calcular","receita, custo, despesa ou resultado contábil","calcular","Apurar a rubrica ou o resultado solicitado a partir dos dados contábeis."),
 rule(r"depreciação|amortização|impairment|ativo imobilizado", "Contabilidade","Ativo não circulante","Mensuração e depreciação","calcular","mensuração contábil de ativo e despesa de depreciação","calcular","Calcular o valor contábil ou a despesa de depreciação do ativo."),
 rule(r"estoque|custo dos produtos vendidos|custeio por absorção|margem de contribuição|ponto de equilíbrio", "Contabilidade de Custos","Custos e estoques","Custeio e resultado","calcular","custo, estoque, margem ou ponto de equilíbrio","calcular","Calcular o custo ou indicador gerencial pelos dados do enunciado."),
 rule(r"partidas dobradas|lançamento contábil|escrituração contábil|débito e crédito", "Contabilidade","Escrituração","Partidas dobradas e lançamentos","aplicar","lançamento e efeito patrimonial da operação","aplicar","Registrar a operação pelo método das partidas dobradas e identificar seu efeito."),
 rule(r"ativo circulante|passivo circulante|patrimônio líquido|balanço patrimonial", "Contabilidade","Balanço patrimonial","Contas patrimoniais","classificar","classificação e mensuração de ativo, passivo ou patrimônio líquido","classificar","Classificar a conta ou apurar o saldo patrimonial com base nos dados fornecidos."),
 rule(r"ponto de equilíbrio|custo fixo|custo variável|custo marginal", "Economia","Custos de produção","Custos e escala de produção","calcular","custo fixo, variável, marginal ou ponto de equilíbrio","calcular","Calcular o custo ou nível de produção solicitado."),
 rule(r"\bSQL\b|banco de dados|consulta SQL|junção|\bJOIN\b", "Tecnologia da Informação","Banco de dados","Modelo relacional e SQL","interpretar","consulta, relação ou operação em banco de dados","interpretar","Interpretar a consulta ou estrutura de banco de dados descrita."),
 rule(r"Power BI|Power Query|\bDAX\b|dashboard|indicadores de BI", "Tecnologia da Informação","Business Intelligence","Modelagem e visualização de dados","aplicar","transformação, medida ou visualização em ferramenta de BI","aplicar","Aplicar a função de transformação, medida ou visualização descrita."),
 rule(r"segurança da informação|criptografia|firewall|\bVPN\b|ataque|vulnerabilidade|incidente de segurança", "Tecnologia da Informação","Segurança da informação","Controles e incidentes","analisar","ameaça, controle ou resposta a incidente de segurança","analisar","Analisar o controle ou resposta adequada à ameaça descrita."),
 rule(r"algoritmo|programação|estrutura de dados|python|javascript|código-fonte", "Tecnologia da Informação","Programação","Lógica e desenvolvimento de sistemas","aplicar","estrutura ou lógica de programação","aplicar","Aplicar a lógica de programação à entrada ou ao código apresentado.","baixa"),
]

ALT=re.compile(r"(?im)^\s*(?:\([A-Ea-e]\)|[A-Ea-e]\))\s*")

def focus_text(row):
    s=row.get("enunciado_original") or row.get("texto_original_completo") or ""
    m=ALT.search(s)
    if m:s=s[:m.start()]
    # Limit long shared passages; the item-specific end of the prompt carries
    # stronger evidence than incidental terms in the context.
    return s[-1400:]

def main():
    rows=[json.loads(x) for x in SRC.read_text(encoding="utf-8").splitlines() if x.strip()]
    output=[]; matched=Counter(); by_rule=Counter()
    for row in rows:
        focus=focus_text(row)
        classes=[]; skills=[]
        for rx,disc,subject,sub,action,obj,demand,desc,conf in RULES:
            m=rx.search(focus)
            if not m: continue
            evidence=m.group(0).strip()
            if len(evidence)>180:evidence=evidence[:177]+"..."
            classes.append({"disciplina":disc,"assunto":subject,"subassunto":sub,"papel":"central","trecho_evidencia":evidence,"origem":ORIGIN,"confianca":conf})
            skills.append({"descricao_operacional":desc,"acao":action,"objeto_conhecimento":obj,"tipo_demanda":demand,"papel":"central","trecho_evidencia":evidence,"origem":ORIGIN,"confianca":conf})
            matched[row["documento_id"]]+=1; by_rule[f"{disc} / {subject}"]+=1
            break
        output.append({"documento_id":row["documento_id"],"numero_original":row["numero_original"],"classificacoes":classes,"habilidades":skills})
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in output),encoding="utf-8")
    print(json.dumps({"questoes":len(rows),"com_classificacao_e_habilidade":sum(bool(x["classificacoes"]) for x in output),"pendentes":sum(not x["classificacoes"] for x in output),"por_documento":matched,"categorias":by_rule},ensure_ascii=False))

if __name__=="__main__":main()
