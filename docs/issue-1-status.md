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

Ainda pendentes para depois do merge: backup espelho e snapshot privado no destino escolhido, verificação dos manifestos das cópias, reescrita/force-push, redução medida num clone completo novo e remoção de e-mails pessoais antigos. O [roteiro](history-cleanup.md) e o planejador de caminhos estão incluídos. O e-mail de novos commits locais já foi configurado como noreply; `package.json` declara MIT e autor.

A preservação local não equivale ao armazenamento externo durável originalmente pedido na issue. Essa diferença está registrada como decisão do proprietário. Recuperar a proveniência real dos lotes antigos continua pendente.

Estado das dependências da release em 30/10/2026: não há prova de backup completo do acervo privado. O PR preparatório #34 ensaia a limpeza em clone descartável e mede 137 MiB para 2,2 MiB, mas ainda há cinco caminhos ambíguos e o mailmap real não foi validado; nenhuma ref pública foi alterada. O trabalho do PR #32 para #25 tem aprovação técnica e nove checks verdes, mas ainda não está na `main`. Esses resultados preparatórios não satisfazem os gates de [release](release.md).

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

README e Makefile usam `inicializar.py` e `python -m estudo`. unittest foi mantido. A issue [#27](https://github.com/marcelopera/concurso/issues/27) acompanha fixtures públicas e limiar de cobertura (PR #35 aberto, ainda não incorporado); [#28](https://github.com/marcelopera/concurso/issues/28) acompanha testes de componentes React e formatação (PR #33 aberto, ainda não incorporado). São melhorias de qualidade posteriores, não pré-requisitos da primeira release; declare-as como pendências se continuarem abertas no SHA publicado.

## 5. GitHub

Aplicado e conferido por API em 30/10/2026: proteção da `main` com PR obrigatório, checks estritos de CI e Security, admins sujeitos à regra, exclusão e force-push bloqueados; secret scanning, push protection e private vulnerability reporting ativados; descrição e topics preenchidos.

Checks exigidos pela proteção da `main`: `test (ubuntu-latest)`, `test (windows-latest)`, `test (macos-latest)`, `dependencies`, `codeql (python)`, `codeql (javascript-typescript)`, `image`, `secrets` e o check agregado `CodeQL`. Os três jobs `test` também executam E2E; o job `image` verifica a imagem e o smoke test confirma que ela inicia sem PDFs. A lista deve ser lida da proteção real da branch no momento da release, sem presumir que um check ausente está verde. A lacuna conhecida no escopo da auditoria Python está em [#26](https://github.com/marcelopera/concurso/issues/26); um check verde não resolve esse defeito por si só. Não se exige aprovação formal de outro colaborador em um repositório pessoal; o parecer técnico é entregue ao proprietário.

A release/tag `v0.1.0` permanece não publicada. Ela depende do backup privado comprovado em [#23](https://github.com/marcelopera/concurso/issues/23) e da limpeza/revisão das refs públicas em [#24](https://github.com/marcelopera/concurso/issues/24). O rastreamento do catálogo e a auditoria de dependências seguem em [#25](https://github.com/marcelopera/concurso/issues/25) e [#26](https://github.com/marcelopera/concurso/issues/26). A checklist, a política de versões e o gate read-only estão em [docs/release.md](release.md) e [tools/check_release_candidate.py](../tools/check_release_candidate.py). O gate exige SHA explícito no HEAD remoto protegido, checks requeridos verdes e evidências locais de backup e limpeza; não cria tag nem release.

## 6. Conferência do PR #9

Na main `a5d327f`, CI e Security passaram. `server.py` tem 192 linhas e compõe serviços; Vite está em devDependencies, Node tem engines e tzdata é declarado para Windows. Compose usa filesystem somente leitura, cap_drop ALL e no-new-privileges; há um único `.gitignore`. Os checks deste novo PR precisam passar novamente e seus links constam na descrição do PR.

O encerramento completo depende das operações pós-merge da seção 2 e da release, além da proveniência que for recuperável. Os desdobramentos de #1 são [#23](https://github.com/marcelopera/concurso/issues/23), [#24](https://github.com/marcelopera/concurso/issues/24), [#25](https://github.com/marcelopera/concurso/issues/25), [#26](https://github.com/marcelopera/concurso/issues/26), [#27](https://github.com/marcelopera/concurso/issues/27), [#28](https://github.com/marcelopera/concurso/issues/28) e [#29](https://github.com/marcelopera/concurso/issues/29). Este documento registra pendências e evidências sem apresentar etapas futuras como concluídas.
