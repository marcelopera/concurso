"""Explicit topic vocabulary. Patterns are normalized (lowercase, no accents).

These rules generate auditable subject matches, not human-validated answers.
The main question command takes precedence over a text's incidental theme.
"""
import re
import unicodedata


def normalize(value):
    value = unicodedata.normalize('NFKD', value or '').lower()
    value = ''.join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r'\s+', ' ', value).strip()
    value = re.sub(r'\b([a-z]*?(?:fi|fl))\s+([a-z]+)',r'\1\2',value)
    return value


# Keys match the permanent lesson IDs. A phrase must occur in the question,
# never merely in the contest's title or in a candidate classification.
VOCABULARY = {
    'adm_01': [r'teoria.{0,25}(classica|humanistica|neoclassica|estruturalista|comportamental|sistemica|contingenc)', r'taylor',r'fayol',r'weber',r'chiavenato',r'funcoes (administrativas|do administrador)',r'processo administrativo',r'planejar,? organizar',r'principios da administracao cientifica',r'teoria das relacoes humanas'],
    'adm_02': [r'departamentaliza',r'estrutura.{0,20}(organizacional|matricial|funcional|linear|rede)',r'racionalidade limitada',r'(processo|tomada|modelo).{0,12}decis(ao|orio)',r'decisoes (programadas|nao programadas)',r'amplitude de (controle|comando)',r'centralizacao e descentralizacao'],
    'adm_03': [r'planejamento estrategico',r'analise swot',r'matriz swot',r'forcas de porter',r'cadeia de valor',r'\bokr\b',r'balanced scorecard',r'\bbsc\b',r'missao,? visao',r'estrategia organizacional',r'matriz (bcg|ansoff)'],
    'adm_04': [r'\bbpm\b',r'\bbpmn\b',r'pmbok',r'\bscrum\b',r'\bkanban\b',r'gestao (de|por) processos',r'gestao de projetos',r'mapeamento.{0,20}processos',r'ciclo de vida.{0,20}projeto',r'caminho critico',r'\bpert\b',r'(escopo|cronograma|stakeholders).{0,30}projeto',r'(projetos|processos).{0,40}(metodologia|gerenciamento|gestao)'],
    'adm_05': [r'motivacao',r'lideranca',r'comportamento organizacional',r'cultura organizacional',r'gestao (de|por) (pessoas|competencias)',r'recrutamento',r'avaliacao de desempenho.{0,30}(servidor|pessoa|funcionario)',r'treinamento e desenvolvimento',r'maslow',r'herzberg',r'mcgregor',r'clima organizacional',r'comunicacao organizacional'],
    'adm_06': [r'patrimonialismo',r'(modelo|administracao).{0,20}(patrimonialista|burocratic|gerencial)',r'new public management',r'nova gestao publica',r'accountability',r'governanca publica',r'governo eletronico',r'reforma.{0,25}(administrativ|estado)',r'estado regulador',r'controle social',r'governabilidade'],
    'adm_07': [r'organizacoes sociais',r'organizacao social',r'\boscips?\b',r'13[. ]?019',r'\bmrosc\b',r'contrato de gestao',r'consorcios? publicos?',r'politicas? publicas?',r'custo[ -]beneficio',r'custo[ -]efetividade',r'(eficiencia|eficacia|efetividade|economicidade).{0,50}(programa|gestao|indicador|public)',r'(avaliacao|indicadores).{0,30}(programa|desempenho)'],
    'adm_08': [r'auditoria (governamental|operacional|de conformidade|financeira|de gestao)',r'(instrumentos|tecnicas|procedimentos|tipos).{0,15}auditoria',r'achados? de auditoria',r'(evidencias?|materialidade|amostragem).{0,25}auditoria',r'auditor.{0,50}(evidencia|risco|amostragem|opiniao|relatorio|asseguracao)',r'(inspecao|levantamento|monitoramento|acompanhamento).{0,35}fiscalizacao'],
    'adm_09': [r'\bcoso\b',r'iso 31[. ]?000',r'gestao de riscos',r'gerenciamento de riscos',r'tres linhas',r'risco inerente',r'apetite a risco',r'matriz de riscos',r'risco de controle'],
    'adm_10': [r'\bippf\b',r'\bnbasp\b',r'\bnbc ta\b',r'ia[ -]cm',r'controle interno',r'auditoria interna',r'\biia\b',r'controladoria geral'],
    'adm_11': [r'programa.{0,5}de integridade',r'anticorrupcao',r'12[. ]?846',r'\besg\b',r'ouvidoria',r'(fraude|corrupcao).{0,30}(prevencao|risco|integridade)',r'codigo de etica',r'etica.{0,30}(public|servidor)',r'compliance'],
    'da_01': [r'fontes do direito administrativo',r'principios.{0,30}administracao publica',r'(principio da |principios de )(impessoalidade|moralidade|publicidade|supremacia|indisponibilidade|autotutela)',r'administracao (direta|indireta)',r'autarquias?',r'fundacoes? publicas?',r'empresas? publicas?',r'sociedades? de economia mista',r'orgaos? publicos?',r'desconcentracao',r'descentralizacao administrativa'],
    'da_02': [r'atos? administrativos?',r'autoexecutoriedade',r'imperatividade',r'presuncao de legitimidade',r'(anulacao|revogacao|cassacao|caducidade).{0,25}(ato|administrativ)',r'(ato|administrativ).{0,25}(anulacao|revogacao|cassacao|caducidade)'],
    'da_03': [r'convalidacao',r'decadencia administrativa',r'poder.{0,15}(policia|hierarquico|disciplinar|regulamentar|normativo)',r'abuso de poder',r'desvio de (poder|finalidade)',r'excesso de poder',r'discricionariedade',r'ato discricionario'],
    'da_04': [r'agentes? publicos?',r'servidores? publicos?',r'cargo publico',r'emprego publico',r'funcao publica',r'estagio probatorio',r'processo administrativo disciplinar',r'69[. ]?122',r'37 a 41',r'acumulacao de cargos',r'regime estatutario'],
    'da_05': [r'licitac',r'contratos? administrativos?',r'14[. ]?133',r'pregao',r'contratacao direta',r'dispensa.{0,15}licitacao',r'inexigibilidade',r'reequilibrio economico[ -]financeiro',r'servicos continuados'],
    'da_06': [r'servicos? publicos?',r'bens? publicos?',r'responsabilidade civil do estado',r'responsabilidade.{0,15}(objetiva|subjetiva)',r'concess(ao|oes)',r'permissao de servico',r'parcerias? publico[ -]privadas?',r'11[. ]?079',r'8[. ]?987'],
    'da_07': [r'improbidade',r'8[. ]?429',r'14[. ]?230',r'controle (judicial|administrativo|da administracao)',r'controle de (merito|legalidade)',r'acao popular'],
    'da_08': [r'lei de acesso a informacao',r'12[. ]?527',r'68[. ]?155',r'68[. ]?769',r'10[. ]?261',r'dados abertos',r'anticorrupcao',r'12[. ]?846',r'13[. ]?709',r'\blgpd\b'],
    'dc_01': [r'poder constituinte',r'(eficacia|aplicabilidade|interpretacao|hermeneutica).{0,25}(constitucional|constituicao|normas)',r'constituicao.{0,30}(classifica|rigida|flexivel|promulgada|outorgada)',r'normas constitucionais',r'mutacao constitucional'],
    'dc_02': [r'direitos? (e garantias )?fundamentais?',r'remedios? constitucionais?',r'habeas (corpus|data)',r'mandado de (seguranca|injuncao)',r'direitos? (individuais?|coletivos?|sociais?)',r'nacionalidade',r'direitos? politicos?',r'(liberdade|igualdade).{0,40}constituicao',r'acao popular'],
    'dc_03': [r'processo legislativo',r'poder (legislativo|executivo|judiciario)',r'competencia (privativa|concorrente|comum|legislativa|da uniao|dos estados|dos municipios)',r'tribuna(l|is) de contas',r'congresso nacional',r'controle externo',r'senado federal',r'organizacao (politico|do estado)',r'federacao',r'art(igo)?\.? ?(37|38|39|40|41|70|71|74)\b'],
    'dc_04': [r'art(igo)?\.? ?(16[3-9])\b',r'(orcament|financeir).{0,30}(vedacoes|constituicao|constitucionais)',r'(vedacoes|normas constitucionais).{0,30}(orcament|financeir)',r'orcamento impositivo',r'emendas? parlamentares?',r'regra de ouro',r'lei (de diretrizes orcamentarias|orcamentaria anual)',r'plano plurianual'],
    'dc_05': [r'sistema tributario',r'competencia tributaria',r'limitacoes.{0,20}tributar',r'principios? tributarios?',r'reparticao.{0,25}receitas',r'132/2023',r'reforma tributaria',r'imunidade tributaria',r'especies tributarias',r'taxas? de policia',r'contribuicao de melhoria',r'principio da anterioridade',r'principio da irretroatividade',r'capacidade contributiva'],
    'dc_06': [r'controle de constitucionalidade',r'acao direta de inconstitucionalidade',r'arguicao de descumprimento',r'acao declaratoria de constitucionalidade',r'\badpf\b',r'\badi\b',r'controle (difuso|concentrado)',r'sumula vinculante',r'reserva de plenario'],
    'dc_07': [r'ordem economica',r'ordem social',r'constituicao (do estado )?de sao paulo',r'seguridade social',r'livre iniciativa',r'funcao social da propriedade',r'intervencao.{0,20}dominio economico',r'direito.{0,15}(saude|educacao|meio ambiente)',r'sistema unico de saude'],
    'eco_01': [r'elasticidade',r'(curva|funcao|lei|excesso).{0,15}(oferta|demanda)',r'equilibrio (de mercado|parcial|geral)',r'(monopolio|oligopolio|competicao monopolistica|concorrencia perfeita)',r'(utilidade marginal|custo marginal|custo medio|receita marginal)',r'excedente (do consumidor|do produtor)',r'(oferta|demanda).{0,40}(preco|quantidade|mercado)',r'teoria (do consumidor|da firma|da producao)',r'restricao orcamentaria.{0,25}consumidor'],
    'eco_02': [r'pareto',r'falhas? de mercado',r'externalidades?',r'bens? (publicos|meritorios).{0,50}(rival|exclud|consumo|oferta|demanda)',r'(rival|exclud).{0,30}(bens?|consumo)',r'assimetria de informacao',r'curva de laffer',r'escolha publica',r'tributacao otima',r'excesso de gravame',r'(incidencia|equidade|eficiencia).{0,30}tribut',r'teoremas?.{0,20}bem[ -]estar',r'selecao adversa',r'risco moral',r'carona',r'public choice'],
    'eco_03': [r'contas? nacionais?',r'contabilidade (nacional|social)',r'\bpib\b',r'produto interno bruto',r'\bpnb\b',r'produto nacional',r'(crescimento|desenvolvimento) economico',r'(modelo|residuo) de solow',r'multiplicador (keynesiano|fiscal|monetario|bancario)',r'(propensao|renda disponivel|poupanca)',r'politica (monetaria|fiscal)',r'(oferta|demanda) agregada',r'base monetaria',r'oferta de moeda',r'sistema bancario'],
    'eco_04': [r'curva de phillips',r'\bis[ -]lm\b',r'mundell[ -]fleming',r'(mercado de trabalho|desemprego|inflacao|indices? de precos)',r'modelos? (classico|keynesiano)',r'armadilha da liquidez'],
    'eco_05': [r'(taxa|regime|politica|mercado|variacao).{0,15}cambi',r'balanco de pagamentos',r'economia aberta',r'(exportac|importac|balanca comercial|conta corrente|transacoes correntes|reservas internacionais)',r'(cambio|inflacao|juros|crescimento).{0,50}(arrecadacao|gasto publico|despesa publica|divida publica)',r'elasticidade.{0,25}receita',r'investimento publico.{0,30}(produtividade|crescimento)'],
    'eco_06': [r'taxa minima de atratividade',r'\btma\b',r'(avaliacao|analise|viabilidade|selecao).{0,30}(projetos|investimento)',r'vida economica',r'(valor residual|capital de giro).{0,40}projeto'],
    'eco_07': [r'analise de sensibilidade',r'estrutura a termo',r'\bettj\b',r'duration',r'value at risk',r'\bvar\b.{0,20}(risco|mercado)',r'projetos? sociais?',r'(cenarios|incerteza|risco).{0,30}(projeto|investimento)'],
    'por_01': [r'ortografi',r'acentuac',r'crase',r'grafia',r'hifen'],
    'por_02': [r'interpretacao',r'intertextualidade',r'(sentido (figurado|literal)|denotacao|conotacao)',r'figuras? de linguagem',r'(discurso direto|discurso indireto)',r'(metafora|metonimia|ironia|hiperbole|personificacao|antitese|paradoxo)',r'(genero|tipologia|estrutura).{0,20}text',r'(argumentacao|narracao|descricao|dissertacao)',r'(autor|texto|cronica|fragmento|paragrafo).{0,50}(afirma|defende|sugere|compreen|infer|sentido|opiniao|intencao)',r'(infere|depreende|deduz|conclui).{0,30}texto',r'em relacao ao texto',r'leitura.{0,15}(texto|cronica)'],
    'por_03': [r'morfossint',r'formacao de palavras',r'(sinonim|antonim)',r'(substantivo|adjetivo|adverbio|preposicao|artigo definido|artigo indefinido|locucao)',r'(prefixo|sufixo|derivacao|composicao)',r'funcao sintatica',r'(sujeito|predicado|objeto direto|objeto indireto|complemento nominal|adjunto adnominal|adjunto adverbial|predicativo)',r'sentido (equivalente|contrario|oposto)'],
    'por_04': [r'pontuacao',r'virgula',r'travessao',r'parenteses',r'pronom',r'concordancia',r'colocacao',r'aspas',r'ponto e virgula',r'dois[ -]pontos'],
    'por_05': [r'(flexao|flexoes|tempos? verbais?|modos? verbais?|forma.{0,10}verbal|verbo)',r'(voz|vozes) (ativa|passiva|reflexiva)',r'(preterito|subjuntivo|imperativo|participio|gerundio|infinitivo|futuro do presente|futuro do preterito)'],
    'por_06': [r'regencia',r'(oracoes?|periodo).{0,20}(subordinad|coordenad|compost)',r'conjun',r'conectivo',r'(relacao|valor|sentido).{0,15}(causa|concessao|condicao|finalidade|consequencia|oposicao)',r'(oracao|locucao) adverbial',r'coerente,? coeso'],
    'mat_01': [r'juros (simples|compostos)',r'taxas? (nominais?|efetivas?|reais?|equivalentes?|proporcionais?)',r'capitalizacao (continua|simples|composta)',r'montante.{0,70}(juros|taxa|capital|aplic)',r'(capital|aplicacao).{0,70}juros',r'equivalencia.{0,15}(taxas|capitais)',r'taxa.{0,15}(mensal|anual).{0,40}(juros|equivalente|capital)'],
    'mat_02': [r'(desconto (simples|composto|racional|comercial)|descontos (simples|compostos))',r'sistema (price|frances|de amortizacao|misto)',r'\bsac\b',r'(prestacoes|parcelas).{0,60}(financiamento|emprestimo|juros)',r'(financiamento|emprestimo).{0,80}(prestacoes|parcelas)',r'series? (de pagamentos|uniformes)',r'rendas? (certas|perpetuas|antecipadas|postecipadas)'],
    'mat_03': [r'valor (presente|futuro)',r'\bvpl\b',r'\btir\b',r'taxa interna de retorno',r'fluxo.{0,10}caixa.{0,50}(investimento|projeto|descont|taxa)'],
    'mat_04': [r'\b(media|mediana|moda|variancia|desvio[ -]padrao|quartil|percentil|assimetria|curtose|covariancia|correlacao)\b',r'estatistica descritiva',r'coeficiente de variacao',r'outliers?',r'distribuicao de frequencia',r'tipos de variaveis',r'(tabela|grafico|diagrama).{0,25}(frequencia|dispersao|histograma)'],
    'mat_05': [r'probabilidade',r'\bbayes\b',r'variave(is|l) aleatori',r'eventos? independentes?',r'espaco amostral'],
    'mat_06': [r'distribuicao.{0,15}(normal|binomial|poisson|bernoulli|multinomial|geometrica|hipergeometrica|uniforme|exponencial|beta|gama|student|qui[ -]quadrado)',r'teorema central do limite',r'esperanca matematica',r'funcao geradora',r'valor esperado'],
    'mat_07': [r'(amostragem|tamanho da amostra|estimacao|estimador|intervalo de confianca|estimativa pontual|estimativa intervalar)',r'aleatoria simples',r'amostra.{0,20}(estratific|conglomerado|sistematic)'],
    'mat_08': [r'teste.{0,10}(hipotese|parametric|nao parametric|media|proporcao)',r'erros? (tipo|de tipo) (i|ii|1|2)',r'valor[ -]p\b',r'p[ -]valor',r'\banova\b',r'poder do teste',r'nivel de significancia',r'hipotese nula'],
    'mat_09': [r'regressao (linear|multipla|simples)',r'series? temporais?',r'\barima\b',r'autocorrelacao',r'estacionariedade',r'minimos quadrados',r'(tendencia|sazonalidade).{0,25}serie'],
    'mat_10': [r'matriz de confusao',r'(acuracia|sensibilidade|especificidade|precisao|f1[ -]score|recall|auc|curva roc)',r'(erro absoluto medio|erro quadratico medio|rmse|\bmae\b|\bmse\b)',r'treinamento,? validacao',r'coeficiente de determinacao'],
    'mat_11': [r'(regressao logistica|arvores? de decisao|random forest|florestas? aleatorias?|maquinas? de vetores|\bsvm\b|k[ -]?nn|vizinhos mais proximos)',r'(k[ -]?means|agrupamento hierarquico|componentes principais|\bpca\b|componentes independentes|\bica\b|regras de associacao)',r'(overfitting|underfitting|ridge|lasso|regularizacao|reducao de dimensionalidade)'],
    'afo_01': [r'classificacao.{0,35}(receita|despesa|funcional|institucional|programatica|economica)',r'(receita|despesa).{0,25}(corrente|capital|classifica)',r'(grupo|elemento|modalidade).{0,20}despesa',r'categoria(s)? economica(s)?',r'fontes? (de |e destinacao de )?recursos',r'natureza (da|de) (receita|despesa)',r'codigo.{0,25}(orcamentario|receita|despesa)',r'subfuncao',r'dotacoes? orcamentarias?'],
    'afo_02': [r'creditos? (adicionais?|suplementares?|especiais?|extraordinarios?)',r'descentralizacao de creditos',r'emendas? parlamentares?',r'orcamento impositivo',r'provisao.{0,25}credito',r'destaque.{0,25}credito'],
    'afo_03': [r'conta unica',r'contingenciamento',r'limitacao (de|do) empenho',r'cronograma de desembolso',r'despesas? de exercicios? anteriores?',r'\bdea\b',r'gestao de disponibilidades'],
    'afo_04': [r'(empenho|liquidacao|arrecadacao|recolhimento|restos a pagar|suprimento de fundos)',r'estagios?.{0,20}(receita|despesa)',r'programacao financeira',r'lancamento.{0,15}receita',r'(receita|despesa).{0,20}(previsao|pagamento)'],
    'afo_05': [r'ciclo orcamentario',r'processo orcamentario',r'orcamento[ -]programa',r'orcamento (tradicional|participativo|cidadao|base zero|de desempenho)',r'tecnicas orcamentarias',r'funcoes do orcamento',r'conceito.{0,15}orcamento publico'],
    'afo_06': [r'principios? orcamentarios?',r'(principio|orcamento).{0,20}(universalidade|unidade|anualidade|exclusividade|nao afetacao|nao vinculacao|orcamento bruto|equilibrio)',r'(controle|desempenho|acompanhamento).{0,20}orcamentari'],
    'afo_07': [r'plano plurianual',r'\bppa\b',r'lei de diretrizes orcamentarias',r'\bldo\b',r'lei orcamentaria anual',r'\bloa\b',r'(programas?|acoes?).{0,30}(objetivos|metas|orcamentarias)',r'\bsiafi\b',r'\bsiafem\b',r'sistema.{0,30}(orcamentari|administracao financeira)',r'planejamento e orcamento',r'esfera orcamentaria'],
    'con_01': [r'contabilidade (aplicada ao setor publico|publica)',r'patrimonio publico',r'variac(ao|oes) patrimonia(is|l)',r'(regime|enfoque).{0,25}(orcamentario|patrimonial)',r'\bcasp\b',r'fatos (permutativos|modificativos|mistos)',r'variacao (quantitativa|qualitativa)'],
    'con_02': [r'\bpcasp\b',r'plano de contas',r'natureza da informacao',r'(reconhecimento|mensuracao|evidenciacao|registro|avaliacao).{0,25}(ativ|passiv|patrimoni|imobiliz|intangive|estoque)',r'(depreciacao|amortizacao|exaustao|impairment|reavaliacao)',r'(provisao|contingente|valor justo|custo historico)'],
    'con_03': [r'\bmcasp\b',r'manual de contabilidade',r'(integracao|escrituracao|registro).{0,35}(orcamentari|financeir|patrimonial)',r'procedimentos contabeis',r'(lancamento|debito|credito).{0,50}(setor publico|conta de controle)'],
    'con_04': [r'balanco (orcamentario|financeiro|patrimonial)',r'demonstracoes contabeis aplicadas ao setor publico',r'\bdcasp\b',r'(superavit|deficit) (orcamentario|financeiro)',r'ativo financeiro',r'passivo financeiro',r'(ativo|passivo) permanente'],
    'con_05': [r'demonstracao das variacoes patrimoniais',r'\bdvp\b',r'(demonstracao.{0,10}(mutacoes|fluxos de caixa)|\bdmpl\b|\bdfc\b)',r'notas explicativas',r'(fluxos?|atividades) de (financiamento|investimento|operacionais)',r'variac(ao|oes) patrimonia(is|l).{0,10}(aumentativa|diminutiva)'],
    'con_06': [r'(conceito|objeto|finalidade|usuarios?).{0,20}contabilidade',r'equacao patrimonial',r'(ativo|passivo) (circulante|nao circulante)',r'(bens,? direitos|direitos e obrigacoes)',r'contas (patrimoniais|de resultado)',r'patrimonio liquido',r'capital social',r'capital proprio',r'balancete'],
    'con_07': [r'(debito|credito).{0,15}(contabil|conta)',r'partidas dobradas',r'escrituracao',r'lancamentos? contabeis?',r'regime de (competencia|caixa)',r'apuracao (do|de) resultado',r'fatos? contabeis?',r'(receitas? e despesas?|despesas? e receitas?)',r'resultado do exercicio'],
    'df_01': [r'direito financeiro',r'lei de responsabilidade fiscal',r'\blrf\b',r'101/2000',r'4[. ]?320',r'atividade financeira do estado',r'fontes.{0,25}direito financeiro'],
    'df_02': [r'antecipacao de receita',r'\baro\b',r'credito publico',r'operacoes? de credito',r'regra de ouro',r'garantias? e contragarantias?',r'emprestimos publicos',r'divida publica',r'divida (consolidada|mobiliaria|fundada|flutuante)',r'ppa,? ldo',r'compatibilidade.{0,20}(ppa|ldo|loa)'],
    'df_03': [r'despesa.{0,10}(com|de) pessoal',r'limite.{0,30}pessoal',r'(despesa obrigatoria|carater continuado|geracao de despesa|aumento de despesa)',r'receita corrente liquida',r'limite prudencial',r'estimativa.{0,30}impacto orcamentario',r'legalidade da despesa'],
    'df_04': [r'precatorios?',r'processo legislativo orcamentario',r'iniciativa.{0,25}(orcamento|ldo|loa|ppa)',r'(natureza juridica|fiscalizacao|controle).{0,20}orcamento',r'compatibilidade.{0,25}(ppa|ldo|loa)'],
    'df_05': [r'renuncia de receita',r'divida ativa',r'receitas? (originarias?|derivadas?)',r'ingressos? (extraorcamentarios?|publicos?)',r'conceito.{0,20}receita publica',r'(anistia|remissao|isencao).{0,40}(beneficio|renuncia|receita|fiscal)'],
    'df_06': [r'federalismo fiscal',r'equalizacao fiscal',r'reparticao.{0,20}receitas',r'transferencias? (intergovernamentais?|constitucionais?|legais|voluntarias?|correntes?|de capital|fundo a fundo|especiais?)',r'fundo de participacao',r'\bfpe\b',r'\bfpm\b',r'(cota|quota)[ -]parte'],
    'df_07': [r'necessidade.{0,25}financiamento.{0,25}setor publico',r'\bnfsp\b',r'resultado (nominal|operacional|primario)',r'(superavit|deficit) (primario|nominal|operacional|publico)',r'(acima|abaixo) da linha',r'financiamento.{0,20}deficit'],
    'dad_01': [r'ciencia de dados',r'crisp[ -]dm',r'dados (estruturados|nao estruturados|semiestruturados)',r'ciclo de vida.{0,20}(dados|informacao)',r'(tipos|ciclo).{0,15}dados'],
    'dad_02': [r'big data',r'data (warehouse|mart|lake|lakehouse)',r'engenharia de dados',r'(limpeza|transformacao|preparacao|qualidade|completude|unicidade).{0,20}dados',r'\betl\b',r'\belt\b',r'pre[ -]processamento'],
    'dad_03': [r'bancos? de dados',r'\bsql\b',r'\bnosql\b',r'\bselect\b',r'\bjoin\b',r'\bgroup by\b',r'\border by\b',r'modelo relacional',r'chave (primaria|estrangeira)'],
    'dad_04': [r'mineracao de dados',r'data mining',r'machine learning',r'deep learning',r'aprendizado (de maquina|profundo|supervisionado|nao supervisionado)',r'inteligencia artificial',r'ia generativa',r'modelos de linguagem',r'\bllms?\b',r'processamento de linguagem natural',r'redes neurais'],
    'dad_05': [r'governanca de dados',r'(etica|explicabilidade|vies|alucinacao).{0,25}(ia|inteligencia artificial|dados|modelo)',r'(ia|inteligencia artificial).{0,25}(etica|transparencia|responsabilidade|vies)',r'(papeis|responsabilidades).{0,20}dados'],
    'dad_06': [r'seguranca da informacao',r'(confidencialidade|integridade e disponibilidade|rastreabilidade|vulnerabilidade)',r'controle de acesso',r'anonimizacao',r'mascaramento',r'retencao de dados',r'(ameacas|riscos).{0,20}(cibernetic|informacao|seguranca)'],
    'dad_07': [r'\blgpd\b',r'13[. ]?709',r'protecao de dados',r'dados pessoais',r'marco civil',r'12[. ]?965',r'agentes? de tratamento',r'bases? legais',r'direitos? do titular'],
    'a01_01': [r'superavit financeiro',r'creditos? (suplementares?|especiais?|extraordinarios?)',r'abertura.{0,25}creditos?'],
    'a01_02': [r'remanejamento',r'transposic',r'excesso de arrecadacao',r'anulacao (de dotacoes|de dotacao|parcial|total)',r'fontes?.{0,25}abertura.{0,20}creditos?',r'recursos?.{0,20}abertura.{0,20}creditos?'],
    'a01_03': [r'descentralizacao.{0,20}(credito|recurso)',r'emendas? parlamentares?',r'empenho (ordinario|estimativo|global|por estimativa)',r'(provisao|destaque).{0,25}credito'],
    'a01_04': [r'liquidacao',r'(reforco|anulacao).{0,15}empenho',r'convenios?',r'(pagamento|ordem bancaria).{0,25}(despesa|empenho|liquidac)'],
    'a01_05': [r'(alteracao|saldos?|compatibilidade|controle).{0,30}(fonte|destinacao)',r'fonte.{0,20}natureza.{0,15}despesa',r'(fonte|destinacao).{0,30}(saldos|controle|alteracao|natureza)'],
    'a01_06': [r'recursos (vinculados|ordinarios|proprios)',r'(vinculacao|destinacao).{0,20}recursos',r'receitas? vinculadas?',r'fontes de recursos'],
    'a01_07': [r'contingenciamento',r'limitacao de empenho',r'bloqueio.{0,15}(limite|orcament)',r'recomposicao de limites',r'cronograma de desembolso',r'(gestao|fluxo).{0,15}(disponibilidades|financeiro)',r'(dotacao|limite).{0,30}caixa'],
    'a01_08': [r'limites? de (movimentacao|empenho|pagamento)',r'limites? (financeiros|orcamentarios)',r'limite.{0,20}(dotacao|movimentacao|empenho|pagamento)'],
    'a01_09': [r'(bloqueio|desbloqueio|cancelamento|pagamento|disponibilidade de caixa).{0,60}restos a pagar',r'restos a pagar.{0,60}(bloqueio|desbloqueio|cancelamento|pagamento|disponibilidade|fonte)',r'disponibilidade de caixa'],
    'a01_10': [r'restos a pagar',r'encerramento.{0,20}exercicio',r'inscricao.{0,25}restos',r'(ultimo|final).{0,15}mandato'],
    'a01_11': [r'limite prudencial',r'(lei de responsabilidade fiscal|\blrf\b).{0,70}(condicoes|requisitos|limites|restricoes)',r'(nulo|vedado|proibido|vedacao).{0,80}(responsabilidade fiscal|101/2000)',r'operacoes de credito.{0,50}(limite|condic|vedac)',r'gestao fiscal responsavel'],
    'a01_12': [r'(transferencias? financeiras?|repasses?|sub[ -]repasses?|interferencias? financeiras?)',r'(movimentacao|devolucao|destinacao).{0,30}recursos publicos',r'(tesouro|fundos|autarquias).{0,30}(transferencias|repasses)'],
    'a01_13': [r'fundo de participacao',r'\bfpe\b',r'\bfpm\b',r'\b(ir|ipi|itr|icms|ipva)\b.{0,55}(reparticao|produto da arrecadacao|pertencem|municipio|estado|percentual|percentagem)',r'(reparticao|produto da arrecadacao|pertencem|percentual).{0,55}\b(ir|ipi|itr|icms|ipva)\b',r'(cota|quota)[ -]parte'],
    'a01_14': [r'reparticao.{0,20}receitas',r'transferencias? (constitucionais?|legais|voluntarias?|fundo a fundo|especiais?)',r'(uniao|estados|municipios).{0,20}reparticao'],
    'a01_15': [r'transferencias? voluntarias?',r'transparencia.{0,20}(gestao fiscal|fiscal)',r'prestacao de contas',r'(fiscalizacao|controle).{0,20}gestao fiscal',r'relatorio (de gestao fiscal|resumido da execucao orcamentaria)',r'\brgf\b',r'\brreo\b',r'conselho de gestao fiscal'],
    'a01_16': [r'divida publica',r'divida (consolidada|mobiliaria|fundada|flutuante)',r'sustentabilidade (fiscal|da divida)',r'(ancoras?|regras?) fiscais?',r'garantias? e contragarantias?',r'(composicao|custo|indexador|vencimento).{0,30}divida',r'(juros|crescimento|resultado primario).{0,40}divida',r'relacao divida.{0,8}pib'],
}

LANGUAGE_CUES = re.compile(r'\b(texto|cronica|paragrafo|fragmento|enunciados|linguistica|gramatical|gramaticalmente|grafia|ortografia|sintatica|semantica|sintaticamente|semanticamente|re[d]?acao|portuguesa|pronome|verbo|adjetivo|concordancia|regencia|crase|virgula|pontuacao|conjuncao|lacunas|vocabulos|vocabulo|trecho|frases|oracao|oracoes|sublinhad\w*)\b')
ENGLISH_CUES = re.compile(r'\b(the|according|following|statement|underlined|sentence|paragraph|phrase|title|extract|researchers|means|based|word|texto en espanol|in the text)\b')


def language_question(stem, discipline):
    # A subject label is only supporting evidence; many extracted labels bleed
    # across section boundaries. Never route a fiscal question by that label alone.
    if re.search(r'lingua (inglesa|espanhola)', discipline):
        return 'foreign'
    if len(ENGLISH_CUES.findall(stem))>=2 and not LANGUAGE_CUES.search(stem):
        return 'foreign'
    grammar=re.search(r'\b(pronom\w*|verbos?|adjetivos?|concordancia|regencia|crase|virgulas?|pontuacao|conjunc\w*|orac(?:ao|oes)|sintatic\w*|gramatica\w*|norma[ -]?padrao|ortograf\w*|acentuac\w*|reescrit\w*|flex(?:ao|oes)|tempos? verbais?|modos? verbais?)\b',stem)
    if grammar:
        return 'portuguese'
    if re.search(r'dados (estruturados|nao estruturados|semiestruturados)|banco de dados|\bsql\b|\betl\b|ciencia de dados|\bcrisp.dm\b',stem):
        return None
    if re.search(r'^\d*\s*[. -]?\s*(ainda )?em relacao ao texto (abaixo|constante)',stem):
        return 'portuguese'
    domain=re.search(r'\b(auditor\w*|contabil\w*|orcament\w*|licitat\w*|licitac\w*|tribun\w*|tribut\w*|constitu(?:icao|icoes|cional\w*)|normativo|lei|decreto|administrativ\w*|judici\w*|codigo|receita|despesa|passivos?|ativos?|patrimoni\w*|fiscal|estatistic\w*|probabilidade|depreciac\w*|amortiz\w*|custos?|custeio|contas?|financeir\w*|balanco|juros|imobiliz\w*)\b',stem)
    if domain and not re.search(r'\b(autor|narrador|poema|poeta|cronica|literari\w*|interpretacao|personagem|sentido figurado|discurso (direto|indireto)|intertextual\w*)\b',stem):
        return None
    if re.search(r'\b(frase|frases|narrador|eu lirico|poema|poeta|charge|autor|textos?|cartaz|redacao|portuguesa)\b',stem) and not re.search(r'\b(texto legal|texto constitucional|texto normativo|redacao.{0,30}lei|redacao.{0,30}complementar|codigo|lei|decreto|auditoria)\b',stem):
        return 'portuguese'
    if LANGUAGE_CUES.search(stem):
        # Administrative gap filling and literal legal excerpts aren't grammar.
        if re.search(r'(trecho|texto).{0,15}(constitucional|legal|normativo|da lei)',stem) and not re.search(r'concordancia|regencia|sintatic|gramatic|crase|pontuacao|pronome|verbo',stem):
            return None
        if re.search(r'preencha.{0,20}lacunas|lacunas.{0,20}(frase|texto|linhas)',stem) and not re.search(r'(lei|orcamento|receita|despesa|contabil|administrativ|constitu)',stem):
            return 'portuguese'
        if re.search(r'\b(texto|cronica|paragrafo|fragmento|linguistica|gramatical|gramaticalmente|ortografia|sintatica|semantica|sintaticamente|semanticamente|portuguesa|pronome|verbo|adjetivo|concordancia|regencia|crase|virgula|pontuacao|conjuncao|vocabulos|vocabulo|frases|oracao|oracoes|sublinhad\w*)\b',stem):
            return 'portuguese'
    return None


# Additional forms found while auditing the whole collection. Singulars and
# inflections matter: e.g. "crédito especial" and "créditos especiais".
VOCABULARY['adm_01'] += [r'teoria administrativa',r'planejamento (tatico|operacional)',r'funcoes?.{0,15}administrador']
VOCABULARY['adm_04'] += [r'\bpdca\b',r'(metodologias|metodos) ageis',r'manifesto agil']
VOCABULARY['adm_06'] += [r'\bgovernanca\b',r'empreendedorismo governamental',r'transparencia.{0,25}administracao publica',r'governo e sociedade',r'not accountable']
VOCABULARY['adm_07'] += [r'avaliac(?:ao|oes) (de impacto|ex post|de programa)',r'custo.beneficio',r'grupos? de (controle|tratamento)',r'ciclo de politicas',r'indicador(?:es)?.{0,15}(sociais|desenvolvimento humano)',r'\bidh\b',r'diferenca.em.diferencas',r'politica publica',r'\bacb\b']
VOCABULARY['adm_08'] += [r'\bauditoria\b',r'\bauditorias\b',r'papeis de trabalho',r'testes? de (observancia|aderencia|auditoria)',r'opiniao.{0,25}auditor',r'auditores independentes']
VOCABULARY['da_01'] += [r'principio.{0,12}(legalidade|eficiencia)',r'principios administrativos',r'administracao publica.{0,35}principios']
VOCABULARY['da_04'] += [r'agentes? de colaboracao',r'funcionarios? publicos?',r'cargos,? empregos e func',r'funcionarios publicos civis',r'estatuto dos funcionarios']
VOCABULARY['da_05'] += [r'licitatori\w*',r'licitantes?',r'\blicitacao\b',r'procedimento licitatorio',r'certame.{0,30}(obra|contratacao|preco)']
VOCABULARY['da_06'] += [r'\bbem publico\b',r'concessionari\w*',r'dano.{0,40}administracao publica',r'conduta imputavel.{0,30}administracao',r'usucapiao.{0,30}public']
VOCABULARY['dc_01'] += [r'classificacao da constituicao',r'hermeneutica',r'interpretacao juridica',r'soberania',r'teoria do estado']
VOCABULARY['dc_02'] += [r'direitos humanos.{0,20}geracao',r'inviolabilidade',r'intimidade',r'pluralismo politico',r'inelegibilidade',r'reeleicao',r'liberdade de expressao',r'direito de resposta']
VOCABULARY['dc_03'] += [r'assembleia legislativa.{0,20}(sao paulo|compet|iniciativa)',r'ministros de estado',r'presidente da republica',r'constituicao.{0,30}(desmembramento|municipio|distrito federal)',r'organizacao federativa',r'comissao mista.{0,20}orcament',r'\bcmo\b',r'sancao.{0,12}lei']
VOCABULARY['dc_05'] += [r'imunidades? tributarias?',r'(uniforme|indelegavel|capacidade economica).{0,30}(imposto|tribut|contribuinte)',r'(imposto|tribut).{0,30}(uniforme|indelegavel)',r'competencias tributarias',r'(especie|conceito|definicao).{0,25}(tributo|taxa|imposto)',r'competencia (federal|municipal|estadual)',r'imposto residual',r'legalidade.{0,20}tributaria',r'legalidade tributaria',r'\be imune\b',r'taxas?.{0,20}(emolumentos|cartorios)',r'(competencia|instituir|anterioridade|nao cumulativ|seletiv).{0,70}(imposto|icms|ipi|ipva|iss)',r'(imposto|icms|ipi|ipva|iss).{0,70}(competencia|instituir|anterioridade|nao cumulativ|seletiv)']
VOCABULARY['dc_07'] += [r'principios gerais da atividade economica',r'estado de bem.estar social']
VOCABULARY['eco_01'] += [r'monopolista',r'concorrencia monopolistica',r'cobb.douglas',r'funcao de producao']
VOCABULARY['eco_02'] += [r'lump.sum',r'deadweight.loss',r'(tributo|imposto).{0,50}(eficiente|equitativo)',r'funcoes do estado na economia',r'(alocativa|distributiva|estabilizadora)',r'(bens publicos|bem publico).{0,60}(rival|exclu|estado|mercado)']
VOCABULARY['eco_03'] += [r'demanda por moeda',r'teoria keynesiana',r'selic',r'depositos compulsorios',r'produto (domestico|de equilibrio)',r'renda liquida',r'impostos indiretos liquidos',r'oferta monetaria',r'mercado monetario']
VOCABULARY['eco_04'] += [r'inflacionaria',r'inflacionario',r'estabilizacao monetaria',r'plano (real|cruzado)',r'forca de trabalho',r'subocupad\w*']
VOCABULARY['eco_05'] += [r'marshall.lerner']
VOCABULARY['eco_06'] += [r'\bacb\b']
VOCABULARY['por_02'] += [r'\bo autor\b',r'em seu conjunto.{0,15}texto',r'(redacao|frase|frases|ideias).{0,30}(claro|corret|coerent)',r'redacao.{0,15}frase',r'\btira\b',r'causa e efeito']
VOCABULARY['por_05'] += [r'flexao.{0,15}plural',r'verbos']
VOCABULARY['por_06'] += [r'periodo.{0,30}(coeso|coerente)',r'causa e efeito']
VOCABULARY['mat_01'] += [r'taxa real de juros',r'taxa nominal de juros',r'taxa efetiva de juros']
VOCABULARY['mat_02'] += [r'prestac(?:ao|oes).{0,40}(semestrais|mensais|anuais)',r'(financiamento|emprestimo).{0,80}prestacoes']
VOCABULARY['mat_04'] += [r'variaveis qualitativas',r'variaveis quantitativas',r'variavel (qualitativa|quantitativa)']
VOCABULARY['mat_09'] += [r'\bregressao\b']
VOCABULARY['mat_10'] += [r'aprendizado supervisionado']
VOCABULARY['afo_01'] += [r'classificacao (funcional|institucional|economica|programatica|orcamentaria)',r'receita patrimonial',r'despesa orcamentaria',r'receita orcamentaria']
VOCABULARY['afo_05'] += [r'orcamento base.zero',r'pacotes de decisao',r'ciclo orcamental',r'orcamento sensivel']
VOCABULARY['afo_06'] += [r'execucao orcamentaria']
VOCABULARY['afo_07'] += [r'lei orcamentaria',r'plano de metas',r'programas? de governo']
VOCABULARY['con_01'] += [r'transacao sem contraprestacao',r'perspectiva orcamentaria',r'regime.{0,20}receita orcamentaria']
VOCABULARY['con_02'] += [r'ativo imobilizado',r'\bintangivel\b',r'valor recuperavel',r'contas a receber',r'(estoques|ativos|passivos).{0,30}(custo|avaliacao|reconheci|mensura|valor)',r'baixa de um direito',r'informacao contabil.{0,20}(qualitativa|caracteristica)',r'caracteristica.{0,30}(informacao|representacao)',r'\bgoodwill\b',r'\bpassivo\b.{0,50}incerteza']
VOCABULARY['con_03'] += [r'lancamento contabil',r'sistema de compensacao']
VOCABULARY['con_04'] += [r'execucao orcamentaria.{0,40}(saldo|variacao liquida|disponibilidade)']
VOCABULARY['con_05'] += [r'fluxo de caixa',r'\bfluxos? de caixa\b']
VOCABULARY['con_06'] += [r'conta contabil',r'natureza (credora|devedora)',r'debita a conta',r'credita a conta',r'contas a pagar']
VOCABULARY['con_07'] += [r'contabiliza\w*',r'lucro liquido',r'\bdre\b',r'demonstracao (do|de) resultado',r'receitas?.{0,20}reconhec',r'(debita|credita|debito|credito).{0,10}conta',r'salarios a pagar']
VOCABULARY['df_05'] += [r'receitas publicas',r'\breceita publica\b',r'entrada.{0,30}cofres publicos']
VOCABULARY['df_06'] += [r'reparticao constitucional',r'receitas transferidas']
VOCABULARY['df_07'] += [r'resultado fiscal',r'deficits? primarios',r'deficits? nominais',r'contas publicas']
VOCABULARY['dad_02'] += [r'pareamento de dados',r'power query']
VOCABULARY['dad_03'] += [r'\btriggers?\b',r'procedimentos armazenados',r'\bviews\b']
VOCABULARY['dad_05'] = [r'governanca de dados',r'(etica|explicabilidade|vies|alucinacao).{0,25}(\bia\b|inteligencia artificial)',r'(\bia\b|inteligencia artificial).{0,25}(etica|transparencia|responsabilidade|vies)',r'(papeis|responsabilidades).{0,20}dados']
VOCABULARY['da_08'] += [r'acesso a informacao',r'\be.sic\b']
VOCABULARY['a01_16'] += [r'divida (bruta|liquida|interna|externa)',r'divida.{0,40}setor publico']
VOCABULARY['adm_01'] += [r'planos operacionais',r'decisoes estrategicas e taticas']
VOCABULARY['adm_06'] += [r'colaboracao publico.privada',r'participacao social']
VOCABULARY['adm_07'] += [r'politicas governamentais',r'indicadores de eficiencia',r'programas sociais']
VOCABULARY['adm_10'] += [r'\bcontroles internos\b',r'gov 91[03]0',r'\bintosai\b']
VOCABULARY['da_01'] += [r'agencia reguladora',r'empresas estatais']
VOCABULARY['da_03'] += [r'poder publico.{0,40}forca',r'autoexecutoriedade']
VOCABULARY['da_04'] += [r'servidor estavel',r'cargo (de provimento )?efetivo',r'inassiduidade habitual']
VOCABULARY['dc_01'] += [r'clausulas petreas',r'poder de reforma',r'nova constituicao']
VOCABULARY['dc_07'] += [r'politica agricola',r'reforma agraria',r'lavra de recursos minerais']
VOCABULARY['eco_01'] += [r'bem de giffen',r'caixa de edgeworth',r'curvas? de indiferenca',r'modelo de troca',r'dilema dos prisioneiros',r'equilibrio de nash',r'teoria dos jogos']
VOCABULARY['eco_02'] += [r'(tributacao|tributo|imposto).{0,30}(progressiv|regressiv|proporciona)',r'setor publico.{0,20}(alocativa|distributiva|estabilizadora)']
VOCABULARY['eco_03'] += [r'\bmoeda\b.{0,25}(sistema economico|cria|liquidez)',r'\bsolow\b',r'produto a precos de mercado',r'produto a custo de fatores',r'orcamento equilibrado',r'criar liquidez',r'conselho monetario nacional',r'intermediarios financeiros']
VOCABULARY['eco_06'] += [r'analise de viabilidade',r'viabilidade tecnica',r'(vida util|capital de giro|taxa de desconto).{0,40}projeto']
VOCABULARY['eco_07'] += [r'\bettjs?\b',r'(risco|incerteza).{0,30}projetos sociais']
VOCABULARY['por_02'] += [r'coerencia',r'incoerencia',r'redundancia',r'ironic',r'linguagem (logica|figura|metalingu)',r'funcao de linguagem',r'personagens?',r'\bpoema\b',r'\beu lirico\b',r'\bcartaz\b',r'\bcharge\b']
VOCABULARY['por_03'] += [r'mesmo significado',r'\bsinonimia\b',r'\bantonimia\b',r'\bplural\b',r'termo.{0,30}significa']
VOCABULARY['por_05'] += [r'tempo verbal']
VOCABULARY['por_06'] += [r'ordem direta',r'causa e consequencia']
VOCABULARY['mat_01'] += [r'juros ao mes',r'juros ao ano',r'capitalizacao',r'taxa de juros.{0,40}(mensal|anual)',r'aplicar.{0,60}(juros|taxa|capital)',r'encargos financeiros totais']
VOCABULARY['mat_02'] += [r'renda mensal.{0,40}fundo',r'apos o periodo de acumulacao',r'depositos? (mensais|semestrais|anuais)']
VOCABULARY['mat_04'] += [r'interquartil',r'variaveis qualitativas',r'variaveis quantitativas']
VOCABULARY['afo_01'] += [r'classificacoes.{0,15}despesa',r'autorizacoes de despesa',r'dotacoes para manutencao',r'\bclassificada\b.{0,30}(corrente|capital|investimento|custeio)']
VOCABULARY['afo_04'] += [r'etapa da despesa',r'execucao da despesa',r'direito adquirido pelo credor']
VOCABULARY['afo_07'] += [r'definicao dos programas',r'programacao orcamentaria',r'proposta orcamentaria']
VOCABULARY['con_01'] += [r'entidade publica',r'entidade do setor publico',r'normas brasileiras de contabilidade aplicadas ao setor publico',r'\bnbc t 16\b']
VOCABULARY['con_02'] += [r'passivo.{0,70}incerteza',r'estrutura conceitual',r'\brcpgs?\b',r'relatorio contabil',r'tratamento contabil',r'valor de custo dos estoques',r'representacao fidedigna',r'provisoes',r'reconhecer contabilmente',r'ativo e um recurso']
VOCABULARY['con_06'] += [r'variacoes positivas nas contas',r'contas de curto prazo']
VOCABULARY['con_07'] += [r'\blancamento\b',r'\bdividendos\b',r'\btransacoes\b.{0,30}(loja|estoque|vendas)',r'receita total',r'demonstracoes (financeiras|contabeis)',r'demonstracao contabil']
VOCABULARY['con_05'] += [r'gerou caixa',r'caixa e equivalentes',r'atividades operacionais',r'fluxo.{0,10}caixa']
VOCABULARY['df_01'] += [r'financas publicas']
VOCABULARY['df_04'] += [r'orcamento.{0,25}natureza juridica']
VOCABULARY['a01_06'] += [r'fundos financeiros',r'fundos especiais']
VOCABULARY['a01_15'] += [r'demonstrativos fiscais',r'metas anuais',r'anexo de riscos fiscais',r'incentivos fiscais',r'recursos.{0,30}alienacao de ativos']
VOCABULARY['dad_06'] += [r'firewalls?',r'\bcid\b.{0,30}seguranca']
VOCABULARY['adm_05'] = [p for p in VOCABULARY['adm_05'] if p not in ['motivacao','lideranca']]
VOCABULARY['adm_05'] += [r'(motivacao|lideranca).{0,60}(organiz|equipe|funcionario|colaborador)',r'(organiz|equipe|funcionario|colaborador).{0,60}(motivacao|lideranca)',r'capacitacao profissional']
VOCABULARY['da_01'] += [r'procedimento administrativo',r'procedimentos administrativos',r'10[. ]?177']
VOCABULARY['da_04'] += [r'\bservidor\b',r'\bservidores\b']
VOCABULARY['da_03'] += [r'principio da motivacao']
VOCABULARY['da_06'] += [r'terreno publico',r'responsabilidade.{0,40}(danos morais|danos materiais)',r'permissao de uso']
VOCABULARY['dc_02'] += [r'direitos e deveres individuais',r'nasceu no territorio brasileiro',r'\bdireito de associacao\b']
VOCABULARY['dc_03'] += [r'compet(e|encia).{0,25}uniao',r'deputado federal',r'emenda a constituicao do estado',r'\bteoria dos freios e contrapesos\b']
VOCABULARY['dc_05'] += [r'conceito de tributo',r'\bdefine tributo\b',r'\bdefinicao de tributo\b',r'\bprecos publicos e taxas\b',r'\bimunidade\b',r'\bimunidades\b',r'\binstituir\b.{0,40}(imposto|tributo|taxa)']
VOCABULARY['eco_01'] += [r'utilidade esperada',r'mercado competitivo']
VOCABULARY['eco_02'] += [r'carga tributaria.{0,30}(renda|distribuicao)',r'\bgini\b']
VOCABULARY['eco_03'] += [r'agregados monetarios',r'meios de pagamento',r'sistema financeiro nacional']
VOCABULARY['eco_05'] += [r'maxidesvalorizacao',r'juros americana',r'choques externos']
VOCABULARY['mat_02'] += [r'taxa de descontos?',r'valor.{0,10}prestacao',r'vendas a prazo']
VOCABULARY['afo_01'] += [r'receita tributaria',r'dotacao',r'despesa.{0,30}classificac']
VOCABULARY['afo_03'] += [r'unificacao dos recursos de caixa']
VOCABULARY['afo_04'] += [r'deficit de execucao']
VOCABULARY['con_06'] += [r'total do ativo',r'\bconceitual basica\b']
VOCABULARY['con_02'] += [r'propriedade para investimento',r'\bprovisao\b',r'conceitual.{0,20}relatorio']
VOCABULARY['df_05'] += [r'gastos tributarios',r'beneficios fiscais',r'incentivos fiscais']
VOCABULARY['a01_16'] += [r'\bcapag\b',r'titulos (publicos|do tesouro)',r'obrigac(?:ao|oes) fiscai']
VOCABULARY['por_06'] = [r'\bconjunc(?:ao|oes)\b' if p=='conjun' else p for p in VOCABULARY['por_06']]
VOCABULARY['con_02'] += [r'deprecia (os|o|as|a)',r'ativos imobilizados',r'registro contabil']
VOCABULARY['por_02'] += [r'argumentacao',r'\bnarrador\b',r'consideracoes de',r'segundo.{0,30}(calvino|conrad)',r'palavras de marilena']


def expand_forms(pattern):
    for old,new in [
        ('adicionais?', 'adiciona(?:l|is)'), ('suplementares?', 'suplementar(?:es)?'),
        ('especiais?', 'especia(?:l|is)'), ('parlamentares?', 'parlamentar(?:es)?'),
        ('servidores?', 'servidor(?:es)?'), ('bens? publicos?', '(?:bem|bens) publicos?'),
        ('fundacoes?', 'fundac(?:ao|oes)'), ('operacoes?', 'operac(?:ao|oes)'),
        ('oracoes?', 'orac(?:ao|oes)'), ('variacoes?', 'variac(?:ao|oes)'),
        ('imunidades?', 'imunidade(?:s)?'), ('controles?', 'controle(?:s)?'),
    ]:
        pattern=pattern.replace(old,new)
    return pattern


COMPILED = {key:[re.compile(expand_forms(p)) for p in patterns] for key,patterns in VOCABULARY.items()}
