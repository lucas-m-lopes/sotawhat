# Insight Engine · P2 Novas fontes I — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA — use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para executar este plano tarefa a tarefa. Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** levar ao pipeline as fontes do SDD §5.3 e §7 que a P0 e a P1 não cobriram, com fixture e teste para cada uma:
- os periódicos e as notícias de saúde do Tier 1;
- medRxiv, a lista da FDA de dispositivos com IA e o Google News;
- AlphaSignal (RSS) e The Batch (sitemap);
- newsletters do Gmail (IMAP + segmentação por LLM);
- GitHub (repositórios novos e em alta, releases), Hugging Face Hub e o registry oficial de MCP.

Os itens novos passam pela triagem e pelo grafo da P3 sem mudança nessas etapas, com a origem visível no digest e na interface.

**Contexto:** executada depois da P3, a pedido do usuário em 2026-11-08 ("continue a implantação segundo o plano SDD direto até o final"). Branch `feature/insight-engine-p2`, a partir do `master` (`4b6d9b9`).

**Sondagem ao vivo (2026-11-08), antes do código:**
- **Respondem com 200:** busca do GitHub (com e sem token), HF Hub (modelos, datasets e *trending*), registry de MCP (`servers` + `metadata.nextCursor`) e medRxiv (`collection`, `messages.total`).
- **Feeds RSS e Atom com itens:** AlphaSignal (100), JAMA AI (4), Lancet Digital Health (58), STAT IA (20), Healthcare Dive Health IT (20), Google News EN (22) e PT-BR (100), MONAI (10) e OpenAI News (1.368).
- **Outros:** o sitemap do The Batch lista 376 edições; cada edição traz as matérias como `<h1>`. O CSV da FDA tem 1.615 linhas, e a decisão mais recente é de 29/06/2026: o CSV atrasa meses.
- **Gmail por IMAP:** a pasta "Todos os e-mails" tem nome localizado e é achada pela flag `\All`. A label `newsletters/ai` não existe (0 mensagens), e a busca `from:(alphasignal.ai OR deeplearning.ai)` acha 37 em 30 dias.

**Decisões:**
- **Fontes sem palavra-chave.** As fontes de canal (GitHub, HF, MCP, medRxiv, FDA, The Batch, Gmail e os feeds de notícia) não usam as palavras-chave do perfil: chamam `fetch(limit)` uma vez por run. Cada fonte tem um teto de itens, e a triagem decide a relevância. Os feeds de laboratório continuam filtrados por palavra-chave, como antes.
- **Tipo do item.** `Result.extra["kind"]` define o tipo: `repo`, `model`, `dataset`, `mcp_server`, `newsletter_item` ou `regulation`. Os metadados (estrelas, licença, *likes*, *downloads*, versão, empresa) vão no início do texto. Assim a triagem e a extração os veem sem mudar o schema.
- **FDA.** A primeira execução só grava a linha de base dos números de submissão em `data/state/`. Depois disso entram as linhas novas, de qualquer data.
- **Gmail.** A busca usa `GMAIL_QUERY`, em pasta só leitura e com `BODY.PEEK`, sem marcar nada como lido. As mensagens já vistas, pelo `X-GM-MSGID`, ficam em `data/state/`. A segmentação usa a tarefa `segment` (prompt `segment_v1`, JSON estrito), e os links de rastreamento são resolvidos e limpos.
  - O AlphaSignal e o The Batch entram pelo RSS e pelo sitemap, então o Gmail serve às newsletters sem feed, com a label que o usuário criar (SDD §7.1). Até lá, o `doctor` avisa.
- **Triagem.** O prompt passa a `triage_v2`, que acrescenta só os tipos de item novos ao `triage_v1`. A mensagem do item ganha a linha `kind:`.
- **Ficam para depois:** a velocidade de estrelas (`star_snapshots`) e o diff dos `marketplace.json` de skills ficam para a P6. A busca do GitHub por `topic:agent-skills` e `topic:claude-skills` já cobre os repositórios novos de skills.

---

## Tarefa 0: Branch, plano e linha de base
- [ ] `git checkout -b feature/insight-engine-p2`; este plano; suíte com **226 passed**.

## Tarefa 1: Fontes sem palavra-chave, tipo do item e RSS por recência
- Testes:
  - `collect` chama `fetch` uma vez por fonte sem palavra-chave, com o teto da fonte, e grava a fonte como conceito;
  - o `kind` de `extra` vira `Item.kind`;
  - `RSSSource(..., keywordless=True)` devolve as entradas mais novas dentro de `max_age_days` e até `max_items`;
  - a falha de uma fonte continua isolada.
- Implementação: `Source.keywordless`, `Source.max_items`, `safe_fetch` e `kind_for(source, extra)`.

## Tarefa 2: GitHub
- Testes, com fixtures reais:
  - a busca monta a query com data e piso de estrelas;
  - os itens saem como `repo`, com o id da URL do repositório;
  - o texto traz estrelas, linguagem, licença, tópicos e o trecho do README;
  - duplicatas entre queries são removidas;
  - o README é opcional, e falhar nele não derruba o item;
  - sem token, a fonte funciona, com o limite menor.
- Implementação: `sources/github.py` e `settings.github_token`.

## Tarefa 3: Hugging Face Hub
- Testes: modelos e datasets `medical` por *trending* e os modelos em alta em geral; tipos `model` e `dataset`; URLs canônicas; `Authorization` só com token.
- Implementação: `sources/hf_hub.py` e `settings.hf_token`.

## Tarefa 4: Registry oficial de MCP
- Testes: busca por termos de saúde e servidores atualizados; só `status: active`; tipo `mcp_server`; o id vem do repositório ou do nome; o texto traz a descrição, os *remotes* e a versão.
- Implementação: `sources/mcp_registry.py`.

## Tarefa 5: medRxiv
- Testes: janela de datas; paginação por cursor; filtro de categorias; id `doi:`; autores separados por `;`.
- Implementação: `sources/medrxiv.py`.

## Tarefa 6: FDA, dispositivos com IA
- Testes:
  - a primeira execução só grava a linha de base, e a segunda emite as submissões novas;
  - a URL depende do tipo de submissão: K, DEN ou P;
  - o tipo é `regulation`;
  - a falha de download não altera o estado.
- Implementação: `sources/fda.py` e `data/state/fda_ai_devices.json`.

## Tarefa 7: The Batch
- Testes: o sitemap dá as últimas N edições; cada edição é dividida nas matérias (`<h1>` depois de "News"); id `url#slug`; tipo `newsletter_item`; edição já vista não é baixada de novo.
- Implementação: `sources/the_batch.py` (parser `html.parser` da stdlib).

## Tarefa 8: Newsletters do Gmail
- Testes, com IMAP falso e `.eml` de fixture:
  - a busca X-GM-RAW roda na pasta `\All`, em modo só leitura;
  - as mensagens já vistas são puladas;
  - HTML vira texto com os links;
  - o segmentador recebe assunto, remetente e texto;
  - as histórias viram itens `newsletter_item`, com links resolvidos e sem rastreamento;
  - "unsubscribe" e "manage preferences" nunca são seguidos.
- Implementação: `sources/gmail.py`, o schema `NewsletterStories`, o prompt `segment_v1` e `make_segmenter(gateway)`.

## Tarefa 9: Perfis e fontes no `run daily`
- `build_sources(profile, settings, segmenter)`:
  - **medico:** periódicos via Crossref (+ JAMIA, Radiology: AI, npj Health Systems), feeds (JAMA AI, Lancet Digital Health, STAT IA, Healthcare Dive Health IT, MONAI), medRxiv, FDA, Google News EN e PT-BR, GitHub e HF médicos, MCP de saúde;
  - **geral:** AlphaSignal, The Batch, OpenAI News, GitHub de agentes/MCP/skills, modelos em alta no HF, servidores MCP recentes e o Gmail.
- O `main_daily` cria o gateway antes das fontes, para o segmentador.

## Tarefa 10: Triagem v2
- `triage_v2.md` igual à v1, mais um parágrafo sobre os tipos de item.
- A mensagem do item ganha `kind:`.

## Tarefa 11: `doctor`
- `GITHUB_TOKEN`: o limite via `/rate_limit`.
- `HF_TOKEN`: `whoami-v2`.
- Gmail: login IMAP e quantas mensagens a `GMAIL_QUERY` acha em 30 dias, com a dica do filtro quando for zero.

## Tarefa 12: Documentação
- README, `.env.example`, SDD v1.5 (P2 executada; decisões acima).

## Tarefa 13: Verificação real
- `run daily --no-llm --no-notify`: coleta de todas as fontes, sem triagem; os itens ficam para o run das 07:00, que manda o digest.
- Contagens por fonte e falhas.
- Triagem v2 de amostra, sem gravar: um repo, um modelo, um servidor MCP, um item do The Batch e um da FDA.
- Segmentação de um e-mail real do AlphaSignal, sem gravar.
- `doctor`.
- Adendo, merge e push.
