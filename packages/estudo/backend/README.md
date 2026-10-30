# Backend de estudo

Pacote Python instalável `concurso-estudo`, com módulos em [src/estudo/](src/estudo/). Consulte o [README principal](../../../README.md) para instalação, execução e migração de dados locais.

O runtime depende do [contrato compartilhado](../../contracts/) e de tzdata no Windows. Não depende do pipeline, de bibliotecas PDF, do diretório do frontend nem de um plano específico. HTTP, serviços, repositórios e migrações têm fronteiras verificadas em testes.

Depois de instalar os pacotes, execute na raiz do repositório:

```sh
python -m estudo init --plan plans/apofp-2026/roadmap.json
python -m estudo
```

`python -m estudo --help` descreve inicialização, servidor, importação de plano e backup/restauração. `python -m estudo.mapping --plan plans/apofp-2026/roadmap.json --apply` executa a vinculação opcional APOFP. As configurações usam `ESTUDO_DATA_DIR`, `ESTUDO_DB`, `ESTUDO_CONTENT_DB`, `ESTUDO_DIST_DIR`, `ESTUDO_PLAN_FILE`, `ESTUDO_PORT` e `BIBLIOTECA_DIR`.

As [regressões](tests/) usam catálogo sintético e dados temporários: execute `python packages/estudo/backend/tests/run_demo_suite.py` na raiz. O catálogo é somente leitura e o progresso usa migrações numeradas; preserve bancos e registros de todos os perfis ao migrar instalações.
