# Evidência de backup — issue #23

Execução privada em 30/10/2026, antes de qualquer limpeza histórica. A cópia foi gravada no destino local escolhido na [ADR 0002](../adr/0002-public-code-private-data.md), em `concurso_codex/backups/issue-23-20261030T211709Z/`. Manifestos SHA-256, lista integral de refs, saída de `git fsck`, configuração completa de proteção da `main` e relatório privado permanecem fora do repositório. Este documento contém apenas resultados resumidos.

O espelho do remoto contém 28 refs e `git fsck --full` terminou sem erros. A configuração da `main` foi consultada pela API antes de qualquer reescrita: proteção estrita com PR obrigatório, administradores sujeitos à regra, force-push e exclusão desativados e nove checks obrigatórios (`test` em Linux, Windows e macOS; `dependencies`; CodeQL para Python e JavaScript/TypeScript; `image`; `secrets`; e `CodeQL`). Nenhuma configuração remota foi alterada.

O snapshot separado contém 876 arquivos e 119 diretórios, totalizando 35.778.505 bytes. Seu manifesto foi calculado na origem, comparado com a cópia e recalculado na origem após a cópia. Um ensaio restaurou os 876 itens para uma pasta temporária e verificou novamente hashes, tamanhos, links simbólicos e diretórios, sem divergências. Credenciais locais, `.git`, dependências instaladas, caches e ferramentas de desenvolvimento foram excluídos; o histórico Git está no espelho separado. O destino é armazenamento local na mesma máquina, conforme a decisão aceita na ADR; não é uma cópia externa independente.

## Acervo e proveniência ainda ausentes

A varredura do checkout de origem não encontrou arquivos PDF, JSONL, SQLite, DB ou CSV, nem diretórios `base-questoes/`, `execucoes/` ou `sistema-estudo/dados/`. A busca por nomes de diretório associados ao acervo ficou limitada a seis níveis no ambiente local. `biblioteca-concursos/` existe vazia; `data/` contém 406 arquivos da compilação local da interface. As árvores de código `sistema-estudo/` e `concurso_pipeline/` foram incluídas no snapshot. Ele preserva os arquivos locais encontrados, inclusive os ignorados, mas essa árvore não contém o acervo histórico descrito na issue.

Não foi localizado o acervo original neste ambiente. Não há base para afirmar que lotes LLM, correções, enriquecimentos, metadados de proveniência, PDFs ou bancos de progresso foram preservados. A proveniência desses itens permanece desconhecida (`legacy-unrecorded`); nenhuma autoria, modelo, versão, prompt ou data foi inferida. A busca deste checkout não prova que uma fonte não exista em outro local.

Esta evidência comprova a integridade e a restauração do snapshot encontrado, não a completude do acervo. A issue permanece aberta até a fonte original ser localizada, copiada e verificada com ensaio de restauração próprio.
