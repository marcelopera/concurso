# ADR 0002 — Código público, dados privados e planos externos

Status: aceita pelo proprietário em 30/10/2026; execução da limpeza histórica após aprovação e merge deste PR.

O repositório permanece público apenas com código, documentação, planos redistribuíveis e fixtures sintéticas. Provas, transcrições, imagens de fontes e lotes gerados por agentes permanecem privados. A licença MIT do código não autoriza distribuir esses dados.

O pipeline vive neste repositório, no pacote `concurso_pipeline`. O aplicativo é uma ferramenta local genérica com planos externos; não é limitado ao concurso do plano de exemplo. Os extratores preservam regras específicas dos formatos históricos e não prometem cobrir qualquer edital de uma banca.

A fonte da verdade de cada execução é o snapshot JSONL revisado em `canonical/`, acompanhado de `documentos.json`. SQLite, CSV, HTML, filas e relatórios são derivados. Os lotes brutos, correções e enriquecimentos são preservados separadamente para auditoria e reconstrução do snapshot, com manifesto SHA-256. Alterar uma transcrição não deve alterar o ID de ocorrência existente.

O proprietário escolheu o diretório irmão `concurso_codex` como destino do backup. Trata-se de armazenamento privado local, uma exceção explícita ao pedido original da issue por cópia fora da máquina. A recuperação dos metadados reais de modelo, versão, prompt e data continua dependendo dos registros originais. Metadados desconhecidos ficam nulos com estado `legacy-unrecorded`; não se inventa proveniência.

A reescrita do histórico foi autorizada para depois da aprovação e do merge. Ela exige backup espelho e cópia privada verificados antes de trocar refs remotas. O [roteiro de migração](../history-cleanup.md) mantém essa operação separada do PR, incluindo restauração da proteção da main e verificação de branches, tags e clones antigos.
