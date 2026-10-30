# Sistema de estudo local

Aplicativo de estudo em português, inspirado no protótipo de referência. O servidor e os dados ficam no computador; o endereço local é `http://127.0.0.1:8765`.

## Executar e distribuir com Docker

Instale e inicie o Docker Desktop (ou Docker Engine com Compose). No terminal, entre na pasta que contém `sistema-estudo`, `base-questoes`, `biblioteca-concursos` e `compose.yaml`, e execute:

```powershell
docker compose up -d --build
```

A biblioteca de PDFs não é versionada no Git. Em uma cópia obtida do repositório, coloque `biblioteca-concursos` ao lado das demais pastas antes de construir a imagem; os caminhos e nomes dos arquivos devem corresponder aos registrados no catálogo. Como alternativa, use uma imagem Docker já construída e distribuída separadamente.

Abra [http://127.0.0.1:8765](http://127.0.0.1:8765). A primeira compilação baixa as imagens e dependências. O container inclui a interface, o catálogo de questões, os PDFs e um banco inicial com as 94 aulas e seus vínculos, sem copiar o progresso pessoal existente no computador. A imagem usa Linux e não exige Node ou Python instalados na máquina de destino.

Os perfis e o progresso ficam no volume Docker `estudo-dados`. Reiniciar ou recriar o container com `docker compose up -d` preserva esse volume; a imagem atualizada não substitui o banco já existente. Para parar e voltar a iniciar:

```powershell
docker compose stop
docker compose up -d
```

Para fazer backup de todos os perfis, pare o serviço e copie a pasta do container; depois, volte a iniciá-lo:

```powershell
docker compose stop
docker compose cp estudo:/app/sistema-estudo/dados ./backup-estudo
docker compose up -d
```

Não use `docker compose down -v` se quiser preservar os dados: essa opção remove o volume. Os dados usados pelo launcher Windows e os do container são independentes.

Para distribuir a imagem pronta sem exigir o código-fonte na outra máquina, depois da compilação execute:

```powershell
docker save -o sistema-estudo.tar sistema-estudo:local
```

Na máquina de destino, com Docker instalado, carregue o arquivo e inicie um container com volume persistente:

```powershell
docker load -i sistema-estudo.tar
docker run -d --name sistema-estudo --restart unless-stopped -p 127.0.0.1:8765:8765 -v estudo-dados:/app/sistema-estudo/dados sistema-estudo:local
```

O endereço continua sendo `http://127.0.0.1:8765`. A aplicação é voltada ao uso local, sem autenticação; a porta é publicada somente no próprio computador.

Se a porta 8765 estiver ocupada, no PowerShell defina outra antes de iniciar o Compose:

```powershell
$env:ESTUDO_PORTA = '8876'
docker compose up -d --build
```

Nesse caso, acesse `http://127.0.0.1:8876` e mantenha a variável definida ao executar outros comandos Compose. Para usar `docker run` com outra porta, defina a mesma porta interna e externa: `-e ESTUDO_PORT=8876 -p 127.0.0.1:8876:8876`.

## Iniciar no Windows

1. Compile a interface uma vez (e depois de alterar o código):

   ```powershell
   pnpm install
   pnpm run build
   ```

2. Execute `iniciar.ps1` ou rode:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\iniciar.ps1
   ```

O launcher inicia o servidor Python em segundo plano, ligado somente a `127.0.0.1`, e abre o navegador. Para encerrá-lo:

```powershell
powershell -ExecutionPolicy Bypass -File .\iniciar.ps1 -Stop
```

Para acompanhar mensagens do servidor em uma janela de terminal, inicie manualmente:

```powershell
& 'C:\Users\marce\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\server.py
```

O Vite 8 usado no build requer Node.js 20.19 ou mais recente; o ambiente de implementação usa Node.js 24 e pnpm. O servidor da aplicação usa a biblioteca padrão do Python, sem FastAPI ou Uvicorn.

## Dados e conteúdo

### Perfis locais e reset do roadmap

A caixa **Perfil de estudo**, no topo, permite criar um perfil apenas com um nome e alternar entre os perfis. A seleção fica lembrada no navegador. O perfil **Principal** conserva todos os dados anteriores; novos perfis começam com progresso zerado e uma cópia das aulas, materiais e vínculos do Principal. Cada perfil mantém suas próprias sessões, respostas, anotações, cartões e revisões. Saia da sessão antes de trocar de perfil. São perfis locais, sem senha ou sincronização.

**Resetar progresso do roadmap**, abaixo da barra de progresso, abre uma confirmação com o nome do perfil. O reset zera as aulas e atividades do plano e apaga suas sessões, respostas, anotações, dificuldades, cartões e revisões. Mantém o conteúdo das aulas, materiais, vínculos, questões livres, aulas pessoais fora do plano e demais perfis. Antes da operação, o servidor cria uma cópia SQLite `*-antes-reset-*.sqlite` ao lado do banco do perfil.

O Principal continua em `dados/estudo.sqlite`; o cadastro fica em `dados/estudo-perfis.sqlite` e os demais bancos em `dados/estudo-perfis/`. Para fazer backup de todos os perfis, encerre o servidor e copie toda a pasta `dados`. Com `ESTUDO_DB`, o cadastro e a pasta de perfis usam o nome e a localização desse banco. Alterações futuras no catálogo do Principal não são replicadas automaticamente nos perfis já criados.

Os testes `tests/test_profiles.py` verificam persistência, isolamento, validação e reset em bancos temporários. `node tests/verify-profiles-ui.cjs` verifica criação, troca, recarregamento, sessão, confirmação/cancelamento e layout móvel em uma instância temporária, sem alterar os dados reais.

### Roadmap APOFP SP 2026 · A01

O plano de Orçamento e Finanças Públicas está cadastrado no banco de estudo: 94 aulas, 52 dias e 4 horas diárias, de 29/10 a 19/12/2026. A prova está prevista para 20/12/2026, conforme o Edital 02/2026. A primeira passagem por todo o conteúdo está planejada até 10/12.

Na tela **Roadmap**, **Plano diário** mostra as aulas, revisões, prática, treino discursivo e simulados. **Conteúdo do edital** permite buscar disciplinas e filtrar P1/P3 ou P2/A01. Cada aula mostra o trecho correspondente do Anexo II, a data prevista e a quantidade de questões vinculadas. A conclusão de uma sessão atualiza o progresso das aulas; as demais atividades têm marcação própria.

A vinculação percorreu as 2.433 ocorrências de todas as seis bancas: 1.953 ocorrências compatíveis geraram 2.687 vínculos em 90 aulas. Quatro aulas permanecem sem correspondência segura. Consulte a cobertura, as lacunas e os motivos de exclusão em `roadmaps/apofp-2026/vinculacao/README.md`; `auditoria-toda-base.jsonl` registra todas as ocorrências, inclusive as 480 não vinculadas. A classificação é temática, por regras explícitas e evidências, com 46 casos revisados individualmente em `revisoes.json`; não houve conferência humana integral de todas as questões.

Em **Ver aula**, pesquise a coleção completa e abra **Ler enunciado e conferir vínculo** para ver a evidência e o trecho do edital. A lista tem paginação e filtro de itens corrigíveis. Questões correlatas, referências normativas históricas, extração pendente, anulações e gabaritos sem definitivo conservam seus avisos. Apenas itens extraídos, válidos e com gabarito definitivo concordante são corrigidos automaticamente.

Cada nova sessão seleciona até 12 conteúdos distintos: prioriza itens corrigíveis ainda não respondidos e depois erros e revisões mais antigas, considerando o histórico em todas as aulas. A seleção separa pré-teste, recuperação e prática, evita repetições do mesmo conteúdo e é preservada ao retomar a sessão. A coleção completa de questões permanece na aula. As propostas discursivas ficam para consulta e adaptação ao formato do APOFP.

O plano completo, as fontes e a cobertura estão em `roadmaps/apofp-2026/README.md` e `roadmaps/apofp-2026/roadmap.json`. A importação foi aditiva e criou uma cópia de segurança em `dados/estudo-antes-roadmap-*.sqlite`. Para importar em outro banco já inicializado, execute `roadmap.py --install caminho/do/banco.sqlite` com o Python do runtime.

Os testes de cobertura, carga horária, importação e persistência podem ser executados com `tests/test_roadmap.py`. `tests/verify-roadmap-ui.cjs` confere o servidor ativo em 8765 no Edge e grava capturas de desktop e celular em `roadmaps/apofp-2026/evidencias`.

- Dados de estudo ficam em `dados\estudo.sqlite`: disciplinas, tópicos, aulas, vínculos explícitos, materiais, sessões, respostas, cartões e revisões.
- O banco `..\base-questoes\dados\conteudo.sqlite` é aberto com SQLite `mode=ro`. O sistema não grava nele.
- PDFs só são servidos se o caminho resolvido estiver dentro de `..\biblioteca-concursos` e o arquivo existir. A aplicação permite links HTTP/HTTPS e PDFs locais dessa biblioteca; não faz upload de arquivos.
- As fontes do quadro Excalidraw são servidas de `public\fonts`. Como o pacote também acrescenta uma URL de CDN à lista de fontes mesmo quando existe um caminho local, o build aplica uma transformação pontual ao chunk de fontes do Excalidraw para remover somente esse fallback externo. A transformação exige encontrar o trecho esperado exatamente uma vez; se o pacote mudar, o build falha para revisão.
- Na execução local, o servidor aceita conexões apenas em `127.0.0.1`. No container, ele escuta na rede interna do Docker e a configuração publica a porta somente em `127.0.0.1`. Não há sincronização ou conta de usuário.
- Para fazer cópia de segurança de todos os perfis, encerre o servidor e copie a pasta `dados` inteira.

## Critério de correção e limitações

- Por padrão, o catálogo mostra ocorrências com gabarito concordante, situação válida, publicação definitiva identificada e extração concluída. Desative o filtro para consultar as demais ocorrências; elas recebem aviso e não são avaliadas automaticamente.
- A avaliação é calculada no servidor por ocorrência. Cada tentativa conserva a resposta e o snapshot do gabarito e do status daquela data.
- A base não fornece comentários explicativos para as questões. A aplicação mostra o resultado disponível e as fontes de gabarito associadas, sem criar comentários.
- As questões do roadmap A01 foram vinculadas com evidências, por solicitação do usuário. Para aulas pessoais, selecione as ocorrências do catálogo. Os vínculos continuam editáveis; salvar uma seleção mantém os metadados de correspondência dos itens conservados.
- Cartões criados ao fechar uma aula vencem no dia seguinte. As respostas “Errei”, “Difícil” e “Fácil” alteram o agendamento entre intervalos de 1, 3 e 7 dias, usando a data local de São Paulo.
- O cronômetro apresenta durações sugeridas por etapa e não impede continuar. A cena do Excalidraw é salva no banco de estudo, incluindo elementos, estado serializável e arquivos incorporados.

## Comandos de manutenção

Recalcular a auditoria temática sem alterar o banco: execute `map_questions.py` com o Python do runtime. Para adicionar os vínculos no banco de estudo com backup: `map_questions.py --apply`. A reaplicação retira somente correspondências geradas que deixaram de ser aceitas pela classificação; as seleções manuais e o histórico são preservados. A base de conteúdo continua aberta somente para leitura. Os testes de integridade, evidências, importação e sessões estão em `tests/test_question_mapping.py`.

Reconstruir a interface:

```powershell
pnpm run build
```

Usar outra porta:

```powershell
& 'C:\Users\marce\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\server.py --port 8876
```

Usar um banco de estudo temporário (por exemplo, para uma verificação isolada sem tocar nos dados locais):

```powershell
$env:ESTUDO_DB = Join-Path $env:TEMP 'sistema-estudo-validacao.sqlite'
& 'C:\Users\marce\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\server.py --port 8876
Remove-Item Env:\ESTUDO_DB
```

`ESTUDO_DB` escolhe o arquivo do banco de estudo, e `--port` substitui a porta padrão. O launcher sempre usa o banco normal em `dados\estudo.sqlite` e a porta `8765`.
