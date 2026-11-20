# Aulas pela interface (F1) — design

**Data:** 2026-11-20 · **Pedido:** "pense numa forma de podermos gerar aulas através da GUI (hj creio que so via
comando bash)". A proposta em duas etapas foi aprovada no mesmo dia ("Quero sim. Aprovado").

## Como é hoje

- Uma aula só nasce no terminal. `sotawhat lessons make --tema "…"` (ou `--auto`) roda tudo de uma vez: fontes,
  roteiro, storyboard, voz, cenas 3D, checagem, vídeo e envio ao Telegram.
- As aulas 6 a 8, medidas, levaram de 9 a 18 min de produção e custaram de US$ 0,10 a 0,56. O grosso do custo é a
  voz: cerca de 3.300 créditos da ElevenLabs, US$ 0,55 ao preço do plano.
- A aba Aulas só lê. Quando uma aula para, o card manda rodar `sotawhat lessons resume N` no terminal.

## O fluxo

1. **Nova aula.** Tema livre ou uma das sugestões da semana, ligado opcionalmente a até 3 entidades do grafo, com
   modelos "econômico" ou "equilibrado". "Planejar roteiro" leva de 2 a 4 min e US$ 0,01 a 0,02. Nenhum crédito de
   voz.
2. **Revisão.** O card mostra o roteiro (cenas com a narração, quiz e o que a checagem de fatos achou) e a
   estimativa: duração, cenas 3D, créditos de voz, custo e tempo de produção, ao lado dos créditos que restam na
   ElevenLabs. Ações: "Produzir aula" (com a caixa "enviar ao Telegram ao terminar"), "Refazer roteiro",
   "Descartar".
3. **Produção em segundo plano.** O card mostra as etapas: as feitas com o tempo que levaram, a atual com o tempo
   corrido e as que faltam com a previsão. Mostra também o tempo total e as últimas linhas do log, com
   "Cancelar". A página pode ser fechada.
4. **Depois.**
   - Aula pronta: o vídeo aparece no card. Se ela ainda não foi enviada, aparece "Enviar ao Telegram".
   - Aula que parou (erro, cancelamento ou processo que sumiu): o card mostra onde e por quê, com "Retomar".

## Decisões

1. **Um caminho de código.** A interface roda o mesmo comando do terminal, `python -m sotawhat.cli lessons …`, num
   processo próprio. Não há um segundo motor para manter, e a aula continua se a interface reiniciar.
   - Uma aula nova é criada pela interface (a linha em `lessons`). Depois vem `lessons resume N --so-roteiro`.
     Assim o card existe desde o primeiro segundo.
   - "Produzir" e "Retomar" são `lessons resume N`. As etapas já feitas ficam em cache, como hoje.
   - "Refazer roteiro" é `lessons resume N --refazer plano --so-roteiro`. A interface apaga o roteiro guardado no
     banco antes, para que um "Retomar" depois de uma falha nunca produza sem revisão.
   - "Enviar ao Telegram" é `lessons send N`.
2. **Sair do job da tarefa agendada.** A interface roda pelo Agendador de Tarefas, dentro de um job object do
   Windows (conferido com `IsProcessInJob`), e parar a tarefa encerra o job inteiro.
   - O processo da aula é criado com `CREATE_BREAKAWAY_FROM_JOB`. Se o job não permitir, a criação cai para o modo
     normal, e a tarefa registra que a aula não sobrevive a um reinício da interface.
   - O processo também leva `CREATE_NO_WINDOW`: um console oculto, herdado pelo node, pelo Chrome e pelo FFmpeg, sem
     janelas piscando.
   - Usa `python.exe`, não `pythonw.exe`, para a saída ir para o log. O log vai em UTF-8 e sem buffer.
3. **Uma tarefa por vez, interface e terminal.** O estado fica no banco, na tabela `lesson_jobs` (schema 8), e não
   em arquivo: o Windows recusa substituir um arquivo que outro processo está lendo.
   - Cada tarefa tem ação (`roteiro`, `aula` ou `envio`), origem, estado, etapa atual, lista de etapas, pid, log e
     batimento.
   - Estados: `iniciando`, `rodando`, `concluida`, `falhou`, `cancelada`, `interrompida`.
   - O processo da aula reescreve `beat_at` a cada 5 s. Tarefa viva = `iniciando`/`rodando` com batimento de até
     30 s.
   - O pedido de uma tarefa nova abre uma transação `BEGIN IMMEDIATE`: confere que não há tarefa viva e insere a
     sua. Dois cliques, ou interface e terminal ao mesmo tempo, não produzem duas aulas.
   - Uma tarefa sem batimento conta como interrompida. A próxima tarefa a marca assim e fecha o run que ela deixou
     aberto.
   - A interface insere a tarefa como `iniciando`, com um token aleatório, e passa `--job TOKEN` ao processo. O
     processo a adota (`rodando`, com o próprio pid). Se o token não existe mais (cancelada antes de começar), ele
     sai sem fazer nada.
   - Pelo terminal, `lessons make/resume/hf/send` também registra a tarefa. Se houver outra viva, o comando recusa e
     diz qual é.
4. **Cancelar encerra a árvore.** `taskkill /PID <pid> /T /F` leva o node, o Chrome e o FFmpeg junto. Depois de o
   processo sumir:
   - a tarefa vira `cancelada`;
   - a aula vira `falhou`, com "cancelada na interface (etapa X)";
   - o run aberto é fechado.
   O que já foi pago (roteiro, voz de cenas prontas) fica em cache, e "Retomar" não paga de novo.
5. **O motor anuncia as etapas.** `run_motion_lesson(progress=…)` chama `attach(aula)`, `expect([...])` e
   `stage(nome)`:
   - as etapas são `roteiro`, `storyboard`, `voz`, `3d` (só com cenas `mechanism3d`), `checagem`, `video` e `envio`
     (só com envio);
   - o `log` da tarefa guarda a última linha, que vira o motivo quando o comando sai com erro.
   `until="roteiro"` para depois do roteiro: grava o custo do LLM até ali em `llm_usd`, que o teto da aula desconta
   na produção, e fecha o run. Sem as checagens de HyperFrames, FFmpeg e chave da ElevenLabs, que só a produção usa.
   O modo (econômico ou equilibrado) fica no relatório, e "Produzir" usa o mesmo.
6. **Estimativa da revisão** (`lessons/estimate.py`). Constantes medidas nas aulas 6 a 8, com a origem no código:

   | Etapa | Estimativa | Medido |
   |---|---|---|
   | duração do vídeo | caracteres da narração ÷ 12,9 por s | 2.694 → 208,8 s; 3.253 → 251,9 s |
   | créditos de voz | caracteres × 1,013 | 2.730 de 2.694; 3.295 de 3.253 |
   | storyboard | ~120 s, ~US$ 0,006 | 74 a 261 s, US$ 0,004 a 0,012 |
   | voz | ~5 s por cena | sem medida (as aulas 7 e 8 vieram do cache) |
   | cenas 3D | ~315 s e ~US$ 0,032 cada | 2 cenas: 631 s, US$ 0,063 |
   | checagem | ~31 s | 30,9 e 31,9 s |
   | vídeo | 1,9 × a duração | 428 e 528 s para 252 s |

   O custo da voz usa o preço do plano (`SOTAWHAT_ELEVENLABS_PLAN_USD` ÷ `_PLAN_CREDITS`), como o relatório da aula.
7. **Créditos da ElevenLabs.** `GET /v1/user/subscription` dá `character_limit`, `character_count` e
   `next_character_count_reset_unix`.
   - Restam = limite − usado. Em 2026-11-20, eram 90.000 − 0 (o limite inclui créditos acumulados de meses
     anteriores), com renovação em 19/12.
   - A leitura não gasta nada e fica 60 s em cache na interface.
   - Se faltarem créditos para a estimativa, "Produzir" fica desligado, com o motivo.
8. **Telegram.** A pergunta ficou sem resposta, então valeu o que já existia, com controle:
   - a caixa "enviar ao Telegram ao terminar" vem marcada (`--sem-envio` quando desmarcada);
   - toda aula pronta e não enviada tem "Enviar ao Telegram".
9. **Descartar** muda o status para `descartada`, e os arquivos ficam no disco. A lista não mostra aulas
   descartadas, e o cabeçalho conta quantas são. `taught_entities` passa a ignorá-las, como já ignora as que
   falharam, e as entidades voltam às sugestões. Uma aula entregue não se descarta.
10. **Sugestões da semana.** `suggest_topics(store, n)` generaliza `pick_topic`: as tendências mais fortes do último
    relatório semanal, de tipo processo, ainda sem aula e com fontes suficientes. `pick_topic` passa a ser a
    primeira delas.
11. **Antes de criar a aula**, a interface confere que o tema acha algo no grafo (`build_pack`, em milissegundos).
    Se não acha nada, responde 422: "nada no grafo sobre “X”: ligue a uma entidade ou mude o tema". Assim a pessoa
    não espera um processo só para ler esse erro.
12. **Confirmações sem diálogo do navegador.** "Cancelar", "Refazer roteiro" e "Descartar" pedem um segundo clique
    no mesmo botão ("confirmar?"), que volta ao normal em 4 s. Diálogos `confirm()` travam a página e a automação.

## API

| Método e caminho | O que faz | Erros |
|---|---|---|
| `GET /api/lessons/state` | tarefa viva (ou a última) com as linhas finais do log, créditos, prontidão, sugestões e número de descartadas | — |
| `GET /api/lessons` | como hoje, sem as descartadas, e com `has_plan`, `delivered_at`, `mode`, a última tarefa e, na revisão, a estimativa | — |
| `POST /api/lessons` `{topic, entities, mode}` | cria a aula e planeja | 409 ocupado · 422 tema vazio ou nada no grafo |
| `POST /api/lessons/{id}/plan` | refaz o roteiro | 409 ocupado ou aula entregue |
| `POST /api/lessons/{id}/produce` `{send}` | produz ou retoma | 409 ocupado, sem roteiro ou sem créditos |
| `POST /api/lessons/{id}/send` | envia ao Telegram | 409 ocupado ou sem vídeo |
| `POST /api/lessons/{id}/cancel` | cancela a tarefa viva da aula | 409 nada rodando |
| `POST /api/lessons/{id}/discard` | descarta | 409 tarefa viva ou aula entregue |

Os POST passam pelo `json_body` de sempre: JSON e origem local. Sem o lançador configurado (testes, contêiner), os
POST respondem 503.

## Interface

- **Cabeçalho:** leituras curtas, como em Perguntar: aulas, créditos de voz disponíveis e data de renovação.
- **Compositor "Nova aula"**, com o mesmo desenho do de Perguntar:
  - o tema em cima;
  - abaixo, "Ligar ao grafo" (busca de entidades em `/api/search`, chips removíveis, até 3) e "Modelos"
    (econômico | equilibrado), cada grupo com sua linha explicativa;
  - "Planejar roteiro" à direita.
  Com outra tarefa viva, o botão fica desligado e a linha explicativa diz qual.
- **Sugestões da semana:** chips com o nome e o tipo. Um clique preenche o tema e liga a entidade.
- **Card por estado:**
  - **tarefa viva:** etapas em linha, tempos, log recolhível e "Cancelar";
  - **revisão:** leituras da estimativa, créditos, roteiro aberto e as três ações;
  - **parou:** onde e por quê, "Retomar" (ou "Planejar roteiro" quando não há roteiro) e "Descartar";
  - **pronta ou entregue:** como hoje, mais "Enviar ao Telegram" quando não foi enviada.
- **Atualização:** com uma tarefa viva, a página consulta o estado a cada 2,5 s e conta os segundos localmente.
  Quando a tarefa termina, a lista recarrega. Fora da aba Aulas, a consulta para.

## Fora de escopo (F2)

- "Gerar aula sobre isto" no painel de uma entidade e nos cards de Tendências.
- Refazer só uma etapa pela interface (storyboard, voz, 3D ou vídeo); continua no terminal com `--refazer`.
- Editar o roteiro à mão antes de produzir.
- Fila com várias aulas.

## Riscos

- **Breakaway recusado pelo job da tarefa:** a aula morreria num reinício da interface. É testado de verdade:
  planejar um roteiro e reiniciar a tarefa `sotawhat-web` no meio.
- **pid reutilizado:** "Cancelar" só age sobre tarefa viva (batimento de até 30 s), e o pid é o do próprio
  processo da aula.
- **Suspensão do computador:** a tarefa pode parecer interrompida até o próximo batimento. A marca só é gravada
  quando outra tarefa pede a vez.

## Testes (sem rede)

- **`lesson_jobs`:**
  - pedido e recusa;
  - adoção pelo token e token que sumiu;
  - tarefa sem batimento não bloqueia e é marcada;
  - etapas e tempos;
  - motivo da falha;
  - cancelamento: a tarefa fica cancelada, o batimento não a revive, a aula para e o run fecha.
- **Motor:**
  - `until="roteiro"` para antes do storyboard e grava `llm_usd`, o modo e o run fechado;
  - as etapas anunciadas numa produção completa com dublês, com e sem 3D e envio;
  - `engine_of` de aula nova.
- **CLI:** `--so-roteiro` e `--job` chegam ao motor; a recusa com outra tarefa viva.
- **Sugestões:** várias, sem as ensinadas; descartada libera a entidade.
- **Créditos:** a resposta da ElevenLabs lida por um transporte falso; o erro vira `None`.
- **Estimativa:** números de um roteiro conhecido.
- **Web, com um lançador falso:**
  - os argumentos de cada ação;
  - 409, 422, 403, 415 e 503;
  - a lista sem descartadas;
  - o estado com o log.
- **Página:** os elementos do compositor e as chamadas da API no `app.js`.
- **De verdade:**
  - leitura dos créditos;
  - um roteiro planejado pela interface (cerca de US$ 0,01), com reinício da tarefa no meio;
  - um cancelamento;
  - a tela de produção desenhada com uma tarefa simulada no navegador.
  Nenhuma voz é gerada e nada vai ao Telegram sem o seu clique.
