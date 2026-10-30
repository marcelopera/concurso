# Pipeline privado de conteúdo

Instale na raiz com `python -m pip install -e ".[dev,extract]"`. O grupo `extract` declara pdfplumber, pypdf e jsonschema. Poppler (`pdftoppm` no PATH) é necessário apenas para `render`: Linux `poppler-utils`, macOS `brew install poppler`; no Windows instale Poppler e adicione seu diretório de executáveis ao PATH. Importar módulos não cria diretórios nem executa extrações.

```text
data/runs/<run-id>/
  documentos.json              # caminhos relativos à biblioteca
  lotes/                       # lotes brutos preservados
  correcoes_questoes.jsonl      # revisões completas opcionais
  paginas/                     # cache geométrico regenerável
  canonical/                   # snapshot JSONL revisado, fonte da verdade
  generated/                   # SQLite, CSV, HTML, filas e relatório
```

`data/` é privado e ignorado. `--run-id` é obrigatório; `--data-root` escolhe a área privada e `--library` (ou `BIBLIOTECA_DIR`) a biblioteca de PDFs. O manifesto é uma lista de documentos com `documento_id`, SHA-256, `tipo`, `banca`, `concurso`, `titulo`, `nome`, `paginas`, `url` e `arquivo` relativo à biblioteca. IDs de documento já publicados devem ser preservados.

Para importar a execução antiga, execute a partir da raiz:

```sh
python tools/import_legacy_pipeline.py ../concurso_codex/base-questoes/execucoes/2026-10-29 --run-id importacao-01
python -m concurso_pipeline review --run-id importacao-01
python -m concurso_pipeline build --run-id importacao-01
```

O importador recusa sobrescrever a execução, copia os lotes e verifica seus hashes contra os originais. Não modifica o arquivo privado antigo nem publica dados. A proveniência ausente é marcada explicitamente; o manifesto não transforma informações desconhecidas em conhecidas.

Para uma extração nova, forneça `documentos.json` e execute `cache`, `extract`, `syllabus` e `answers` separadamente com os mesmos argumentos de execução. `--board` pode ser repetido para selecionar bancas. O registry cobre Cebraspe, Fundatec, FCC, ESAF, Vunesp e FGV para questões. Os parsers de edital preservados cobrem os formatos/concursos configurados no código, e podem precisar de adaptação para novos documentos. Nenhum download da biblioteca é necessário ao aplicativo.

`review` aplica correções completas e enriquecimentos, rejeita duplicações ambíguas e valida os três contratos em [schemas](schemas/extraction-question.schema.json). Inferências sem evidência literal ficam em `enriquecimento_rejeitado`. `review --repair-ce` também reconstrói fronteiras C/E a partir do cache geométrico; revisões humanas posteriores prevalecem. Correções específicas e transcrições históricas permanecem nos dados privados, não no código.

`build` lê somente o snapshot canônico e executa `consolidate`, `index`, `validate` e `report`. Os PDFs não são necessários nessa etapa. O catálogo emite `schema_meta` e `user_version=1`, verifica chaves estrangeiras e conserva o algoritmo histórico de `ocorrencia_id`. O HTML usa o template versionado; seus links de PDFs dependem da biblioteca local, que continua opcional. `render` gera imagens sob demanda.

`generated/run.md` é o log por execução gerado de `relatorio.json`. Contagens privadas não são digitadas no README de produto. Uma execução pública e sintética está em [runs/pipeline-sintetico.md](runs/pipeline-sintetico.md). O estado real de uma extração privada deve ser consultado no relatório correspondente, não inferido a partir dos testes sintéticos.

Execute `python -m unittest discover -s tests/pipeline -v` ou `make test`. A CI testa PDFs originais sintéticos das seis bancas, contratos, portabilidade, duplicações, idempotência byte a byte e estabilidade de IDs após correções. As fixtures não incluem provas de terceiros.
