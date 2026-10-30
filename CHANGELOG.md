# Alterações

## Não lançado (revisado em 2026-10-30)

`v0.1.0` ainda não foi publicada nem marcada. Esta seção descreve o conteúdo candidato; a data de publicação e os checksums só serão registrados depois que as dependências de backup e limpeza histórica forem concluídas. [#23](https://github.com/marcelopera/concurso/issues/23) e [#24](https://github.com/marcelopera/concurso/issues/24) bloqueiam a tag. [#25](https://github.com/marcelopera/concurso/issues/25) e [#26](https://github.com/marcelopera/concurso/issues/26) continuam acompanhando metadados do catálogo e a auditoria de dependências; [#27](https://github.com/marcelopera/concurso/issues/27) e [#28](https://github.com/marcelopera/concurso/issues/28) acompanham qualidade e testes de interface. A política e o gate estão em [docs/release.md](docs/release.md).

Para atualizar uma instalação anterior à reorganização, mantenha o volume Docker `estudo-dados` ou defina `ESTUDO_DATA_DIR=sistema-estudo/dados` antes de iniciar. Faça backup do banco de progresso, do registro de perfis e dos diretórios de perfil; migrações numeradas preservam o progresso existente. Detalhes em [Atualização e backup](README.md#atualização-e-backup).

Limitações conhecidas: PDFs e catálogo real não são distribuídos; a biblioteca externa é opcional. Os testes usam fixtures sintéticas e não atestam extração correta de todo formato de prova. O backend é local e não tem autenticação. Nenhum binário ou outro asset de release acompanha este changelog, portanto ainda não há checksums de artefatos publicados.

- Monorepo em pacotes instaláveis: pipeline, backend, frontend e contrato compartilhado, com planos externos e infraestrutura separados.
- Instâncias explícitas da aplicação, SQL em repositórios e serviços independentes do adaptador HTTP; regressões de fronteiras e de dois servidores simultâneos.
- CLI, Docker, CI e documentação adaptados; validação de wheels fora do checkout e preservação do volume de progresso.

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
