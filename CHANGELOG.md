# Alterações

## Não lançado

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
