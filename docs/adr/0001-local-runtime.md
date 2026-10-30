# ADR 0001 — Aplicativo local e fronteiras de dados

Status: aceita para o aplicativo atual.

O produto funciona localmente, sem autenticação, com PDFs opcionais e catálogo somente leitura. Mantemos o backend na biblioteca padrão do Python e adicionamos um adaptador HTTP com tabela explícita de rotas. Isso conserva a instalação pequena e dá uma localização única para status e erros. Os serviços recebem as dependências da composição em `server.py`; as conexões e migrações pertencem a `estudo/db/`.

O código novo usa identificadores em inglês; UI e transcrições de fontes usam português. Os nomes portugueses no contrato SQLite permanecem para compatibilidade com os dados existentes.

O frontend permanece em JavaScript com ESLint e regras de hooks. O salvamento tem uma fila serial testada. O Excalidraw está fixado na versão 0.18.1; mantemos o transform específico no build porque o aplicativo serve fontes localmente e a CSP impede a CDN de fallback. Há guardas para o chunk e para o conteúdo esperado, além de E2E que abre o quadro sem requisições externas. Atualizar o editor exige revisar essa adaptação. A remoção futura desse transform em favor de um patch do pacote é uma alternativa, sem mudar o contrato do usuário.

Código, planos e fixtures sintéticas são versionados. Dados de terceiros e artefatos da execução histórica permanecem privados, separados do aplicativo. O JSON Schema formaliza o registro de questão; o manifesto local protege a integridade das saídas insubstituíveis sem inventar proveniência ausente. A migração do pipeline para pacote, fixtures por banca e estabilidade de IDs está descrita na [ADR 0002](0002-public-code-private-data.md).

Reescrever o histórico e criar a primeira release ficam para depois da aprovação e do merge, conforme a [avaliação da issue](../issue-1-status.md). Datasets privados não serão publicados como parte dessa operação.
