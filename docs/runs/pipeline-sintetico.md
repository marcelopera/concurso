# Execução sintética do pipeline

Origem: fixtures originais do projeto em `tests/pipeline/`. Não contém material de provas nem saída de LLM.

O teste golden gera um PDF por banca, extrai, revisa, consolida e verifica o conteúdo contra `fixtures/golden.json`. O teste de reconstrução compara todos os arquivos derivados byte a byte entre duas execuções. Depois aplica uma correção textual e confere os IDs contra o algoritmo histórico.

As estatísticas de cada execução são geradas de `generated/relatorio.json` pelo comando `report`, em `generated/run.md`. Arquivos temporários são removidos ao terminar os testes. Os resultados locais e da CI são registrados no PR; este documento não afirma cobertura integral dos formatos reais de uma banca.
