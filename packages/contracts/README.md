# Contrato do catálogo

Pacote instalável `concurso-contracts`, compartilhado por backend e pipeline sem depender deles. Distribui [JSON Schemas](src/concurso_contracts/schemas/), [SQL do catálogo](src/concurso_contracts/catalog/esquema.sql), [validador de compatibilidade](src/concurso_contracts/catalog/contrato.py) e [catálogo fictício](src/concurso_contracts/catalog/criar_demo.py).

Os recursos são acessados com `concurso_contracts.resource_file`, inclusive fora do checkout. Os nomes e IDs dos schemas são preservados; alterações do contrato exigem coordenação entre produtor e consumidor. Consulte o [contrato de dados](../../docs/data-contract.md).
