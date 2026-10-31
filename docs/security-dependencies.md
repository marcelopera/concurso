# Auditoria das dependências Python

O workflow **Security** instala o workspace em um ambiente virtual temporário e audita os pacotes instalados com **pip-audit 2.10.1**. Ele roda em Linux e Windows com Python 3.12 para avaliar marcadores de plataforma, incluindo **tzdata** no backend Windows. A versão de bootstrap **pip==26.2** é fixada antes da instalação; isso mantém o gerenciador de build dentro do escopo auditado.

| Escopo | Raízes e dependências declaradas |
| --- | --- |
| Runtime | **packages/contracts**, **packages/pipeline** e **packages/estudo/backend**. Contratos não declara dependências externas; o pipeline usa **jsonschema**; o backend usa **tzdata** somente em Windows. As dependências transitivas resolvidas também entram no inventário. |
| Extração | O extra **extract** da raiz instala **concurso-pipeline[extract]**, incluindo **pdfplumber** e **pypdf** e suas transitivas. |
| Desenvolvimento | O extra **dev** da raiz inclui **ruff**, **jsonschema** (também usado em runtime) e **pip-audit**. O inventário inclui as transitivas dessas ferramentas. |
| Build | Todos os pyproject.toml usam **setuptools>=77** como backend de build. O extra de desenvolvimento instala **wheel>=0.45**; o ambiente também inclui o **pip==26.2** que instala as distribuições. Esses pacotes são auditados junto com os demais. |

O auditor varre o ambiente local completo. A validação trata como erro qualquer item ignorado que não seja um dos quatro pacotes editáveis deste repositório (**concurso**, **concurso-contracts**, **concurso-estudo** e **concurso-pipeline**): eles são código próprio, não dependências publicadas de terceiros. A verificação exige que todos os quatro apareçam com o motivo de exclusão esperado e falha para qualquer pacote ignorado adicional. Não há exceções de vulnerabilidade nem IDs ignorados; qualquer vulnerabilidade conhecida no inventário torna o job vermelho.

**tools/audit_python_dependencies.py** exige que o inventário contenha dependências sentinela dos escopos runtime, extração, dev e build, incluindo transitivas de **jsonschema** e da pilha PDF. Assim, a auditoria vazia obtida ao apontar somente para **packages/estudo/backend/requirements.txt** falha tanto no Linux como no Windows.

Cada execução publica **python-dependencies.json** como artefato do workflow. Ele contém sistema e versão Python, dependências e versões efetivamente analisadas, resultados do scanner e a lista explícita dos pacotes locais excluídos. Como a resolução pode variar entre sistemas e ao longo do tempo, o inventário é publicado por execução, não versionado como um lockfile.

Para reproduzir localmente na raiz, execute:

    python tools/audit_python_dependencies.py

O comando cria um ambiente virtual temporário isolado, resolve e audita os mesmos escopos, e grava o inventário em **build/security/python-dependencies.json**.
