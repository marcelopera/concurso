# Avaliação da issue #1

Revisão do estado posterior aos PRs #2 e #8, com complementos deste PR. Esta página distingue correções do aplicativo de trabalho ainda necessário no pipeline e no histórico. A issue continua aberta.

| Item | Estado e evidência |
| --- | --- |
| P0.1/P0.2 — clone limpo e caminhos | Catálogo fictício, biblioteca opcional, variáveis de ambiente e testes portáveis já existiam. A CI agora procura caminhos pessoais e inicia a imagem; o contexto Docker passa a incluir as migrações SQL. |
| P0.3/P0.4 — dados e licença | A árvore atual contém código, plano e fixtures sintéticas com MIT e política de dados separada. Há ferramenta de manifesto com SHA-256 e proveniência, e atributos de dados gerados. A limpeza do histórico e o armazenamento externo dos lotes continuam pendentes. |
| P1.1 — contratos e planos | A abertura do catálogo valida estrutura e versão, com compatibilidade legada. Há JSON Schema v1 de questões, validação na CI e importação transacional de planos externos. O teste de estabilidade de IDs após reconsolidação ainda depende do pipeline. |
| P1.2 — backend | Configuração, conexões, migrações, serviços de catálogo/aulas/sessões e adaptador HTTP com tabela de rotas. Exceções/status centralizados; detalhes internos não chegam em 5xx. Etapas vêm do servidor; a porta efetiva substitui a mutação global. Os módulos de planos e mapeamento usam a migração central em vez de duplicar DDL. |
| P1.3 — frontend | Telas por feature, Excalidraw sob demanda e versão exata já existiam. Agora há hook de persistência, componente de revisão separado, testes da fila de salvamento, ESLint e correções de hooks. O transform de fontes é documentado, validado no build e no E2E. TypeScript permanece uma alternativa futura. |
| P1.4 — pipeline | Ainda fora da árvore pública, preservado em `concurso_codex`, diretório irmão. Não foi convertido em pacote, nem teve normalização unificada, CLI por execução ou testes por banca. O schema e o manifesto são infraestrutura; não substituem essa migração. |
| P1.5 — testes | Fixtures temporárias e testes de API cobrem respostas, restrições de sessão, persistência, conclusão idempotente, SRS, contratos, backup e importação de planos. Cinco testes históricos específicos do catálogo privado permanecem opcionais. E2E configurado nos três sistemas operacionais; evidências são artefatos da CI. Mantido unittest para evitar uma migração de framework sem ganho de cobertura. |
| P2.1 — qualidade | Ruff, ESLint, testes JS/Python, JSON Schema, links, caminhos e arquivos grandes na CI. Workflow de auditoria de dependências, CodeQL, Trivy e Gitleaks; Dependabot para pip e hooks pre-commit; CODEOWNERS e templates. Proteção de branch e recursos de segurança do GitHub dependem de configuração do repositório. |
| P2.2/P2.3 — ambiente | `pyproject.toml`, `.python-version`, engines e pnpm fixos, bases Docker por digest e Compose endurecido. Makefile usa a suíte sintética e tem lint; comandos equivalentes sem Make estão documentados para Windows. |
| P2.4 — documentação | Arquitetura, contrato, glossário e ADR presentes. Contagens privadas não são copiadas para o README. Descrição/topics do GitHub e documentação histórica do pipeline não são alteradas por este PR. |
| P3.1 — robustez | Streaming por intervalos, CSP documentada e backup/restore já existiam; testes exercitam essas garantias. Erros internos têm mensagem genérica e a CI examina segredos nas alterações. |

Para concluir integralmente a issue ainda é necessário:

- Preparar backup espelho, definir o plano de reescrita e executar a limpeza do histórico com coordenação de clones e branches; este PR não faz force-push.
- Recuperar a proveniência real dos lotes antigos, escolher armazenamento privado durável e verificar os manifestos antes de qualquer distribuição.
- Migrar o pipeline preservado para um pacote portátil: normalização e IO comuns, CLI com run ID, extratores por banca, template separado e testes sintéticos de regressão/idempotência/IDs. Os scripts privados atuais não são apresentados como reproduzíveis.
- Validar os outros registros do contrato histórico (tópicos e gabaritos) com schemas e fixtures ao migrar o pipeline.
- Configurar proteção da main e metadados do repositório, decidir a primeira release e confirmar a política para dados históricos. Uma release de catálogo privado não deve ser publicada como efeito colateral de um PR de código.

As validações locais e o resultado dos workflows deste PR ficam na descrição do PR. Docker e E2E em Linux/macOS são verificados pela CI; o ambiente local desta alteração é Windows.
