# Pipeline de questões

Pacote instalável `concurso-pipeline`, com código em [src/concurso_pipeline/](src/concurso_pipeline/) e [testes sintéticos](tests/). Depende do [contrato compartilhado](../contracts/), sem importar o aplicativo de estudo.

Na raiz, `make setup` instala os pacotes e o grupo opcional de extração. `python -m concurso_pipeline --help` mostra a CLI; `make pipeline PIPELINE_ARGS="build --run-id minha-execucao"` gera os derivados de um snapshot canônico revisado. Veja o [guia completo](../../docs/pipeline.md) para biblioteca, Poppler, proveniência e importação de dados históricos.

`python -m unittest discover -s packages/pipeline/tests -v` executa extração golden por banca, revisão, contratos, reconsolidação e estabilidade de IDs. Entradas e saídas ficam em `data/runs/<run-id>/`, fora do Git.
