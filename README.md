# Sistema de estudo para concursos

Aplicativo local para organizar aulas, estudar questões e acompanhar revisões. O frontend é React/Vite; o servidor Python usa SQLite para o progresso e consulta um catálogo de questões em somente leitura.

## Executar com Docker

Com Docker e Compose instalados, execute na raiz:

```sh
docker compose up --build
```

Acesse <http://127.0.0.1:8765>. O progresso fica no volume `estudo-dados`. O sistema cria um catálogo de demonstração com questões fictícias na primeira execução. A biblioteca de PDFs é opcional: coloque os arquivos em `biblioteca-concursos/` ou defina `BIBLIOTECA_DIR` no ambiente do Compose. Ela é montada somente para leitura e nunca é copiada para a imagem.

Para usar um catálogo privado no Docker, copie-o para o volume e reinicie o serviço: `docker compose cp caminho/conteudo.sqlite estudo:/app/sistema-estudo/dados/conteudo.sqlite` e `docker compose restart estudo`. A atualização do catálogo não altera o banco de progresso; conserve IDs de ocorrências para manter os vínculos existentes.

Ao atualizar uma instalação antiga, preserve o volume de progresso e copie o catálogo privado para ele. Até isso ser feito, o catálogo fictício não contém as questões associadas ao progresso anterior.

## Execução local

Requisitos: Python 3.10 ou superior (no Windows instale `tzdata` com `python -m pip install tzdata`), Node.js 22.13 ou superior e pnpm 11.25.0.

```sh
cd sistema-estudo
pnpm install --frozen-lockfile
pnpm run build
python scripts/preparar_container.py
python server.py
```

O preparo instala o plano em um banco novo e importa vínculos privados quando disponíveis; ele se recusa a sobrescrever um banco existente. Para iniciar com um banco vazio sem instalar o plano, execute `python server.py` diretamente. Para desenvolvimento, use `pnpm dev` com o servidor Python em execução na porta 8765; o Vite encaminha as chamadas `/api` para ele. Testes: `python -m unittest discover -s tests -v`.

`ESTUDO_DB` seleciona o banco de progresso, `ESTUDO_CONTENT_DB` o catálogo e `BIBLIOTECA_DIR` a biblioteca local. O servidor não possui autenticação: use-o somente na própria máquina e não exponha sua porta a redes externas.

Para salvar um banco de progresso, execute `python -m estudo backup dados/estudo.sqlite backup.sqlite` dentro de `sistema-estudo`. Para restaurar, pare o servidor e use `python -m estudo restore backup.sqlite dados/restaurado.sqlite`; inicie com `ESTUDO_DB` apontando para o arquivo restaurado. Cada comando recusa sobrescrever um arquivo existente. Os bancos de outros perfis e o registro de perfis também precisam ser copiados separadamente.

## Organização

- `sistema-estudo/`: aplicativo, plano e testes.
- `sistema-estudo/catalogo/`: esquema e gerador do catálogo fictício.
- `sistema-estudo/dados/conteudo.sqlite`: catálogo privado opcional, ignorado pelo Git.
- `biblioteca-concursos/`: acervo opcional local, ignorado pelo Git.
- `concurso_codex/`, diretório irmão: pipeline de extração, lotes, auditorias e evidências preservados da execução anterior. Os scripts históricos do pipeline precisam ser adaptados antes de serem executados a partir do novo local.

Os dados de terceiros ficam fora da versão atual do repositório. A remoção de arquivos do estado atual não os remove do histórico Git; consulte [DATA-LICENSE.md](DATA-LICENSE.md).
