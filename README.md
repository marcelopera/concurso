# Sistema de estudo para concursos

Aplicativo local para organizar aulas, estudar questões e acompanhar revisões. O frontend é React/Vite; o servidor Python usa SQLite para o progresso e consulta um catálogo de questões em somente leitura.

## Executar com Docker

Com Docker e Compose instalados, execute na raiz:

```sh
docker compose up --build
```

Acesse <http://127.0.0.1:8765>. O progresso fica no volume `estudo-dados`. O sistema cria um catálogo de demonstração com questões fictícias na primeira execução. A biblioteca de PDFs é opcional: coloque os arquivos em `biblioteca-concursos/` ou defina `BIBLIOTECA_DIR` no ambiente do Compose. Ela é montada somente para leitura e nunca é copiada para a imagem.

Para usar um catálogo privado no Docker, copie-o para o volume e reinicie o serviço: `docker compose cp caminho/conteudo.sqlite estudo:/app/sistema-estudo/dados/conteudo.sqlite` e `docker compose restart estudo`. A atualização do catálogo não altera o banco de progresso; conserve IDs de ocorrências para manter os vínculos existentes.

O catálogo de demonstração contém apenas exercícios fictícios de aritmética e não inclui correspondências automáticas com as aulas do plano. Para vinculá-los manualmente, abra uma aula, escolha **Selecionar do catálogo** e salve a seleção. Questões livres não são vinculadas automaticamente às aulas.

Para vincular questões compatíveis de um catálogo privado ao plano APOFP após copiá-lo e reiniciar o serviço, execute:

```sh
docker compose exec estudo python map_questions.py --apply
```

O comando cria um backup do progresso no volume e registra evidências para os vínculos gerados por regras temáticas; revise as correspondências na aula. Ele preserva vínculos manuais e o histórico, mas substitui vínculos gerados anteriormente que deixaram de corresponder. Execute novamente após atualizar o catálogo. Sem `--apply`, o comando apenas gera a auditoria em `dados/vinculacao/`. A vinculação automática aplica-se somente ao plano APOFP; para outros planos, selecione as questões na própria aula.

Ao atualizar uma instalação antiga, preserve o volume de progresso e copie o catálogo privado para ele. Até isso ser feito, o catálogo fictício não contém as questões associadas ao progresso anterior.

## Execução local

Requisitos: Python 3.10 ou superior (no Windows instale `tzdata` com `python -m pip install tzdata`), Node.js 22.13 ou superior e pnpm 11.25.0.

```sh
cd sistema-estudo
pnpm install --frozen-lockfile
pnpm run build
python scripts/inicializar.py
python -m estudo
```

A inicialização instala o plano apenas quando ainda não existe progresso e preserva bancos existentes. Para iniciar com um banco vazio sem instalar o plano, execute `python -m estudo` diretamente. Para desenvolvimento, use `pnpm dev` com o servidor Python em execução na porta 8765; o Vite encaminha as chamadas `/api` para ele.

Para preparar o ambiente de desenvolvimento e validar o projeto, execute na raiz:

```sh
make setup
make lint
make test
make run
```

`make run` compila a interface e inicializa o plano apenas quando ainda não existe progresso. No Windows sem Make, os comandos equivalentes são `python -m pip install -e ".[dev,extract]"` e `python -m unittest discover -s tests/pipeline -v` na raiz e, dentro de `sistema-estudo/`: `pnpm install --frozen-lockfile`, `pnpm run lint`, `pnpm test`, `python tests/run_demo_suite.py`, `pnpm run build`, `python scripts/inicializar.py` e `python -m estudo`. As suítes usam dados temporários e sintéticos, mesmo quando há dados privados na máquina.

Os testes de navegador usam `pnpm exec playwright install chromium` e `pnpm run test:e2e`, dentro de `sistema-estudo/`. A CI executa lint, contrato JSON Schema, testes Python/JS, build e E2E em Linux, macOS e Windows; no Linux também inicia a imagem Docker e verifica a ausência de PDFs. `make lint` verifica caminhos pessoais, tamanho dos arquivos e links locais da documentação.

`ESTUDO_DB` seleciona o banco de progresso, `ESTUDO_CONTENT_DB` o catálogo e `BIBLIOTECA_DIR` a biblioteca local. O servidor não possui autenticação: use-o somente na própria máquina e não exponha sua porta a redes externas.

Para salvar um banco de progresso, execute `python -m estudo backup dados/estudo.sqlite backup.sqlite` dentro de `sistema-estudo`. Para restaurar, pare o servidor e use `python -m estudo restore backup.sqlite dados/restaurado.sqlite`; inicie com `ESTUDO_DB` apontando para o arquivo restaurado. Cada comando recusa sobrescrever um arquivo existente. Os bancos de outros perfis e o registro de perfis também precisam ser copiados separadamente.

## Organização

- `sistema-estudo/`: aplicativo, plano e testes.
- `sistema-estudo/catalogo/`: esquema e gerador do catálogo fictício.
- `sistema-estudo/dados/conteudo.sqlite`: catálogo privado opcional, ignorado pelo Git.
- `biblioteca-concursos/`: acervo opcional local, ignorado pelo Git.
- `concurso_pipeline/`: extratores por banca, revisão e geração do catálogo; veja o [guia do pipeline](docs/pipeline.md).
- `data/`: entradas privadas por execução, JSONL canônico e arquivos gerados; ignorado pelo Git.
- `concurso_codex/`, diretório irmão: arquivo privado da execução anterior, preservado sem alterações. O importador verifica hashes dos lotes copiados.

Os dados de terceiros ficam fora da versão atual do repositório. A remoção de arquivos do estado atual não os remove do histórico Git; consulte [DATA-LICENSE.md](DATA-LICENSE.md).

Consulte a [arquitetura](docs/architecture.md), o [contrato de dados](docs/data-contract.md), os [planos externos](docs/plan-packs.md) e a [avaliação das pendências da issue #1](docs/issue-1-status.md).
