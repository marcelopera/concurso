# Preparação para limpeza do histórico

Este roteiro e as ferramentas associadas apenas planejam e validam uma limpeza. Nenhuma delas altera refs remotas. A autorização do proprietário já registrada permite a reescrita somente depois da aprovação e do merge deste PR e da conclusão de #23 com backup completo verificado. Esses pré-requisitos ainda não foram cumpridos, então a operação pública permanece bloqueada neste PR.

## Pré-requisitos e cópias

1. Concluir #23: localizar a fonte original, preservar seus dados em cópia separada e verificar a restauração. Um clone do Git não substitui a cópia dos arquivos ignorados.
2. Depois de cumprir a autorização registrada, interromper gravações e registrar os SHAs remotos de cada branch e tag. Conferir separadamente refs de PRs, caches e configurações que `git clone --mirror` não cobre.
3. Usar o destino local escolhido pelo proprietário: o diretório irmão `concurso_codex/backups/<identificador>/`. Essa cópia local substitui explicitamente o pedido anterior de uma cópia fora da máquina. Validar nela um espelho Git com `git fsck --full` e inventário de refs, além de um snapshot separado dos dados privados. Criar outra cópia para a reescrita; nunca filtrar o único backup.
4. Criar e verificar manifestos SHA-256 com `tools/dataset_manifest.py` para a fonte antes da cópia e para o snapshot restaurado. Manter o original intacto; hashes comprovam igualdade, não autoria, licença ou proveniência.
5. Salvar fora dos repositórios o estado exato da proteção da `main`, incluindo os checks configurados. Não alterar a proteção durante este PR.

## Plano privado de caminhos

Execute a ferramenta em um espelho de trabalho separado. O plano e a lista de caminhos podem revelar nomes internos, por isso são criados fora do clone, sem sobrescrita e com modo `0600` em POSIX. Não os adicione ao GitHub nem a um comentário público.

```sh
python tools/history_cleanup_plan.py /caminho/para/espelho /tmp/plano-antes.json \
  --base-ref refs/heads/main --paths-output /tmp/caminhos-para-remover.txt
```

A ferramenta captura os SHAs de todas as refs, o inventário de caminhos históricos e um resumo por hash da árvore atual. Caminhos de `base-questoes/dados/`, `biblioteca-concursos/`, `sistema-estudo/dados/`, diretórios de execuções/evidências/fontes visuais e formatos de dados conhecidos são propostos para remoção. PDFs, mídia e arquivos compactados fora dessas áreas, fixtures e código/documentação em diretórios de dados ficam como candidatos ambíguos até revisão humana; o plano não os remove automaticamente.

Revise `review_paths` no arquivo privado. Para cada candidato, crie uma decisão local com ação `remove` ou `keep` e justificativa; por exemplo:

```json
{
  "version": 1,
  "decisions": [
    {"path": "docs/example.png", "decision": "keep", "reason": "Imagem pública da documentação."}
  ]
}
```

Proteja esse arquivo com permissão `0600` em POSIX e gere novamente o plano e a lista:

```sh
python tools/history_cleanup_plan.py /caminho/para/espelho /tmp/plano-revisado.json \
  --base-ref refs/heads/main --decisions-file /tmp/decisoes.json \
  --paths-output /tmp/caminhos-para-remover.txt
```

Só prossiga quando `unresolved_review_paths` estiver vazio e a lista integral tiver sido revisada independentemente. O planejamento falha em caminhos que não podem ser representados com segurança como uma entrada por linha.

## Mailmap privado e ensaio

Monte uma lista privada explícita apenas com pares de nome/e-mail confirmados como identidades do proprietário, a partir de uma fonte confiável. Não inferir propriedade só pelo nome do commit, não incluir outras pessoas ou bots e não publicar a lista. O utilitário confirma que cada par ocorre como autor, committer ou tagger e gera um mailmap exato em arquivo privado:

```json
{
  "version": 1,
  "identities": [
    {"name": "Nome confirmado localmente", "email": "alias@exemplo.invalid"}
  ]
}
```

```sh
python tools/history_cleanup_mailmap.py /caminho/para/espelho /tmp/identidades.json /tmp/mailmap.txt \
  --canonical-name "Nome canônico" --canonical-email "00000000+usuario@users.noreply.github.com"
```

Depois da revisão independente do plano, da lista e do mailmap, aplique-os somente na cópia de trabalho descartável:

```sh
git -C /caminho/para/espelho filter-repo \
  --invert-paths --paths-from-file /tmp/caminhos-para-remover.txt \
  --mailmap /tmp/mailmap.txt --replace-refs delete-no-add
```

Não use `push --mirror`. Confira os SHAs de todas as branches e tags contra o inventário anterior, a árvore de código preservada e a ausência dos caminhos removidos. Gere um clone completo novo do resultado e execute:

```sh
python tools/history_cleanup_validate.py /caminho/para/clone-novo \
  /tmp/plano-revisado.json --mailmap /tmp/mailmap.txt /tmp/relatorio-validacao.json
```

O relatório compara cada SHA anterior e posterior, verifica refs novas/ausentes, caminhos, a aplicação exata do mailmap, `git fsck --full`, objetos inalcançáveis, clone raso e o hash da árvore atual preservada. Também mede o armazenamento antes/depois; o alvo de dezenas de MB é uma expectativa, não um resultado presumido. Mantenha planos, listas, mailmaps e relatórios fora do repositório.

## Atualização remota e proteção

Antes de qualquer envio, repita a comparação dos SHAs com `git ls-remote`; pare se qualquer ref mudou desde o inventário. Envie cada branch e tag com seu SHA antigo esperado, incluindo `--force-with-lease=<ref>:<sha-antigo>` quando suportado. Revise cada ref individualmente e não exclua refs novas. Trate refs de PR e caches separadamente com o GitHub; atualizar branches e tags não comprova que esses objetos desapareceram.

Se a proteção impedir a migração, um administrador deve registrar a configuração completa e os checks imediatamente antes de qualquer exceção. Prepare a restauração a partir desse registro antes de alterá-la; restaure a configuração no primeiro encerramento, inclusive após falha ou interrupção, e compare o estado restaurado com o registro antes de liberar novas gravações. Se não for possível confirmar a restauração, mantenha a pausa e corrija a proteção antes de continuar.

Após a atualização, crie outro clone completo do remoto, repita a validação, examine objetos grandes remanescentes e registre medições reais e verificações independentes. Oriente a substituição dos clones antigos para evitar reintrodução de objetos. Só então atualize a issue e registre a primeira release de código `v0.1.0` no commit limpo, sem assets privados. Proveniência, integridade do backup, limpeza de refs e disponibilidade de cópias em PRs/caches são evidências distintas e devem ser registradas separadamente.
