# Pendências da issue #1

## Refatoração estrutural da seção 5

A branch de refatoração parte da main com o PR #21 e preserva os simulados de provas completas. O código foi reorganizado em `packages/pipeline/`, `packages/estudo/backend/`, `packages/estudo/frontend/`, `plans/` e `deploy/`. Backend e pipeline têm distribuição, layout `src/` e testes próprios. `packages/contracts/` concentra os recursos compartilhados sem dependências entre aplicativo e pipeline.

HTTP adapta o transporte, serviços executam os casos de uso e repositórios contêm SQL. Cada servidor recebe sua própria instância `Application`; não há composição por `sys.modules`. Há verificações de dependências, regressão com dois servidores simultâneos e smoke de wheels fora do checkout. Makefile, CI, Docker, launcher e documentação usam a nova estrutura. Planos são montados em runtime e a imagem não os incorpora. A [ADR 0004](adr/0004-package-boundaries.md) documenta essas fronteiras.

As seções seguintes preservam a avaliação histórica das operações externas. A refatoração não executa limpeza de histórico, publicação de dados, alteração das configurações do GitHub ou release, e não encerra automaticamente a issue.

Referência: último comentário da issue, de 30/10/2026, após os PRs #2, #8 e #9. Esta avaliação distingue o que foi implementado neste PR das operações que o proprietário condicionou à aprovação e ao merge. A issue não deve ser encerrada automaticamente pelo PR.

## 1. Decisões

- Público apenas com código, documentação, planos redistribuíveis e fixtures sintéticas; dados de provas permanecem privados.
- Pipeline neste repositório, em `concurso_pipeline/`.
- JSONL revisado em `canonical/` como fonte da verdade; lotes originais preservados separadamente com SHA-256.
- Produto local genérico com planos externos, preservando as limitações dos parsers históricos.
- Reescrita autorizada para depois da aprovação e do merge. Backup no diretório irmão `concurso_codex`, escolhido pelo proprietário como substituição explícita ao pedido original de cópia fora da máquina.

Evidência: [ADR 0002](adr/0002-public-code-private-data.md).

## 2. Histórico e dados

O importador copia e verifica lotes sem modificar o arquivo histórico. Na execução privada de validação, o catálogo foi reconstruído com contratos e integridade válidos. A proveniência ausente é marcada `legacy-unrecorded`; modelo, versão, prompt e data desconhecidos não são inventados.

Um espelho do remoto e um snapshot local do checkout foram criados e verificados em 30/10/2026; a evidência resumida está em [backup da issue #23](runs/issue-23-backup-evidence.md). A busca não localizou o acervo privado original, então lotes, correções, enriquecimentos, proveniência, PDFs e bancos de progresso continuam sem cópia comprovada. Antes de qualquer limpeza, ainda são necessários localizar e verificar essa fonte, fazer um backup atualizado pós-merge, executar a reescrita/force-push autorizado, medir a redução num clone completo novo e tratar e-mails pessoais antigos. O [roteiro](history-cleanup.md) e o planejador de caminhos estão incluídos. O e-mail de novos commits locais já foi configurado como noreply; `package.json` declara MIT e autor.

A preservação local não equivale ao armazenamento externo durável originalmente pedido na issue. Essa diferença está registrada como decisão do proprietário. Recuperar a proveniência real dos lotes antigos continua pendente.

## 3. Pipeline

| Requisito | Implementação e verificação |
| --- | --- |
| Versionamento e dependências | Pacote instalado por `pyproject.toml`, grupo `extract` e wheel com schemas, SQL e template; Poppler documentado para renderização opcional. |
| CLI e registry | `python -m concurso_pipeline`, `--run-id` obrigatório, caminhos configuráveis e registry para as seis bancas; sem data de execução fixa nos módulos. |
| Normalização e IO | `common` concentra `norm` (NFKC + casefold), `clean`, `readjl`, `expected_count` e identidade histórica. Transcrições preservam caixa original. |
| Revisão | Estágio `review` aplica correções e enriquecimentos; `--repair-ce` incorpora a reconstrução geométrica. Correções manuais específicas ficam nos dados privados. |
| Testes golden | PDFs sintéticos originais para Cebraspe, Fundatec, FCC, ESAF, Vunesp e FGV, extraídos e consolidados contra resultados esperados. |
| Idempotência e IDs | Comparação de todos os derivados byte a byte entre dois builds; reconsolidação com texto corrigido preserva os IDs de ocorrência e o algoritmo anterior. |
| Contratos | Questões, tópicos e gabaritos validados por JSON Schema; fontes verificadas; catálogo com `schema_meta`, `user_version`, FKs e índices de busca. |
| Portabilidade | Manifesto e dados com caminhos relativos à biblioteca; teste executa a CLI em outro diretório, sem PDFs para o build canônico. |
| Derivados e documentação | SQLite/CSV/HTML/filas/relatórios fora do Git; template próprio; `report` gera log por execução a partir de `relatorio.json`; [guia](pipeline.md), [execução sintética](runs/pipeline-sintetico.md) e [ADR histórica](adr/0003-content-and-recommendation.md). |

Os parsers de edital preservados ainda têm regras específicas dos concursos originais. Os testes sintéticos não demonstram extração correta de todo novo formato nem substituem revisão semântica de conteúdo real. O downloader opcional não foi adicionado: a biblioteca continua opcional ao aplicativo.

## 4. Qualidade de baixa prioridade

README e Makefile usam `inicializar.py` e `python -m estudo`. unittest foi mantido. Migração para pytest/TypeScript, testes de componentes com Vitest/Testing Library, Prettier, limiar numérico de cobertura e supressão dos avisos `use client` permanecem melhorias posteriores. Conforme o comentário da issue, esta seção não bloqueia seu encerramento.

## 5. GitHub

Aplicado e conferido por API em 30/10/2026: proteção da `main` com PR obrigatório, checks estritos de CI e Security, admins sujeitos à regra, exclusão e force-push bloqueados; secret scanning, push protection e private vulnerability reporting ativados; descrição e topics preenchidos.

Checks exigidos: `test (ubuntu-latest)`, `test (windows-latest)`, `test (macos-latest)`, `dependencies`, `codeql (python)`, `codeql (javascript-typescript)`, `image`, `secrets`. Não se exige aprovação formal de outro colaborador em um repositório pessoal; o parecer Astra é entregue ao proprietário.

A primeira release `v0.1.0` fica para o commit com histórico limpo. Publicar agora também criaria uma referência para o histórico que ainda contém os dados removidos da árvore.

## 6. Conferência do PR #9

Na main `a5d327f`, CI e Security passaram. `server.py` tem 192 linhas e compõe serviços; Vite está em devDependencies, Node tem engines e tzdata é declarado para Windows. Compose usa filesystem somente leitura, cap_drop ALL e no-new-privileges; há um único `.gitignore`. Os checks deste novo PR precisam passar novamente e seus links constam na descrição do PR.

O encerramento completo depende das operações pós-merge da seção 2 e da release, além da proveniência que for recuperável. O PR entrega as correções de código e registra as exceções aprovadas sem apresentar essas etapas futuras como concluídas.
