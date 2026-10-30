# Planos externos

O aplicativo carrega planos JSON em runtime. O arquivo incluído em `sistema-estudo/roadmaps/apofp-2026/roadmap.json` serve como referência de formato. Para instalar outro plano em um banco já inicializado, execute dentro de `sistema-estudo/`:

```sh
python -m estudo plan caminho/roadmap.json dados/estudo.sqlite
```

O comando valida campos, datas, duração, IDs únicos e cobertura do calendário antes de modificar o progresso. Ele cria um backup SQLite e importa as aulas em uma transação. Repetir a importação preserva conclusões, sessões, materiais e seleções. Falhas de importação revertem todas as inserções parciais.

Use IDs de plano, tópico e aula próprios do pacote. Um ID de aula que já pertence a outro plano ou tópico é recusado. O mesmo ID de plano é imutável: uma configuração diferente precisa de outro identificador. O plano instalado mais recentemente aparece no roadmap; os demais registros continuam no banco.

Cada pacote contém `id`, `title`, `area`, `strategy`, `daily_minutes`, `exam_date`, `coverage_deadline`, `subjects`, `days` e `coverage.lessons`. Cada disciplina tem `subject_id`, `name` e `lessons`; as aulas têm `lesson_id`, `topic_id`, `topic`, `title`, `exam`, `scheduled_date` e `minutes`. `checklist`, `pages` e `source_url` são opcionais. Cada dia tem `date`, `phase`, `lessons`, `activities` e, opcionalmente, `review_lesson_ids`; atividades usam `id`, `title`, `detail` e `minutes`.

Para mudar o plano usado na inicialização de bancos novos, defina `ESTUDO_PLAN_FILE` antes de executar `scripts/inicializar.py`. Essa variável não substitui o plano de um banco existente. No Docker, monte o JSON em um volume somente leitura e defina a variável com o caminho dentro do contêiner; instale no banco existente com o comando acima. A imagem continua contendo o plano de exemplo para instalações sem arquivos externos.
