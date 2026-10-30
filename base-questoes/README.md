# Base local de questões e editais

Extração de 29/10/2026. Abra [o índice pesquisável](dados/index.html) no navegador. Funciona localmente, sem servidor ou conexão: busca por palavras, expressões, assuntos e habilidades candidatas; filtros por tipo, banca, concurso e estado de extração. Cada questão oferece alternativas, gabaritos, PDF e imagem das páginas originais. O gabarito fica recolhido para permitir resolver a questão antes de consultar a resposta.

## Conteúdo disponível

| Conteúdo | Quantidade |
|---|---:|
| PDFs de origem | 71 |
| Cadernos de provas | 33 |
| Ocorrências de questões | 2.349 |
| Conteúdos únicos por hash normalizado | 2.262 |
| Questões de múltipla escolha | 2.016 |
| Itens certo/errado | 330 |
| Propostas discursivas | 3 |
| Questões objetivas com gabarito associado | 2.346 |
| Registros de tópicos de edital | 4.429 |
| Editais com conteúdo programático extraído | 12 |
| Páginas originais de provas renderizadas | 545 |

As provas abrangem todas as disciplinas presentes nos cadernos. Bancas: Cebraspe (410 ocorrências), ESAF (264), FCC (351), FGV (702), Fundatec (94) e Vunesp (528).

O acervo contém 13 PDFs de editais. Um deles é uma retificação da FCC de cronograma/recursos, sem alteração programática, e por isso não produz tópicos. Os 4.429 registros incluem níveis hierárquicos e 158 unidades de indexação derivadas explicitamente de parágrafos; não representam 4.429 conceitos independentes. Escopos de outros cargos presentes nos editais também estão preservados e devem ser filtrados na comparação com uma prova.

## Arquivos e consultas

- [SQLite com busca FTS5](dados/conteudo.sqlite): fonte estruturada principal.
- [Questões JSONL](dados/questoes.jsonl), [CSV](dados/questoes.csv), [tópicos JSONL](dados/topicos.jsonl) e [gabaritos JSONL](dados/gabaritos.jsonl).
- [Cobertura e contagens](dados/relatorio.json), [validação estrutural](dados/validacao.json) e [pendências](dados/pendencias.jsonl).
- [Manifesto dos documentos](execucoes/2026-10-29/documentos.json): caminhos, URLs, hashes SHA-256 e número de páginas.

Com Python e SQLite FTS5, a partir da pasta deste projeto:

```powershell
python base-questoes/consultar.py '"restos a pagar"' --banca FCC --limite 10
python base-questoes/consultar.py '"contabilidade pública"' --tipo topicos --limite 10
```

As consultas retornam JSONL e aceitam sintaxe MATCH do FTS5. `--disciplina` filtra a disciplina impressa identificada, quando disponível. O índice HTML pesquisa termos sem diferenciar acentos e exige todos os termos digitados; aspas agrupam uma expressão. Inclui número, identificação, cargo e especialidade na busca.

No SQLite, `questoes` guarda o conteúdo canônico, `ocorrencias` relaciona cada aparição ao caderno, `alternativas` e `contextos` preservam as partes do item. `classificacoes` e `questao_habilidade` guardam origem, confiança, evidência e estado de revisão. `topicos` mantém a hierarquia e o escopo dos editais. `fontes_visuais` permite conferir gráficos, tabelas e notação no original.

Para respostas, use `vw_gabaritos_referencia` junto com o histórico `vw_gabaritos_associados`. Seis itens têm publicações divergentes sem precedência definitiva confirmada; a visão retorna resposta nula e estado `divergente` nesses casos. `concordante` significa concordância das publicações disponíveis; consulte também `possui_publicacao_definitiva`. Não trate uma publicação preliminar como definitiva. Itens anulados mantêm sua situação e não servem para avaliar acerto do aluno.

Os 16.011 registros de gabarito incluem versões e outros cargos nos PDFs coletivos. Somente os registros com escopo compatível foram associados às 2.346 questões objetivas da biblioteca.

## Qualidade e trabalho restante

A revisão de 29/10/2026 isolou **84 ocorrências** em [quarentena](dados/quarentena_questoes.jsonl): alternativas vazias, segmentação inválida ou contaminação por material posterior à questão. O arquivo mantém cada registro, sua origem e o motivo; os PDFs e lotes originais foram preservados. Imagens usadas como alternativas sem transcrição também ficam na quarentena até recuperação. A exclusão da base ativa não significa que a questão original ou seu gabarito estejam errados. As regras são reaplicadas na consolidação.

Em 264 questões ESAF, as alternativas foram separadas do enunciado sem alterar a transcrição integral. Rótulos de disciplina reconhecidos como fragmentos de cabeçalho, equação ou alternativa foram retirados da indexação, com o valor anterior preservado em `disciplina_original_rejeitada`. A indexação FTS inclui explicitamente alternativas; os vínculos gerados do sistema de estudo foram recalculados e o histórico preservado. Os candidatos temáticos permanecem heurísticos e não foram verificados individualmente.


Há 2.243 ocorrências com estado `extraido` e 106 que pedem revisão por caracteres substituídos ou referências a elementos visuais. A imagem da página original está disponível em todos esses casos. `extraido` significa que o parser não sinalizou pendência estrutural; não significa conferência humana integral nem transcrição garantida de todas as fórmulas/gráficos.

A auditoria amostral encontrou fronteiras incorretas entre questões, rótulos contábeis confundidos com alternativas e uma página de coluna única processada como duas colunas. As correções estão em `revisar_questoes.py` e `reparar_ce.py`, com transcrição anterior e motivos preservados nos registros corrigidos. Cabeçalhos editoriais reconhecidos foram removidos do texto pesquisável.

544 ocorrências têm habilidades candidatas com evidência textual localizável; 1.805 continuam sem habilidade. A maioria das atribuições ainda vem de regras heurísticas e permanece pendente de revisão semântica. Há 17 atribuições da leitura individual Luna e cinco habilidades de três questões revisadas individualmente pelo coordenador. Evidência literal é um requisito de rastreabilidade, não uma garantia de que a classificação está correta. As classificações rejeitadas após correção das fronteiras permanecem nos lotes de origem e em `enriquecimento_rejeitado` no JSON das questões.

A frota Luna atingiu o limite de uso durante a leitura individual. A extração textual e a consolidação foram realizadas; o enriquecimento semântico individual não foi concluído. As filas atuais para retomada estão em [questões sem habilidade](dados/filas/questoes_sem_habilidade.jsonl), [revisão de conteúdo](dados/filas/questoes_revisao.jsonl) e [gabaritos divergentes](dados/filas/gabaritos_divergentes.jsonl). Use estas filas, pois os lotes anteriores à auditoria contêm fronteiras que já foram corrigidas.

As relações de cobrança direta, correlata e pré-requisito têm tabela própria (`associacoes_topico_questao`), ainda sem vínculos produzidos. O próximo passo é revisar e normalizar os conceitos/habilidades e executar esse relacionamento com evidências. Ainda não há recomendador, histórico de respostas do aluno ou diagnóstico de pontos fracos nesta base de conteúdo.

## Fundamentação do sistema de estudo

A [pesquisa sobre aprendizagem](../pesquisa-metodologia/FUNDAMENTACAO-CIENTIFICA.md) reúne as evidências e seus limites. O [desenho pedagógico do sistema](../pesquisa-metodologia/DESENHO-DO-SISTEMA.md) propõe o ciclo de estudo, os dados do estudante, a recomendação e a avaliação. São documentos de planejamento; o módulo de aprendizagem permanece separado deste catálogo de conteúdo.

## Reprodução

Preserve `biblioteca-concursos` ao lado de `base-questoes`, pois os links relativos do índice dependem dessa organização. Os caminhos SQLite/JSONL são absolutos nesta máquina.

Os lotes brutos da frota ficam em `execucoes/2026-10-29/lotes`, os caches de linhas PDF em `paginas` e os relatórios de cada extrator no mesmo diretório dos lotes. Para reaplicar a revisão e consolidar os arquivos existentes:

```powershell
python base-questoes/revisar_questoes.py
python base-questoes/revisar_habilidades.py
python base-questoes/consolidar.py
python base-questoes/gerar_indice.py
python base-questoes/validar.py
```

Os extratores originais usam `pdfplumber` e `pypdf`; a renderização usa Poppler. A consolidação e a consulta usam apenas a biblioteca padrão do Python. Não é necessário executar novamente os extratores para consultar a biblioteca.
