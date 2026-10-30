# Proposta da base de questões e tópicos de editais

Estado: referência de desenho. A primeira extração foi executada em 29/10/2026; cobertura, limitações e acesso estão em README.md. Recursos de recomendação e relações tópico–questão descritos abaixo são objetivos posteriores.

Data: 29/10/2026.

## Decisões já definidas pelo usuário

- Extrair todas as disciplinas das provas da biblioteca.
- Relacionar tópicos de edital a questões de cobrança direta e também a questões correlatas ou de pré-requisito, em grupos separados.
- Usar agentes Luna em paralelo nas futuras extrações de questões e de tópicos.
- Refinar este esquema antes de iniciar a extração.
- Manter a estrutura de recomendação e acompanhamento do aluno separada da base de conteúdo.
- Incluir habilidades avaliadas na base de questões, com vínculos reutilizáveis e rastreáveis.

## Objetivos de consulta

- Encontrar questões por palavras, expressões, conceitos e referências normativas.
- Filtrar por disciplina, assunto, banca, órgão, cargo, especialidade, ano, formato, situação do gabarito e qualidade da extração.
- Partir de qualquer tópico de um edital e recuperar questões que o cobram diretamente.
- Consultar separadamente questões correlatas ou que cobram pré-requisitos.
- Identificar tópicos sem questões correspondentes no acervo disponível.
- Abrir o PDF original na página da questão, do gabarito ou do tópico.
- Contar questões únicas e ocorrências em provas sem confundir repetição de cadernos com frequência de cobrança.

## Entidades e informações

### 1. Documento de origem

Campos: `documento_id`, `tipo_documento`, `arquivo_local`, `sha256`, `total_paginas`, `url_fonte`, `urls_alternativas`, `data_publicacao`, `data_download`, `versao_documento`, `substitui_documento_id`, `observacoes`.

Reutilizar o inventário existente em `biblioteca-concursos/fontes.json` e `verificacao.json`. Um documento pode servir a vários cargos, provas ou especialidades. Espelhos idênticos preservam suas fontes e apontam para o mesmo conteúdo.

Não presumir que a data do edital, o ano do concurso e a data da aplicação sejam iguais. Datas desconhecidas ficam nulas, com a precisão conhecida registrada.

### 2. Concurso, cargo e prova

Campos: `concurso_id`, `banca`, `orgao`, `uf`, `municipio`, `ano_concurso`, `cargo_id`, `cargo_nome_original`, `especialidade_original`, `escolaridade`, `prova_id`, `data_aplicacao`, `fase`, `turno`, `codigo_caderno`, `versao_caderno`, `cor_caderno`, `bloco_prova`, `disciplinas_impressas`, `quantidade_esperada_objetivas`, `quantidade_esperada_discursivas`, `documento_id`.

A quantidade esperada só será preenchida quando houver evidência no documento. Registrar os escopos comuns e específicos em provas que atendam vários cargos.

### 3. Questão e ocorrência

Separar o conteúdo da questão de sua ocorrência em uma prova. A identidade de uma ocorrência depende da prova, do caderno, do bloco e do número original, e recebe um identificador persistente.

Campos da ocorrência: `ocorrencia_id`, `prova_id`, `numero_original`, `ordem_no_documento`, `bloco_original`, `disciplina_impressa`, `questao_id`, `paginas_pdf`, `paginas_impressas`, `regioes_fonte`, `referencias_fonte`.

Campos do conteúdo: `questao_id`, `formato`, `enunciado_original`, `texto_para_busca`, `contextos_ids`, `alternativas`, `subitens`, `anexos_ids`, `referencias_normativas_literais`, `hash_texto`, `grupo_duplicidade`, `observacoes`.

Formatos previstos: múltipla escolha, certo/errado e discursiva. Outros formatos só serão adicionados quando observados.

Regras de segmentação:

- Em certo/errado, cada item com resposta própria é uma questão. Preservar o comando e o contexto compartilhados.
- Assertivas I, II e III dentro de uma questão de múltipla escolha permanecem subestruturas da mesma questão.
- Textos, casos, tabelas ou figuras usados por várias questões serão armazenados como contextos compartilhados, com ordem de leitura.
- Subitens discursivos permanecem ligados à questão original; só terão respostas ou critérios independentes quando isso estiver explícito na fonte.
- Questões que atravessam páginas devem manter todos os trechos e a sua sequência.
- Não fundir automaticamente questões semelhantes, nem cadernos que mudam a ordem das alternativas. Candidatos à duplicidade conservam suas ocorrências e suas correspondências de alternativas.

Alternativas: identificador, rótulo original, ordem, texto original, texto normalizado e regiões de origem. Não gerar alternativas que não existam na fonte.

Anexos: tipo, arquivo local do recorte, documento, página, região, legenda original e descrição auxiliar quando necessária. A descrição inferida nunca substitui a imagem original.

O texto para busca poderá corrigir quebras de linha, hifenização de diagramação e espaços. O original permanece preservado. Fórmulas, sinais, valores e unidades precisam de verificação específica quando a leitura for incerta.

### 4. Gabarito e histórico

Campos: `gabarito_registro_id`, `ocorrencia_id`, `documento_gabarito_id`, `codigo_caderno`, `versao_caderno`, `bloco_prova`, `numero_original`, `resposta_publicada`, `situacao_item`, `natureza_gabarito`, `data_publicacao`, `paginas_fonte`, `regioes_fonte`, `substitui_registro_id`, `status_associacao`, `observacoes`.

`natureza_gabarito`: preliminar, definitivo ou não identificado.

`situacao_item`: válido, anulado, alterado ou não identificado. Ausência de gabarito é uma condição de disponibilidade, distinta de anulação.

Regras:

- O definitivo comprovadamente correspondente à ocorrência orienta a resposta de referência; preservar publicações anteriores.
- Se houver apenas preliminar, exibir essa condição.
- Confirmar prova, caderno, versão, bloco e número antes de associar respostas. A numeração sozinha não basta.
- Divergências entre fontes ou entre versões declaradas definitivas entram em revisão.
- Não resolver questões para preencher gabaritos ausentes.
- Respostas discursivas e critérios de correção só serão extraídos quando efetivamente disponíveis em documentos de origem.

### 5. Classificação temática da questão

Campos: `classificacao_id`, `questao_id`, `conceito_id`, `disciplina_normalizada`, `caminho_tematico`, `papel_do_assunto`, `palavras_chave`, `trecho_evidencia`, `referencia_fonte`, `origem_classificacao`, `metodo`, `modelo`, `versao_taxonomia`, `grau_confianca_classificacao`, `status_revisao`.

`papel_do_assunto`: central, secundário ou pré-requisito.

Preservar a disciplina impressa separadamente da disciplina atribuída pelo modelo. Uma questão pode receber vários assuntos centrais ou secundários. Classificações inferidas precisam ser identificadas como inferidas.

Taxonomia proposta: disciplina > assunto > subassunto > conceito. A profundidade varia conforme o conteúdo; não criar níveis artificiais para preencher uma estrutura fixa.

Sinônimos e abreviações apontam para conceitos estáveis. Termos ambíguos são contextualizados por disciplina. Exemplos: AFO, Administração Financeira e Orçamentária; LDO, Lei de Diretrizes Orçamentárias.

Referências normativas: preservar a forma literal e, quando verificável no próprio documento, registrar norma, número, ano, artigo e edição citada. A base não declarará automaticamente que uma questão antiga continua juridicamente atual.

### 5.1. Habilidades avaliadas

As habilidades fazem parte do catálogo de conteúdo, em entidades próprias ligadas às questões. Uma habilidade descreve uma ação sobre um objeto de conhecimento que a questão exige executar.

Exemplo de distinção: disciplina = Contabilidade Pública; tópico = estágios da despesa; habilidade = distinguir liquidação e pagamento em uma situação concreta.

Campos da habilidade: `habilidade_id`, `descricao_operacional`, `acao`, `objeto_conhecimento`, `tipo_demanda`, `conceitos_ids`, `versao_definicao`, `status_revisao`.

Campos do vínculo: `questao_habilidade_id`, `questao_id`, `habilidade_id`, `papel_na_questao`, `trecho_evidencia`, `referencias_fonte`, `justificativa_curta`, `origem_classificacao`, `modelo`, `versao_classificacao`, `grau_confianca_classificacao`, `status_revisao`.

Categorias iniciais de demanda: identificar, distinguir, interpretar, aplicar, calcular e analisar. O vocabulário será refinado no piloto. Categorias não representam automaticamente níveis de dificuldade ou uma escala psicométrica validada.

Regras:

- Uma questão pode avaliar várias habilidades; a mesma habilidade pode aparecer em várias questões e concursos.
- O papel no vínculo distingue exigência central e apoio, com evidência. Não associar todas as habilidades do assunto a todas as questões daquele assunto.
- Preservar separadamente a descrição original que exista na fonte e a habilidade inferida pelo modelo.
- Formular descrições específicas e reutilizáveis, evitando tanto rótulos vagos como “saber contabilidade” quanto descrições presas aos nomes e valores de um único enunciado.
- Não atribuir pesos numéricos arbitrários às habilidades.
- Não incluir estado do aluno, histórico de respostas ou decisão de recomendação nesses registros.
- Relações de pré-requisito entre habilidades podem ser adicionadas futuramente em catálogo próprio; não são um requisito para a extração inicial das habilidades avaliadas.

### 6. Edital, escopo de conteúdo e tópico

Campos do edital: `edital_id`, `documento_id`, `concurso_id`, `numero_original`, `data_publicacao`, `tipo_publicacao`, `versao`, `retifica_edital_id`.

Campos do tópico: `topico_id`, `edital_id`, `escopo_conteudo_id`, `topico_pai_id`, `ordem_original`, `numero_original`, `texto_original`, `texto_para_busca`, `caminho_original`, `disciplina_original`, `paginas_fonte`, `regioes_fonte`, `estado_na_versao`, `topico_substituido_id`, `conceitos_normalizados`, `status_extracao`.

O escopo de conteúdo relaciona tópico a cargo, especialidade, bloco da prova e à condição comum/específica. Uma seção compartilhada pode servir a vários cargos sem repetir o tópico.

Regras:

- Extrair o conteúdo programático com sua hierarquia original.
- Preservar tópicos amplos e seus filhos. Não atribuir a um tópico amplo a mesma especificidade de uma subdivisão explícita.
- Quando um item composto contiver conceitos separáveis, manter o item original e representar as partes como unidades auxiliares de indexação, identificadas como derivadas.
- Não transformar requisitos, cronogramas, atribuições, condições de inscrição ou referências incidentais em tópicos de conteúdo programático.
- Preservar notas e restrições sobre bibliografia, normas, edições e datas de atualização quando vinculadas ao conteúdo.
- Registrar acréscimos, exclusões e substituições das retificações. Não apagar o histórico.
- Distinguir abertura, retificação e edital consolidado; tópicos do mesmo conteúdo em documentos repetidos não devem inflar a contagem.

### 7. Associação entre tópico e questão

Campos: `associacao_id`, `topico_id`, `questao_id`, `escopo_conteudo_id`, `tipo_relacao`, `conceitos_compartilhados`, `trecho_questao_evidencia`, `trecho_topico_evidencia`, `justificativa_curta`, `metodo`, `versao_metodo`, `modelo`, `score_similaridade`, `grau_confianca_match`, `status_revisao`, `data_associacao`.

`tipo_relacao`: cobrança direta, correlata ou pré-requisito. Correspondências descartadas podem ser preservadas para auditoria, mas não aparecem como resultados válidos.

Regras:

- Associação muitos-para-muitos: um tópico pode corresponder a várias questões e vice-versa.
- Cobrança direta exige evidência do conceito efetivamente avaliado. Mera presença de palavras no contexto ou em uma alternativa não basta.
- Separar o que a questão exige resolver de conceitos citados apenas como distração ou contexto.
- Usar busca lexical, sinônimos, taxonomia e busca semântica como mecanismos complementares de recuperação de candidatos.
- A similaridade semântica não é uma prova de cobertura nem uma probabilidade de acerto do vínculo.
- Exibir cobrança direta separadamente de correlatas e pré-requisitos, conforme escolha do usuário.
- A classificação de assunto é independente de um edital específico. O vínculo com cada edital é um registro próprio, que pode ser recalculado sem reextrair a questão.
- Um tópico sem questões diretas no acervo deve aparecer como lacuna do acervo, sem concluir que nunca foi cobrado.

## Qualidade, revisão e rastreabilidade

Manter três avaliações distintas: qualidade da transcrição, confiança da classificação temática e confiança da associação tópico-questão.

Campos de auditoria: `execucao_id`, `documento_sha256`, `agente`, `modelo`, `versao_instrucoes`, `versao_extrator`, `data_processamento`, `metodo_leitura`, `status_extracao`, `alertas`, `revisao_id`, `alteracoes`.

Estados de extração: extraído, precisa de revisão ou incompleto. Campos ausentes permanecem nulos, com motivo. Não tratar preenchimento obrigatório como autorização para inventar valores.

Validações previstas:

- Quantidade extraída versus quantidade explicitamente esperada na prova.
- Lacunas ou repetições de numeração por bloco e caderno.
- Limites entre enunciados, alternativas, comandos e contextos compartilhados.
- Alternativas completas e na ordem original.
- Preservação de números, fórmulas, tabelas, gráficos e sinais.
- Associação de gabarito com ocorrência e versão corretas.
- Referências a páginas, regiões e arquivos locais existentes.
- Origem documental de cada dado extraído e evidência para as classificações inferidas.
- Revisão independente de casos problemáticos e de uma amostra dos demais; uma amostra aprovada não implica revisão integral do acervo.

## Armazenamento proposto

- SQLite como base local de conteúdo consolidada, com chaves e relações entre documentos, provas, questões, ocorrências, contextos, gabaritos, conceitos, habilidades, vínculos questão-habilidade, editais, tópicos e associações.
- FTS5 para busca textual em questões, alternativas, contextos e tópicos. Documentação: https://www.sqlite.org/fts5.html.
- Resultados intermediários JSONL por lote e por agente, com esquema comum e validação antes da consolidação.
- Exportações CSV para consulta e análise; JSONL para preservar estruturas hierárquicas e multimídia.
- PDFs e recortes mantidos como arquivos locais referenciados na base.
- Índices semânticos e embeddings poderão ser gerados como derivados, com modelo e versão registrados, sem substituir os textos originais.

## Execução futura das fleets

Limite atual da sessão: até três agentes Luna trabalhando simultaneamente, além do coordenador. Paralelizar em lotes com uma fila de trabalho até cobrir o acervo.

1. Fechar o esquema após o refinamento.
2. Fazer um piloto pequeno, incluindo múltipla escolha, certo/errado e material com figura, tabela ou discursiva. Conferir o resultado antes do processamento integral.
3. Fleet de questões: processar os cadernos e seus gabaritos em lotes independentes, produzindo JSONL e registros de evidência.
4. Consolidar e validar questões e gabaritos.
5. Fleet de editais: extrair hierarquias, escopos por cargo e retificações de todos os editais disponíveis.
6. Consolidar os tópicos e a taxonomia, preservando o vocabulário original de cada edital.
7. Processar os matches, com cobrança direta, correlatas e pré-requisitos em grupos separados.
8. Revisar divergências e apresentar índice pesquisável, cobertura por tópico e fila de pendências.

Os agentes não escreverão simultaneamente na mesma base SQLite. O coordenador consolida lotes validados. As divisões de trabalho devem respeitar os limites das questões; quando houver divisão por páginas, incluir o contexto necessário e eliminar sobreposições na consolidação.

## Limite de responsabilidade e integração com recomendação

A base aqui proposta é um catálogo de conteúdo. Ela armazena questões, gabaritos, contextos, referências documentais, assuntos, habilidades avaliadas e tópicos dos editais, com suas relações e versões.

A outra estrutura de recomendação poderá consumir esse catálogo para selecionar questões e interpretar resultados. Histórico de tentativas, perfil do aluno, estimativas de domínio, esquecimento, agenda de revisão, prioridades pessoais e decisões de recomendação pertencem àquela estrutura. Esta proposta não determina onde nem como ela os armazenará.

A integração se apoia em identificadores persistentes: `questao_id`, `ocorrencia_id`, `habilidade_id`, `topico_id`, identificador da versão do gabarito e versões das classificações. Mudanças de classificação ou gabarito preservam o histórico para permitir reavaliação pelo consumidor.

Informações sobre o estudante não são exigidas para extrair ou classificar o conteúdo. O catálogo pode ser usado por diferentes usuários e diferentes políticas de recomendação.

A classificação de habilidades pode contribuir para identificar pontos fracos, mas não demonstra, por si só, uma dificuldade do aluno: essa interpretação depende das interações e dos critérios mantidos na outra estrutura.

Resoluções comentadas geradas e estimativas de dificuldade também podem ser mantidas como recursos derivados separados, vinculados às questões e identificados por autoria, método e versão. Não são requisitos da primeira extração.

As ideias anteriores sobre acompanhamento adaptativo foram preservadas em [notas separadas](NOTAS-SOBRE-RECOMENDACAO.md), como referência, sem integrar o esquema desta base.
