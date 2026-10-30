# Primeira release `v0.1.0`

**Status em 2026-10-30: não publicada.** Não criar tag ou release até cumprir todos os gates abaixo. A issue [#29](https://github.com/marcelopera/concurso/issues/29) acompanha esta entrega; o backup privado e a limpeza do histórico são tratados separadamente em [#23](https://github.com/marcelopera/concurso/issues/23) e [#24](https://github.com/marcelopera/concurso/issues/24).

As evidências ainda não satisfazem os gates: o acervo original não está disponível neste ambiente para provar o backup; o PR preparatório #34 reduziu um clone descartável de 137 MiB para 2,2 MiB, sem alterar refs públicas, mas mantém cinco caminhos ambíguos e não validou o mailmap real. A mudança de metadados de #25 no PR #32 está tecnicamente aprovada e tem nove checks verdes, mas ainda não foi incorporada à `main`. As melhorias de qualidade #27 e #28 têm PRs #35 e #33 abertos, ainda fora da `main`; se continuarem pendentes, devem ser declaradas como limitações da release. A release deve ser reavaliada contra o SHA final da `main`, depois que os gates obrigatórios forem resolvidos.

## Política de versões

`vMAJOR.MINOR.PATCH` identifica uma versão do repositório e do aplicativo local. Os projetos Python — `concurso`, `concurso-contracts`, `concurso-pipeline` e `concurso-estudo` — são versionados em conjunto; os metadados atuais são `0.1.0`. A tag do repositório não publica automaticamente pacotes no PyPI ou npm. O `package.json` do frontend é metadado de build do aplicativo, não um artefato npm desta release; seu número não determina a versão da release. Qualquer publicação separada de pacote exigirá uma política própria e explícita.

## Gates antes da tag

1. **Backup privado verificado.** Concluir [#23](https://github.com/marcelopera/concurso/issues/23): espelho do remoto íntegro, snapshot separado do acervo privado, manifesto SHA-256 comparado à fonte e destino, e ensaio de restauração concluído. Guardar a evidência fora do repositório. A existência de ferramentas ou de um clone do código não prova backup do acervo.
2. **Histórico público limpo.** Concluir [#24](https://github.com/marcelopera/concurso/issues/24) somente depois do backup. Revisar todas as refs, verificar que caminhos e objetos privados não permanecem alcançáveis, validar as identidades do mailmap, restaurar a proteção da `main` e registrar `git fsck` e a medição de um clone completo novo. Guardar a evidência da limpeza fora do repositório.
3. **SHA candidato exato.** Escolher explicitamente o SHA no topo da `main` protegida depois da limpeza. Confirmar que o commit contém as notas e documentação finais e que seu histórico não contém caminhos de dados proibidos. Não usar um SHA anterior ou de uma branch de preparação.
4. **Checks verdes para esse mesmo SHA.** Ler a lista de checks requeridos da proteção real da `main` e confirmar cada um no SHA candidato. Na auditoria de 2026-10-30, a lista era `test (ubuntu-latest)`, `test (windows-latest)`, `test (macos-latest)`, `dependencies`, `codeql (python)`, `codeql (javascript-typescript)`, `image`, `secrets` e `CodeQL` agregado. Os três jobs `test` incluem os testes E2E; o CI também constrói e exercita a imagem no Linux. A lista pode mudar: checks novos também são obrigatórios, e ausência de status não equivale a sucesso. Resolver separadamente a lacuna auditada em [#26](https://github.com/marcelopera/concurso/issues/26). Se as issues de qualidade [#27](https://github.com/marcelopera/concurso/issues/27) e [#28](https://github.com/marcelopera/concurso/issues/28) ainda estiverem abertas, registrar seus limites na release.
5. **Conteúdo público revisado.** A release inicial contém código, documentação, planos redistribuíveis e fixtures sintéticas. Não anexar PDFs, transcrições, catálogo real, lotes, screenshots privados, bancos de progresso ou outros dados pessoais/privados. Conferir a árvore e todo o histórico alcançável, não só o diretório atual. O runtime e a imagem devem funcionar sem biblioteca externa; confirmar os checks E2E, imagem e smoke do próprio SHA candidato. Se arquivos públicos forem anexados futuramente, calcular e registrar SHA-256 a partir dos arquivos efetivamente publicados.
6. **Migração e limites comunicados.** Rever as notas em [CHANGELOG.md](../CHANGELOG.md) e as instruções de [backup e atualização](../README.md#atualização-e-backup). A atualização mantém o volume Docker existente; em instalação local antiga, `ESTUDO_DATA_DIR=sistema-estudo/dados` seleciona a pasta anterior ou o usuário copia todo o conteúdo, com o servidor parado. Fazer backup do banco de progresso, registro de perfis, diretórios dos perfis e catálogo privado. Migrações numeradas preservam o progresso existente. PDFs são opcionais e não distribuídos; fixtures sintéticas não garantem extração correta de novos formatos; o backend local não tem autenticação.

## Verificação read-only

Depois que ambos os arquivos de evidência existirem **fora da árvore do repositório**, execute a partir de um checkout limpo da `main`, substituindo o SHA e os caminhos pelos valores reais:

```sh
python tools/check_release_candidate.py <sha-completo-da-main> \
  --backup-evidence /caminho/privado/backup-verificado.json \
  --cleanup-evidence /caminho/privado/limpeza-verificada.json \
  --confirm-no-private-assets
```

O verificador só lê Git e a API do GitHub: exige clone completo (não raso), SHA explícito igual ao HEAD remoto de `main`, árvore de trabalho limpa, ausência de caminhos que a política de limpeza classifica como privados, evidências não vazias fora do repositório, confirmação de ausência de assets privados e sucesso de todos os status checks atualmente requeridos. A pessoa responsável ainda deve revisar o conteúdo das evidências e a lista dos assets. O comando não cria nem publica refs. Somente após sucesso e revisão humana a tag `v0.1.0` pode apontar para esse mesmo SHA; registrar a data e checksums reais na release/changelog.
