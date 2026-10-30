# ADR 0001 — Aplicativo local e fronteiras de dados

Status: aceita para o aplicativo atual.

O produto funciona localmente, sem autenticação, com PDFs opcionais e catálogo somente leitura. Mantemos o backend na biblioteca padrão do Python e adicionamos um adaptador HTTP com tabela explícita de rotas. Isso conserva a instalação pequena e dá uma localização única para status e erros. Os serviços recebem as dependências da composição em `server.py`; as conexões e migrações pertencem a `estudo/db/`.

O código novo usa identificadores em inglês; UI e transcrições de fontes usam português. Os nomes portugueses no contrato SQLite permanecem para compatibilidade com os dados existentes.

O frontend permanece em JavaScript com ESLint e regras de hooks. O salvamento tem uma fila serial testada. O Excalidraw está fixado na versão 0.18.1; mantemos o transform específico no build porque o aplicativo serve fontes localmente e a CSP impede a CDN de fallback. Há guardas para o chunk e para o conteúdo esperado, além de E2E que abre o quadro sem requisições externas. Atualizar o editor exige revisar essa adaptação. A remoção futura desse transform em favor de um patch do pacote é uma alternativa, sem mudar o contrato do usuário.

Código, planos e fixtures sintéticas são versionados. Dados de terceiros e artefatos da execução histórica permanecem privados, separados do aplicativo. O JSON Schema formaliza o registro de questão; o manifesto local protege a integridade das saídas insubstituíveis sem inventar proveniência ausente. Reintroduzir o pipeline como pacote exige uma migração própria, com fixtures por banca e testes de estabilidade de IDs.

Reescrever o histórico, publicar datasets e criar releases têm consequências fora da árvore de um PR. Essas operações continuam registradas como pendências na [avaliação da issue](../issue-1-status.md).
