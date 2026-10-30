# Alterações

## Não lançado

- Pipeline versionado com CLI por execução, extratores por banca, normalização comum, JSONL canônico e revisão explícita.
- Geração de SQLite, CSV, HTML e relatório a partir do canônico, contratos de questões/tópicos/gabaritos e testes sintéticos das seis bancas.
- Importação verificável dos lotes históricos, preservação dos IDs de ocorrência e roteiro de limpeza do histórico após o merge.
- Decisões sobre dados e escopo registradas; unificação da execução local com o Makefile.

- Adaptador HTTP com tabela de rotas e erros centralizados; serviços de catálogo, aulas e sessões e conexões separados.
- Validação estrutural do catálogo, JSON Schema de questões e manifestos privados com SHA-256.
- Planos externos com validação, backup e importação transacional que preserva progresso.
- Hook de rascunhos e fila de salvamento testada; lint Python/JS, testes de API e E2E em três sistemas na CI.
- Contexto Docker inclui migrações; imagens base por digest, smoke test e workflows de segurança.
- Correção de dependências transitivas do quadro identificadas pela auditoria.
- Caminhos de perfis derivados do registro local, com verificação de contenção após resolver links simbólicos.

- Separação dos dados e arquivos de processamento; catálogo fictício para instalações limpas.
- Biblioteca opcional fora da imagem Docker; resolução portátil e leitura de PDFs por intervalos.
- Melhorias de testes, documentação, carregamento do quadro e tratamento de erros.
