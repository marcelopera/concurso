# Planos externos

O aplicativo carrega planos JSON em runtime. O arquivo incluído em [plans/apofp-2026/roadmap.json](../plans/apofp-2026/roadmap.json) serve como referência de formato. Para instalar outro plano em um banco já inicializado, execute na raiz:

```sh
python -m estudo plan caminho/roadmap.json data/estudo/estudo.sqlite
```

O comando valida campos, datas, duração, IDs únicos e cobertura do calendário antes de modificar o progresso. Ele cria um backup SQLite e importa as aulas em uma transação. Repetir a importação preserva conclusões, sessões, materiais e seleções. Falhas de importação revertem todas as inserções parciais.

Use IDs de plano, tópico e aula próprios do pacote. Um ID de aula que já pertence a outro plano ou tópico é recusado. O mesmo ID de plano é imutável: uma configuração diferente precisa de outro identificador. O plano instalado mais recentemente aparece no roadmap; os demais registros continuam no banco.

Cada pacote contém `id`, `title`, `area`, `strategy`, `daily_minutes`, `exam_date`, `coverage_deadline`, `subjects`, `days` e `coverage.lessons`. Cada disciplina tem `subject_id`, `name` e `lessons`; as aulas têm `lesson_id`, `topic_id`, `topic`, `title`, `exam`, `scheduled_date` e `minutes`. `checklist`, `pages` e `source_url` são opcionais. Cada dia tem `date`, `phase`, `lessons`, `activities` e, opcionalmente, `review_lesson_ids`; atividades usam `id`, `title`, `detail` e `minutes`.

Para escolher o plano inicial, use `python -m estudo init --plan plans/outro/roadmap.json` ou defina `ESTUDO_PLAN_FILE` antes de `python -m estudo init`. Um banco existente é preservado. No Compose, `ESTUDO_PLAN` escolhe o nome da pasta do plano e `ESTUDO_PLANS_DIR` a coleção externa montada somente para leitura. A imagem não contém planos. Para mudar um plano já instalado, use `docker compose exec estudo python -m estudo plan /app/plans/outro/roadmap.json /app/data/estudo.sqlite`.
