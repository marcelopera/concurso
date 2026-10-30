# Contrato de dados

O catálogo SQLite é somente leitura. O esquema gerado para a demonstração está em `sistema-estudo/catalogo/esquema.sql`: usa `PRAGMA user_version=1`, tabela `schema_meta` e os relacionamentos entre questão, ocorrência, prova e gabarito. O servidor aceita catálogos legados de versão zero e rejeita versões superiores a 1. Uma ocorrência identifica a presença de uma questão em uma prova: o progresso usa esse ID, portanto catálogos substitutos devem mantê-lo estável. A aplicação não modifica o catálogo ao importá-lo.

O banco de progresso usa `PRAGMA user_version` e `schema_migrations`. A versão 1 registra o esquema inicial e reconhece bancos legados com versão zero, mantendo seus dados; versões futuras desconhecidas são rejeitadas. Faça backup antes de atualizar. Não há chave estrangeira entre os dois bancos, por isso a compatibilidade de IDs é responsabilidade da produção do catálogo.
