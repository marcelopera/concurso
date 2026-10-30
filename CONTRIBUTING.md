# Contribuição

Instale as versões indicadas no [README](README.md). Na raiz, `make setup`, `make lint` e `make test` preparam e validam o projeto; `make build` compila a interface. Para E2E, execute `pnpm exec playwright install chromium` e `pnpm run test:e2e` em `sistema-estudo/`.

Use dados fictícios nos testes e diretórios temporários para toda gravação. Não adicione catálogos, provas ou bancos de progresso ao Git. Documente mudanças de esquema, acrescente migrações numeradas sem editar as já publicadas e confirme `git diff --exit-code` depois dos testes em uma árvore limpa. A suite padrão independe dos dados privados; os testes históricos específicos desse catálogo são opcionais.

Identificadores novos usam inglês; textos da interface e termos das fontes permanecem em português. Consulte o [glossário](docs/glossary.md) e a [decisão de arquitetura](docs/adr/0001-local-runtime.md).

Opcionalmente instale `pre-commit` (`python -m pip install pre-commit` e `pre-commit install`). Os hooks verificam Python, YAML, conflitos, espaços e arquivos grandes; o lint JavaScript continua em `make lint` e na CI.
