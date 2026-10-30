# ADR 0004 — Pacotes instaláveis e fronteiras de persistência

Status: aceita para a refatoração solicitada na issue #1.

A estrutura anterior já separava parte dos serviços, mas o backend dependia de módulos soltos e do módulo do servidor. O pipeline buscava schemas e SQL em caminhos do checkout do aplicativo. Mover somente diretórios conservaria esses acoplamentos.

Adotamos `packages/pipeline/src/concurso_pipeline/` e `packages/estudo/backend/src/estudo/`, com metadados de distribuição e testes próprios; React fica em `packages/estudo/frontend/`. Um terceiro pacote pequeno, `packages/contracts/src/concurso_contracts/`, distribui os recursos versionados que produtor e consumidor do catálogo compartilham. Ele não contém casos de uso nem depende dos outros pacotes. Os três wheels são verificados em ambiente isolado, sem imports das instalações editáveis do checkout.

O backend recebe `Settings` em uma instância `Application`. O servidor mantém essa instância, e o contexto do perfil continua isolado por requisição. HTTP trata transporte, serviços tratam validações e transações, repositórios contêm SQL. A seleção de questões permanece um serviço de domínio. Um teste estático impede regressões nessas fronteiras.

Continuamos com a biblioteca padrão no runtime, além do contrato e de tzdata no Windows. Dependências de PDF pertencem somente ao grupo `extract` do pipeline. Não alteramos os contratos HTTP, IDs nem a migração SQL já publicada.

Planos JSON vivem em `plans/` e são carregados em runtime. A imagem é construída sem eles; Compose monta os planos somente para leitura. `deploy/` concentra a infraestrutura e a entrada Compose na raiz mantém o comando existente. Dados e builds ficam em `data/`, fora do Git. Os caminhos padrão são relativos ao diretório de execução, com alternativas explícitas por ambiente.

O volume Docker mantém seu nome e os mesmos nomes de bancos e perfis. Instalações locais podem selecionar a pasta antiga com `ESTUDO_DATA_DIR` antes de migrar seu conteúdo. Arquivos privados não são movidos automaticamente e migrações numeradas continuam preservando o progresso.

As decisões de dados públicos, backups privados, limpeza de histórico e release da [ADR 0002](0002-public-code-private-data.md) permanecem separadas desta reorganização. A implementação estrutural não encerra por si só a issue.
