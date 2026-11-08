# Insight Engine · P3 Grafo + interface — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA — use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para executar este plano tarefa a tarefa. Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** dar ao sotawhat o grafo e a interface próprios que o usuário pediu, sem Obsidian:
- tirar do código tudo o que lê ou escreve no vault do Obsidian;
- extrair entidades, relações e números de cada item aprovado (LLM, JSON estrito) e resolvê-las num grafo de entidades no SQLite (aliases, juiz LLM barato, auditoria das fusões);
- ligar as categorias da triagem (domínios A, tipos de problema B, famílias de técnica C) ao grafo sem custo de LLM;
- **interface web local** (`sotawhat serve`, FastAPI + sigma.js) com o grafo navegável, filtros, busca, painel da entidade e do item e votos;
- espelho do grafo no Neo4j (Docker Desktop), servidor MCP para o Claude Code e export JSON/CSV;
- extração e espelho no run diário, depois do digest.

**Decisões do usuário (2026-11-08), registradas no SDD v1.4 (§9, §11, §16.1, D12, D16):**
- "Quero uma interface com um grafo construído por nós. Não quero usar o vault do Obsidian ou o Obsidian whatsoever."
- Próxima fase: "Grafo + interface" (esta P3, executada antes da P2, com a interface antes prevista na P6).
- Vault antigo: "Ignorar o vault" (as 2.893 notas não são migradas).
- A tarefa `sotawhat-daily` já foi registrada de novo sem `--vault`, antes de qualquer escrita no vault.

**Arquitetura:**
- **O SQLite guarda o grafo** (D16). As tabelas novas do schema 3 são: `extractions`, `entities`, `entity_aliases`, `entity_mentions`, `entity_relations`, `entity_merges` e `entity_embeddings`. A interface e o MCP leem dessas tabelas, então funcionam com o Docker Desktop fechado.
- `pipeline/extract.py` escolhe os itens aprovados sem extração, chama o gateway em paralelo (tarefa `extract`, prompt `extract_v1`) e passa cada resultado para `graph/resolve.py`, no thread principal.
- `graph/resolve.py` normaliza os nomes e procura cada um nos aliases. Para nomes parecidos (sempre com os mesmos números), pergunta ao juiz (tarefa `resolve`) e registra a decisão. Também liga as categorias da triagem e descarta relações fora dos padrões.
- `graph/query.py` monta as respostas da interface e do MCP: a visão do grafo por janela de tempo, os detalhes da entidade e do item, a busca, as estatísticas e o export.
- `web/app.py` (FastAPI, só em 127.0.0.1) serve a API e a página estática. O sigma.js 3, o graphology e o graphology-library ficam em `web/static/vendor/`, sem CDN.
- O espelho no Neo4j fica em `graph/neo4j_sync.py`: `MERGE` idempotente e marca d'água em `items.graph_synced_at`. `graph/docker.py` abre o Docker Desktop e sobe o `compose.yaml`.
- `mcp_server.py` usa o `MCPServer` do SDK `mcp` 2.x, por stdio, com ferramentas sobre o `graph/query.py` e Cypher só leitura no Neo4j.
- No `run daily`, depois do digest, um run do tipo `graph` faz a extração, as categorias e a sincronização. O digest não espera o grafo.

**Stack (versões verificadas em 2026-11-08):**
- Python: o da P1, mais `fastapi` 0.162 e `uvicorn` 0.54 (interface), `neo4j` 6.4 (driver) e `mcp` 2.3 (servidor).
- JS, nos arquivos do pacote: sigma.js 3.0.3, graphology 0.26.0 e graphology-library 0.8.0, todos MIT. O sigma.js 4 saiu em outubro de 2026 e ainda é novo demais.
- Imagem do banco: `neo4j:2026.10.1-community`. O APOC e o GDS ficam para a P4.

**Spec:** `docs/sdd/2026-11-07-insight-engine-sdd.md` v1.4: §6.3 e §6.4 (armazenamento e schema), §6.5 (ontologia), §6.8 (extração e resolução), §6.11 (interface, MCP e export), §6.12 (operação), §9 (sem Obsidian), §11 (P3), §15 (D12 e D16).

**Convenções:**
- As da P1: PowerShell a partir da raiz, `.venv` com Python 3.12, testes sem rede e sem Docker, `core.autocrlf=true`.
- Um commit por tarefa na branch `feature/insight-engine-p3`, criada a partir do `master` (`1350eb2`).
- Cada tarefa começa pelos testes, que falham, e termina com a suíte inteira verde. O código fica no commit da tarefa; este plano define as interfaces, os testes e os critérios.

**Fora do escopo da P3:**
- P2: novas fontes, juiz para notícias parecidas de veículos diferentes, sinais sociais no classificador.
- P4: comunidades, tendências e lacunas calculadas (GDS ou NetworkX), relatório semanal, ideação.
- Pessoas como entidades (LGPD; as organizações bastam por ora).
- Revisão manual de fusões pela interface, reextração quando o prompt mudar e golden set de extração (P6).

---

## Pré-requisitos do usuário (para a Tarefa 13)

1. Docker Desktop aberto (está: v29.8, Compose v5.5). Recomendado: Settings → General → "Start Docker Desktop when you sign in".
2. ~1 GB livre para a imagem do Neo4j e o volume `sotawhat_neo4j_data`.
3. Nada a preencher à mão: a Tarefa 13 gera uma `NEO4J_PASSWORD` aleatória no `.env`, sem imprimi-la. Ela vale só para o Neo4j local, nas portas 7474/7687 de 127.0.0.1.

---

## Estrutura de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `sotawhat/obsidian.py`, `sotawhat/backfill.py`, `sotawhat/digest.py`, `scripts/schedule_digest.ps1` | remover | Obsidian (2.0) |
| `sotawhat/pipeline/collect.py` | criar | `collect` e `filter_relevant`, vindos de `digest.py` |
| `sotawhat/store/db.py` | editar | schema 3: tabelas do grafo e métodos |
| `sotawhat/llm/schemas.py`, `llm/tasks.py` | editar | `Extraction`, `SameEntity`; tarefa `resolve` |
| `sotawhat/llm/prompts/extract_v1.md`, `resolve_v1.md` | criar | prompts da extração e do juiz |
| `sotawhat/pipeline/extract.py` | criar | seleção, chamadas em paralelo, orçamento, registro |
| `sotawhat/graph/__init__.py`, `graph/resolve.py` | criar | normalização, aliases, juiz, categorias, padrões de relação |
| `config/aliases.yaml` | criar | aliases iniciais (LLM → large language model, …) |
| `sotawhat/graph/query.py` | criar | visão do grafo, detalhes, busca, estatísticas, export |
| `sotawhat/web/__init__.py`, `web/app.py` | criar | API FastAPI + `serve` |
| `sotawhat/web/static/index.html`, `app.js`, `style.css` | criar | interface |
| `sotawhat/web/static/vendor/*.js`, `vendor/LICENSES.md` | criar | sigma.js 3.0.3, graphology 0.26.0, graphology-library 0.8.0 (MIT) |
| `compose.yaml` | criar | Neo4j CE no Docker Desktop, portas só em 127.0.0.1 |
| `sotawhat/graph/docker.py`, `graph/neo4j_sync.py` | criar | `graph up`; espelho com marca d'água |
| `sotawhat/mcp_server.py`, `.mcp.json` | criar | servidor MCP `sotawhat-graph` |
| `sotawhat/pipeline/daily.py`, `sotawhat/cli.py`, `sotawhat/config.py` | editar | run `graph` depois do digest; `serve`, `serve-mcp`, `graph …`; `NEO4J_*`, `SOTAWHAT_WEB_PORT` |
| `sotawhat/doctor.py` | editar | Neo4j, backlog do grafo, interface no ar |
| `scripts/schedule_daily.ps1`, `README.md`, `.env.example`, `pyproject.toml` | editar | `-Web`, documentação, variáveis, dependências e arquivos do pacote |
| `tests/test_no_obsidian.py`, `test_collect.py`, `test_store_v3.py`, `test_extract.py`, `test_resolve.py`, `test_graph_query.py`, `test_web.py`, `test_neo4j_sync.py`, `test_mcp.py`, `test_graph_daily.py`, `test_doctor_p3.py` | criar | testes sem rede |

---

## Tarefa 0: Branch, documentos e linha de base

- [ ] `git checkout -b feature/insight-engine-p3` a partir do `master`.
- [ ] SDD v1.4 (sem Obsidian; P3 antes da P2; grafo no SQLite com espelho no Neo4j) e este plano.
- [ ] Linha de base: `.\.venv\Scripts\python.exe -m pytest -q` → **178 passed**.
- [ ] Commit: `docs: SDD v1.4 (no Obsidian, graph + own interface first) and the P3 plan`.

## Tarefa 1: Obsidian fora do código

**Testes primeiro** (`tests/test_no_obsidian.py`):
- `importlib.util.find_spec` não encontra `sotawhat.obsidian`, `sotawhat.backfill` nem `sotawhat.digest`.
- `parse_args(["digest", ...])` e `parse_args(["backfill-links", "--vault", "V"])` saem com `SystemExit`. A segunda vira uma busca com uma opção desconhecida, e o argparse recusa.
- `parse_args(["run", "daily", "--vault", "V"])` e `parse_args(["eval", "golden", "draft", "--vault", "V"])` saem com `SystemExit`.
- O `--help` da CLI não menciona "vault" nem "Obsidian".

**Implementação:**
- Remover `obsidian.py`, `backfill.py`, `scripts/schedule_digest.ps1`, `tests/test_obsidian.py` e `tests/test_backfill.py`.
- Mover `collect` e `filter_relevant` para `sotawhat/pipeline/collect.py`, apagar `digest.py` e renomear `tests/test_digest.py` para `tests/test_collect.py`.
- `cli.py`: sem `digest`, sem `backfill-links` e sem `--vault`, tanto em `run daily` quanto em `eval golden draft`.
- `pipeline/daily.py`: sem o parâmetro `vault`.
- `evals/golden.py` e `evals/commands.py`: sem `read_vault`.
- `doctor.py`: a dica do golden set sem `--vault`.
- `scripts/schedule_daily.ps1`: sem `-Vault`.
- `.gitignore`: sem `_tmp_vault/`.
- README: sem as seções do Obsidian.
- Testes antigos: tirar os do vault de `test_daily.py`, `test_cli.py` e `test_evals.py`.

**Aceite:** a suíte passa com os 17 testes do Obsidian removidos e os novos somados. `rg -i "obsidian|--vault" sotawhat scripts` não encontra nada.
**Commit:** `refactor: remove Obsidian (vault export, digest and backfill-links commands, --vault)`.

## Tarefa 2: SQLite schema 3 (grafo de entidades)

**Testes primeiro** (`tests/test_store_v3.py`):
- Um banco do schema 2 abre como schema 3:
  - as tabelas novas existem;
  - `items.graph_synced_at` é adicionada;
  - nenhum dado é perdido;
  - abrir de novo não falha.
- `record_extraction` é um upsert: soma `attempts`, guarda o payload, o erro e o custo.
- `extraction_candidates` devolve só itens aprovados (`main`, `frontier`, `radar`) sem extração ok e com erro abaixo do limite de tentativas. A ordem é `main` → `frontier` → `radar` e, dentro de cada uma, os mais novos primeiro.
- `add_entity` é idempotente por `(type, norm)`.
- Os aliases são procurados pelo grupo: modelo e produto compartilham o grupo `artifact`.
- `add_mention` é idempotente:
  - conta `mention_count` uma vez por item;
  - atualiza `first_seen` e `last_seen`;
  - promove o papel (`mentioned` < `used` < `main`);
  - marca o item como pendente de espelho (`graph_synced_at = NULL`).
- `add_relation` é idempotente por `(sujeito, relação, objeto, item)`.
- `record_merge` e `entity_merges` registram as fusões.
- `save_entity_embeddings` e `load_entity_embeddings` fazem a ida e volta dos vetores.
- `graph_dirty_items` e `mark_graph_synced`.

**Implementação:**
- `SCHEMA_VERSION = 3` e `_SCHEMA_V3`, com as tabelas do SDD §6.4 (v1.4): `extractions`, `entities` com `UNIQUE(type, norm)`, `entity_aliases` com PK `(grp, alias_norm)`, `entity_mentions` com PK `(item_id, entity_id)` e índice por entidade, `entity_relations` com PK de 4 colunas, `entity_merges` e `entity_embeddings`.
- Métodos com `_lock` nas escritas, como no schema 2.

**Commit:** `feat: SQLite schema 3 (entities, aliases, mentions, relations, merges, extractions)`.

## Tarefa 3: Extração (schema, prompt e pipeline)

**Testes primeiro** (`tests/test_extract.py`):
- `Extraction` valida um JSON de exemplo.
  - O schema estrito (`strict_schema`) marca todas as chaves como obrigatórias.
  - `category` só aceita `none`, C01–C21 ou B01–B15.
  - `ExtractedClaim.text_pt` com caracteres CJK falha na validação, como na triagem.
- O prompt `extract_v1` carrega. A mensagem do item traz o título, a fonte, a data, o host da URL, as categorias da triagem com rótulos e o texto truncado.
- `run_extraction` com um gateway falso:
  - extrai só os candidatos;
  - grava `extractions` com o modelo, a versão do prompt e o custo;
  - chama o resolvedor para cada sucesso;
  - registra `error` em `LLMFailure`;
  - para em `BudgetExceeded` e deixa o resto para depois;
  - respeita `limit`;
  - não extrai de novo um item que já tem extração ok.
- Teto de orçamento: com 80% do diário quase gasto, só cabem N itens, conforme o custo médio da tarefa `extract`.

**Implementação:**
- Em `llm/schemas.py`: `ExtractedEntity`, `ExtractedRelation`, `ExtractedClaim`, `Extraction` (SDD §6.8) e o `SameEntity` do juiz (`same: bool`, `reason: str`).
- `llm/prompts/extract_v1.md`, em inglês:
  - até 12 entidades e 10 relações, só entre as entidades listadas;
  - até 5 números em pt-BR, copiados do texto;
  - nomes canônicos em inglês, com nomes próprios como escritos (com a versão) e técnicas e problemas no singular e por extenso, com o acrônimo entre parênteses;
  - nada de pessoas, palavras genéricas nem entidades que não estão no texto.
- `llm/tasks.py`: `resolve` → `(DEEPSEEK_FLASH, GLM_FLASH)`, raciocínio "low", 600 tokens. A `extract` continua como está: DeepSeek → MiMo Pro → GLM, raciocínio "high".
- `pipeline/extract.py`:
  - `ExtractionStats`;
  - `item_message`, `messages_for`;
  - `run_extraction(store, run_id, gateway, resolver, limit=None, concurrency=4, now=None)`, com `ThreadPoolExecutor` para as chamadas e a resolução no thread principal, à medida que as respostas chegam.

**Commit:** `feat: entity extraction (strict JSON, prompt v1, budget cap, parallel calls)`.

## Tarefa 4: Resolução de entidades

**Testes primeiro** (`tests/test_resolve.py`):
- `normalize`:
  - remove acentos, pontuação e o "the";
  - põe técnicas e problemas no singular ("diffusion models" → "diffusion model"), mas não organizações nem produtos.
- `split_acronym`: "Retrieval-Augmented Generation (RAG)" → ("Retrieval-Augmented Generation", "RAG").
- Correspondência exata e por alias:
  - os aliases de `config/aliases.yaml` levam "LLM" e "LLMs" a "large language model";
  - o acrônimo vira alias da entidade.
- Grupo `artifact`: "MedGemma 1.5" como produto encontra o modelo "MedGemma 1.5".
- Números diferentes nunca vão ao juiz: "GPT-4o" × "GPT-4.1", "MedGemma 1.5" × "MedGemma 2".
- Juiz (falso):
  - "DeepMind" × "Google DeepMind" (nome contido no outro) chama o juiz;
  - "sim" vira alias com `entity_merges(method="judge")`;
  - "não" cria uma entidade nova;
  - acima do teto de chamadas, cria sem perguntar.
- Nomes genéricos ("AI", "model", "patients", "machine learning"), vazios, longos ou com CJK que não está no texto do item são descartados.
- Relações:
  - os padrões permitidos entram;
  - as fora do padrão são contadas como descartadas (ex.: `developed_by` apontando para um problema);
  - relações consigo mesma são descartadas.
- Categorias:
  - os rótulos da triagem viram nós `domain`, `problem_type` e `technique_family` com papel `tag`;
  - a `category` da técnica, do modelo ou do problema vira a relação `in_category`.

**Implementação:**
- `graph/resolve.py`:
  - `TYPES`, `GROUPS`, `GENERIC`, `PATTERNS`;
  - `normalize`, `split_acronym`, `digits`;
  - `Resolver(store, embedder=None, judge=None, aliases=None, max_judge_calls=40)`, com `apply(item_row, extraction)` e `link_categories(item_id, tags, seen)`.
- Candidatos parecidos: mesmos números e então semelhança de texto ≥ 0,88, tokens contidos ou cosseno dos nomes ≥ 0,90. Os três melhores vão ao juiz, um por vez, até um "sim".
- `graph/__init__.py` define `make_judge(gateway)`, que monta o prompt `resolve_v1` e chama `gateway.structured("resolve", …, SameEntity)`.
- `config/aliases.yaml` traz técnicas comuns e organizações conhecidas, com a validação em `configfiles.load_aliases`.

**Commit:** `feat: entity resolution (aliases, digit guard, LLM judge, category nodes, relation patterns)`.

## Tarefa 5: Consultas do grafo

**Testes primeiro** (`tests/test_graph_query.py`, com um banco montado pelos métodos da Tarefa 2):
- `graph_view`:
  - aplica a janela por `fetched_at` (7 dias deixa de fora um item de 20 dias atrás);
  - filtra por tipo e por mínimo de menções;
  - aplica o limite (as mais mencionadas ficam);
  - as categorias ficam de fora por padrão;
  - `focus` traz a entidade e os seus vizinhos.
- As arestas de coocorrência têm o peso igual ao número de itens em comum. Uma relação tipada vira o `kind` da aresta, com rótulo em pt-BR.
- `entity_detail`: aliases, itens (mais novos primeiro, com seção, resumo e por que importa), vizinhos com o número de itens em comum, relações nos dois sentidos e números (claims) dos itens; `None` para id inexistente.
- `item_detail`: triagem com rótulos das categorias, entidades com papel, extração (maturidade, modalidades, números) e voto mais recente.
- `search`: acha entidades por nome e por alias, e itens por título e por resumo, sem diferenciar maiúsculas de minúsculas.
- `stats`: contagens por tipo, itens pendentes de extração e última sincronização.
- `export`: JSON e dois CSVs (nós e arestas) em `data/exports/`.

**Implementação:** `graph/query.py`: `TYPE_LABELS`, `RELATION_LABELS`, `SECTIONS`; `graph_view`, `entity_detail`, `item_detail`, `search`, `neighbors`, `recent_items`, `stats`, `export`. Só SQL parametrizado; as listas `IN (...)` são montadas com `?`.

**Commit:** `feat: graph queries for the interface and MCP (window, filters, details, search, export)`.

## Tarefa 6: API web

**Testes primeiro** (`tests/test_web.py`, `fastapi.testclient.TestClient`):
- `GET /api/graph` repassa os filtros e devolve `nodes` e `edges`. `GET /api/entity/{id}` dá 200 ou 404. `GET /api/item?id=url:https://…` aceita ids com `:` e `/`.
- `GET /api/search?q=` e `GET /api/stats`.
- `POST /api/feedback` grava o voto com `channel="web"` e devolve o voto atual. Recusa valor inválido (422), corpo que não é JSON (415) e `Origin` de outro site (403).
- Um `Host` estranho dá 400 (proteção contra DNS rebinding).
- `GET /` serve a página. Os arquivos de `/static/vendor/` existem e são servidos.

**Implementação:**
- `web/app.py`:
  - `create_app(db_path)` abre um `Store` no *lifespan*;
  - `TrustedHostMiddleware` aceita só `127.0.0.1` e `localhost`;
  - endpoints síncronos;
  - `serve(settings, host="127.0.0.1", port=8765, open_browser=True)`.
- CLI: `sotawhat serve [--port] [--no-browser]`.
- `pyproject.toml`: `fastapi` e `uvicorn` nas dependências e `web/static/**` no `package-data`.

**Commit:** `feat: local web API (FastAPI on 127.0.0.1, host and origin checks, votes from the web)`.

## Tarefa 7: Interface (página, sigma.js e graphology)

**Testes primeiro** (em `tests/test_web.py`):
- A página carrega `vendor/graphology.umd.min.js`, `vendor/graphology-library.min.js`, `vendor/sigma.min.js`, `app.js` e `style.css`, sem nenhuma URL externa.
- Os três arquivos vendorizados conferem com o SHA-256 registrado em `vendor/LICENSES.md`.

**Implementação** (`web/static/`), tudo em pt-BR:
- Cabeçalho com as estatísticas.
- Painel de filtros:
  - período: 7, 30, 90 ou 365 dias, ou tudo;
  - tipos, com a cor de cada um;
  - mínimo de menções e limite de nós;
  - "mostrar categorias";
  - colorir por tipo ou por comunidade (Louvain no navegador).
- Busca com resultados de entidades e de itens.
- O grafo:
  - layout ForceAtlas2 síncrono, com as iterações conforme o tamanho;
  - o tamanho do nó segue a raiz das menções;
  - os rótulos aparecem nos nós maiores;
  - passar o mouse destaca os vizinhos, clicar abre o painel e o duplo clique foca a vizinhança.
- Painel da entidade: tipo, categoria, aliases, primeira e última menção, vizinhos clicáveis, relações, números e itens (seção, resumo, por que importa, link e votos 👍/👎/🧪).
- Painel do item.
- Tema claro e escuro (`prefers-color-scheme`) e layout que funciona em tela estreita.
- `vendor/LICENSES.md` traz as versões, a origem (jsDelivr) e o SHA-256 de cada arquivo:
  - sigma.min.js `58e30383…9e16`;
  - graphology.umd.min.js `dc337efa…c087`;
  - graphology-library.min.js `5323729e…a105`.

**Commit:** `feat: graph interface (sigma.js 3 + graphology, filters, search, entity and item panels)`.

## Tarefa 8: Espelho no Neo4j e `sotawhat graph`

**Testes primeiro** (`tests/test_neo4j_sync.py`, com um driver falso que registra cada `execute_query`):
- `ensure_schema` cria as restrições de unicidade de `Item.id` e `Entity.id`.
- `sync`:
  - envia em lotes `UNWIND` os itens pendentes, as entidades tocadas (com rótulo pelo tipo, de uma lista fechada), as menções e as relações agregadas (`items`, `weight`);
  - marca os itens como sincronizados;
  - um segundo `sync` sem mudanças não envia nada.
- `sync(rebuild=True)` apaga em lotes e reenvia tudo.
- Os rótulos e os tipos de relação vêm de uma lista fechada: um tipo desconhecido no banco é ignorado, nunca interpolado no Cypher.
- `graph_up` com `docker` falso:
  - sem `NEO4J_PASSWORD`, falha com uma instrução;
  - com o Docker fechado, abre o Docker Desktop e espera;
  - roda `docker compose up -d neo4j` e espera o Neo4j responder;
  - por fim, desiste com uma mensagem clara.
- CLI: `graph up|extract|sync|status|export` e `--rebuild`.

**Implementação:**
- `compose.yaml`:
  - `neo4j:2026.10.1-community`, `container_name: sotawhat-neo4j`;
  - portas `127.0.0.1:7474` e `127.0.0.1:7687`;
  - `NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:?…}`, memória via `NEO4J_HEAP_MAX` e `NEO4J_PAGECACHE`;
  - volume nomeado `sotawhat_neo4j_data`, `restart: unless-stopped`;
  - *healthcheck* com `cypher-shell`.
- `config.py`: `neo4j_uri`, `neo4j_user`, `neo4j_password`, `neo4j_database`, `sotawhat_web_port`.
- `graph/neo4j_sync.py` (`Neo4jMirror`) e `graph/docker.py` (`graph_up`).
- `pyproject.toml`: `neo4j`.

**Commit:** `feat: Neo4j mirror (compose, graph up/sync/status/export, watermark, rebuild)`.

## Tarefa 9: Servidor MCP

**Testes primeiro** (`tests/test_mcp.py`):
- `build_server` registra `search`, `entity`, `neighbors`, `recent_items`, `graph_stats` e `cypher`.
- As funções das ferramentas respondem sobre um banco de teste:
  - `entity` aceita o nome, um alias ou o id;
  - nome inexistente devolve uma mensagem, não uma exceção.
- `cypher`:
  - recusa escrita (`CREATE`, `MERGE`, `DELETE`, `SET`, `REMOVE`, `DROP`, `LOAD CSV`, `CALL dbms`/`apoc` …);
  - roda com `routing_=READ`;
  - limita as linhas;
  - sem Neo4j configurado, explica como ligar.

**Implementação:**
- `mcp_server.py`: `build_server(db_path, mirror_factory=None)` e `main_mcp`.
- CLI `sotawhat serve-mcp`: nada é escrito no stdout fora do protocolo.
- `.mcp.json` registra `sotawhat-graph` → `.venv/Scripts/sotawhat.exe serve-mcp`.
- `pyproject.toml`: `mcp`.

**Commit:** `feat: MCP server sotawhat-graph (search, entity, neighbors, recent items, read-only Cypher)`.

## Tarefa 10: Grafo no run diário

**Testes primeiro** (`tests/test_graph_daily.py`):
- `run_graph_stage` faz, nesta ordem:
  - abre um run `graph`;
  - extrai os candidatos;
  - liga as categorias de todos os aprovados;
  - sincroniza o espelho quando há Neo4j;
  - fecha o run com as estatísticas e o custo.
- Neo4j fora do ar vira um aviso, não uma falha. Um erro inesperado na extração fecha o run `graph` como falho e não afeta o run diário.
- O `doctor` continua olhando o último run `daily`.

**Implementação:**
- `pipeline/daily.py`: `run_graph_stage(settings, store, gateway, embedder, config, mirror_factory=None)`, chamado por `main_daily` depois do Telegram e do e-mail. O console mostra uma linha de resumo.
- `sotawhat graph extract` usa a mesma função.

**Commit:** `feat: graph stage after the daily digest (extraction, categories, mirror)`.

## Tarefa 11: `doctor` da P3

**Testes primeiro** (`tests/test_doctor_p3.py`):
- `check_neo4j`:
  - sem senha, avisa "espelho desligado; a interface funciona sem ele";
  - com o espelho no ar, mostra as contagens e a idade da última sincronização;
  - quando o espelho não responde, falha com "rode `sotawhat graph up`".
- `check_graph`:
  - mostra as entidades por tipo e os aprovados sem extração;
  - avisa quando a fila passa de 50 itens.
- `check_web`: com a porta aberta, ok com a URL; com ela fechada, avisa com "`sotawhat serve`".
- A tarefa `resolve` entra nos requisitos de modelo do catálogo.

**Commit:** `feat: doctor checks for the graph, the Neo4j mirror and the interface`.

## Tarefa 12: Agendamento, README e `.env.example`

- `scripts/schedule_daily.ps1 -Web`: tarefa `sotawhat-web` ao fazer logon (`pythonw.exe -m sotawhat.cli serve --no-browser`, com reinício em falha).
- README:
  - interface (`sotawhat serve`);
  - comandos `graph …`;
  - Neo4j (Browser em `http://127.0.0.1:7474`);
  - MCP no Claude Code;
  - export.
- `.env.example`:
  - `NEO4J_PASSWORD`, com a instrução de que a Tarefa 13 gera uma;
  - `SOTAWHAT_WEB_PORT`;
  - sem `GRAPH_BACKEND`, que não é mais usada.
- Suíte verde.
- Commit: `docs: graph interface, Neo4j and MCP in README, scheduling and .env.example`.

## Tarefa 13: Verificação com rede e Docker (precisa dos pré-requisitos)

1. Gerar a `NEO4J_PASSWORD` no `.env` sem imprimi-la.
2. Rodar `sotawhat graph up`: baixa a imagem, sobe o contêiner e espera o Neo4j.
3. Rodar `sotawhat graph extract` nos ~64 itens já aprovados e anotar custo, tempo, entidades, fusões e relações descartadas.
4. Rodar `sotawhat graph sync` e conferir as contagens no Neo4j.
5. Rodar `sotawhat serve`, abrir a interface no navegador, conferir o grafo, os painéis, a busca e um voto, e tirar uma captura de tela.
6. Testar o MCP por stdio com o cliente do SDK: `graph_stats`, `search` e `cypher`.
7. Rodar `sotawhat doctor`.
8. **Perguntar ao usuário** antes de registrar a tarefa `sotawhat-web` (logon) e antes do merge e do push.
9. Escrever o adendo de execução neste plano.

---

## Adendo: execução (2026-11-08)

O usuário escolheu "Grafo + interface" com a pergunta "Qual fase eu planejo e implemento agora?". Por isso, o plano e a implementação saíram na mesma sessão, na branch `feature/insight-engine-p3`, com um commit por tarefa. Em todas as tarefas os testes novos falharam antes da implementação e a suíte inteira passou depois:

| Tarefa | Commit | Suíte |
|---|---|---|
| 0 · SDD v1.4 e plano | `ac3effe` | 178 |
| 1 · Obsidian fora do código | `4ef631a` | 170 (−17 do Obsidian, +9) |
| 2 · Schema 3 | `62a6340` | 177 |
| 3 · Extração | `ec92bbd` | 183 |
| 4 · Resolução de entidades | `5738118` | 195 |
| 5 · Consultas do grafo | `eba598b` | 201 |
| 6 · API web | `1a7679b` | 205 |
| 7 · Interface | `cc43a07` | 206 |
| 8 · Espelho no Neo4j | `8b1bee6` | 211 |
| 9 · Servidor MCP | `4edc0bc` | 215 |
| 10 · Grafo no run diário | `fa51c5a` | 221 |
| 11 · `doctor` | `bcb4232` | 225 |
| 12 · Documentação e agendamento | `27a7c5e` | 225 |
| 13 · Prompt de extração ajustado nos 3 primeiros itens reais | `b2ccf3a` | 225 |
| 13 · Interface ajustada com o grafo real | `8bd63f5` | 225 |
| 13 · Juiz sem a regra de contenção para técnicas e problemas | `f9258ef` | 226 |

### Mudanças além do plano

- **Interface (Tarefa 7).** Um teste de fumaça no Chrome, sobre um grafo sintético, achou quatro defeitos antes do commit:
  - o CSS de `.chip` e `.overlay` anulava o atributo `hidden`, e o overlay vazio cobria o grafo e bloqueava os cliques;
  - o painel recebia listas e `null` como texto;
  - as partes da linha de metadados ficavam grudadas;
  - o destaque do mouse ficava preso quando o ponteiro saía do canvas.

  Também entraram duas melhorias: a separação entre os vizinhos que são entidades e as categorias frequentes, e a remoção de números repetidos no painel da entidade.
- **Prompt de extração (Tarefa 13).** Nos 3 primeiros itens reais, um problema veio com o enquadramento do próprio estudo (mais de 80 caracteres) e foi descartado junto com suas relações, e a System Usability Scale veio como regulação. O `extract_v1` foi corrigido no lugar, antes de qualquer uso em produção: problemas com no máximo seis palavras, gerais o bastante para se repetir, e escalas fora das regulações. As linhas de grafo desse teste (3 itens) foram apagadas e o backfill rodou do zero.

### Tarefa 13: resultados

1. **`NEO4J_PASSWORD`**: gerada no `.env` (32 caracteres hexadecimais), sem ser impressa.
2. **`sotawhat graph up`**: 62 s, contando o download da imagem `neo4j:2026.10.1-community`, a subida do contêiner e a espera pelo Bolt. Resultado: contêiner `sotawhat-neo4j` *healthy*, portas só em 127.0.0.1 e volume `sotawhat_neo4j_data`.
3. **Extração dos itens já aprovados** (`sotawhat graph extract`):
   - **Teste com 3 itens:** 42 s e US$ 0,003. Levou ao ajuste do prompt descrito acima; as linhas desse teste foram apagadas.
   - **Backfill:** 64 de 64 itens sem erro, em 3 min 18 s e US$ 0,035. A extração custou US$ 0,0005 por item (raciocínio alto, cerca de 12 s por chamada, 4 em paralelo). As 48 chamadas do juiz somaram US$ 0,0017.
   - **Grafo resultante:**
     - 388 entidades: 185 técnicas, 89 problemas, 55 modelos, 36 datasets, 12 organizações, 9 produtos e 2 regulações;
     - 51 nós de categoria: 20 domínios, 13 tipos de problema e 18 famílias de técnica;
     - 840 menções e 665 relações (317 explícitas e 348 `in_category`); 43 nomes ou relações descartados.
   - **Mais citadas:** large language model (11 itens), electronic health record (3) e reinforcement learning (3).
   - **Juiz:** chegou ao teto de 40 chamadas e não fundiu nada; daí o commit `f9258ef`.
4. **Espelho:** sincronizado no fim da mesma etapa. O Neo4j ficou com 503 nós e 1.478 relações (840 `MENTIONS` e 638 tipadas), e `graph status` não mostra nada pendente.
5. **Interface** (`sotawhat serve`, http://127.0.0.1:8765), conferida no Chrome com o grafo real:
   - grafo, filtros, painel da entidade ("large language model": 11 itens, alias "LLM", relações e categorias), busca e votos;
   - nenhum erro no console;
   - os ajustes de rótulos, de layout e do cache vieram dessa conferência (`8bd63f5`).
6. **MCP por stdio**, com o cliente do SDK, os dados reais e o `.env` real:
   - as 6 ferramentas aparecem;
   - `graph_stats` e `search` respondem;
   - `cypher` lista os modelos mais citados direto do Neo4j;
   - um `DETACH DELETE` é recusado.
7. **`doctor`:** tudo OK, inclusive as verificações novas: "grafo: 388 entidades · 317 relações · 64 itens extraídos", "espelho Neo4j: 503 nós · 1478 relações" e "interface: no ar".
8. **Custo:** US$ 0,16 de LLM no mês até aqui (limite da chave: US$ 5).

**Pendências que dependem do usuário:**
- registrar `sotawhat-web` (interface ao fazer logon) com `scripts\schedule_daily.ps1 -Web`;
- merge da branch no `master` e push.
