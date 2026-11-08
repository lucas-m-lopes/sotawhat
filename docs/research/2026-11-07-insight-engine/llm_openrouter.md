# LLM via OpenRouter — modelos chineses × Anthropic (2026-11-07)

**Pergunta (resposta do usuário à §16, item 12 do SDD):** "Quero usar modelos chineses comparáveis aos da Anthropic via OpenRouter para redução drástica de custo."

**Método:** consultas diretas, sem intermediários, em 2026-11-07:
- catálogo público do OpenRouter (`GET https://openrouter.ai/api/v1/models`, 460 modelos);
- endpoints por modelo (`GET /api/v1/models/{autor}/{slug}/endpoints`), com preço, quantização, parâmetros suportados e uptime;
- lista de endpoints com Zero Data Retention (`GET /api/v1/endpoints/zdr`, 1.120 endpoints);
- documentação oficial em Markdown (`https://openrouter.ai/docs/*.md`): roteamento, ZDR, coleta de dados, saídas estruturadas, Batch API, cache, contabilização de uso, fallbacks e FAQ;
- tabela do leaderboard da Artificial Analysis (`https://artificialanalysis.ai/leaderboards/models`, HTML lido diretamente) e duas buscas web para contexto.

Os preços abaixo valem para 2026-11-07, em US$ por milhão de tokens (entrada/saída). Eles mudam com frequência; o `doctor` do projeto deve reconsultar a API.

---

## 1. Resultado em um parágrafo

Nas tarefas de volume (triagem, segmentação, extração, resumo), os modelos chineses de pesos abertos **empatam com o Haiku 5.5 e com o Sonnet 5.5 em esforço médio** no Artificial Analysis Intelligence Index. O custo fica entre 1× e 10× menor, conforme a etapa. Na triagem, o Haiku 5.5 já custa quase o mesmo que os modelos "flash" chineses, então a economia ali é pequena. Ela aparece na extração, na síntese e principalmente na ideação. **Nenhum modelo chinês alcança o Opus 5.5 em esforço alto ou máximo:** o melhor de pesos abertos, Kimi K3.1 Pro, marca 46, contra 59 do Opus 5.5 (max), e equivale ao Opus 5.5 em esforço médio (48). Para ideação, a diferença se compensa em parte com juízes de famílias diferentes, já que vários juízes heterogêneos reduzem o viés de autopreferência. Ainda assim, ela deve ser medida com o *bake-off* do projeto, não presumida. Com a política de privacidade adotada (só endpoints **ZDR**, com quantização ≥ fp8 e suporte a saída estruturada), sobram endpoints suficientes, quase todos de provedores dos EUA e da Europa (DeepInfra, Fireworks, Together, DigitalOcean, Nebius, Parasail, Cohere, CoreWeave). Os pesos são abertos, e a inferência não passa pelos laboratórios chineses.

## 2. Qualidade — Artificial Analysis Intelligence Index (lido em 2026-11-07)

| Faixa Anthropic | Índice | Modelos chineses na mesma faixa (índice) |
|---|---|---|
| Opus 5.5 (max / xhigh / high / medium) | 59 / 57 / 52 / 48 | **Kimi K3.1 Pro (46)**, abaixo do Opus 5.5 medium |
| Sonnet 5.5 (max / xhigh / high / medium) | 55 / 50 / 42 / 31 | Tencent Hy4 (35), Qwen3.8 Max 0902 (34), **DeepSeek V4.1 Flash 1017 max (33)**, **GLM-5.3 max (32)**, MiMo-V2.6-Pro (30), Ling 3.1 Flash (30) |
| Haiku 5.5 (max / xhigh / high / medium / low) | 36 / 35 / 30 / 25 / 19 | DeepSeek V4.1 Flash 1017 high (29), MiniMax-M3.1-Flash (29), Step 5 Preview (29), GLM-5.3-Flash (28), MiMo-V2.6-Flash (27), DeepSeek V4.1 Flash 1017 sem raciocínio (19) |

Observações:
- Topo geral em 2026-11-07: Gemini 4 Carbon (high) 60, Claude Opus 5.5 (max) 59, GPT-6 Astra (max) 57.
- **DeepSeek V4 Pro 0813 (max) marca só 23**, abaixo do V4.1 Flash. Para este projeto, "Pro" não é sinônimo de melhor; preferir o V4.1 Flash 1017.
- MiniMax-M3 marca 19. O M3.1-Flash (29) o supera.
- Agregadores de terceiros (benchlm, benchleader, modelgrep) publicam números diferentes por versão do índice, e vários benchmarks citados por fornecedores são autodeclarados. Use o índice só como ordenação grosseira. A escolha final por etapa sai do *bake-off* do projeto (§12 do SDD).

## 3. Preço e privacidade — endpoints elegíveis

Filtro aplicado: endpoint presente em `/api/v1/endpoints/zdr`, `structured_outputs` em `supported_parameters` e quantização fora de {fp4, mxfp4, nvfp4, int4}. Os mais baratos por modelo:

| Modelo (slug OpenRouter) | Elegíveis | Mais baratos (provedor · quantização · entrada/saída) | Visão | Cache implícito |
|---|---|---|---|---|
| `deepseek/deepseek-v4.1-flash-1017` | 34 | Particle AI · ? · 0,025/0,25 — Morph · fp8 · 0,022/0,40 — **DeepInfra · fp8 · 0,078/0,235** — DeepInfra · fp8 · 0,098/0,294 | sim | sim |
| `deepseek/deepseek-v4.1-flash` | 26 | Morph · fp8 · 0,022/0,40 — DeepInfra · fp8 · 0,14/0,42 — InferenceNet · fp8 · 0,103/0,60 | sim | sim |
| `xiaomi/mimo-v2.6-flash` | 5 | Cohere / DeepInfra / Makora · fp8 · 0,14/0,28 | sim | sim |
| `xiaomi/mimo-v2.6-pro` | 2 | **DeepInfra · fp8 · 0,387/0,783** (único barato; PrimaLabs 4/8) | — | sim |
| `z-ai/glm-5.3-flash` | 13 | Tenstorrent · fp8 · 0,075/0,25 — Near AI · fp8 · 0,08/0,50 — DigitalOcean · 0,112/0,375 | sim | sim |
| `z-ai/glm-5.3` | 18 | Reka · 0,14/2,10 — DekaLLM · 0,18/2,95 — Cloudflare · 0,70/2,20 — Morph · fp8 · 0,74/3,00 | — | sim |
| `moonshotai/kimi-k3.1-pro` | 7 | DeepInfra · bf16 · 1,90/9,50 — Fireworks / Phala / DigitalOcean · 2,00/10,00 | sim | sim |
| `minimax/minimax-m3.1-flash` | 5 | Fireworks / DigitalOcean / SambaNova / Parasail · 0,15/0,60 | sim | sim |
| `tencent/hy4`, `stepfun/step-5-preview` | 0 | só endpoints fp4 em ZDR → **fora** | — | — |
| `qwen/qwen3.8-max*`, `qwen/qwen3.8-flash`, `qwen/qwen3.7-plus` | 0 | servidos só pela Alibaba (fora da lista ZDR) → **fora** quando ZDR é exigido | — | — |
| Referência: `anthropic/claude-haiku-5.5` | 3 | Google (Vertex) · 0,10/0,50 | sim | — |
| Referência: `anthropic/claude-sonnet-5.5` | 3 | Google (Vertex) · 2,00/10,00 | sim | — |
| Referência: `anthropic/claude-opus-5.5` | 3 | Google (Vertex) · 4,00/20,00 | sim | — |

Outros achados do catálogo:
- **O preço de `/models` é o do endpoint mais barato**, muitas vezes fp4 ou de nuvem chinesa. Exemplos: o GLM-5.3 aparece a US$ 0,07/1,40 e o DeepSeek V4 Pro 0813 a US$ 0,111/4,44 por causa de endpoints fp4/mxfp4. Para estimar custo, use os endpoints elegíveis acima.
- Há **preço por horário** em alguns endpoints (campo `pricing.overrides` com `utc_days`, `utc_start` e `utc_end`). Exemplos: `deepseek-v4.1-flash-1017` (dobra em parte do dia útil) e `minimax-m3.1-flash` (dobra das 01:00 às 15:00 UTC). O pipeline diário roda às 07:00 BRT = 10:00 UTC.
- **Modelos com data de expiração** aparecem em `expiration_date`. Exemplos: `moonshotai/kimi-k2.5` expira em 2026-11-18; `bytedance-seed/seed-1.6` e `seed-2.0-code` em 2026-11-11; `z-ai/glm-4.5`, `glm-4.5v` e `glm-4.7` em 2026-12-31. O `doctor` deve alertar.
- Kimi K3 (não o K3.1 Pro) tem saída cara (US$ 11–16/M) e endpoints ZDR quase todos fp4; não usar.
- **Níveis de raciocínio aceitos** (campo `reasoning` do catálogo):

  | Modelo | Raciocínio obrigatório | Níveis aceitos |
  |---|---|---|
  | `z-ai/glm-5.3`, `z-ai/glm-5.3-flash` | sim | `max`, `high`, `low` |
  | `minimax/minimax-m3.1-flash` | sim | `max`, `xhigh`, `high`, `medium`, `low` |
  | `deepseek/deepseek-v4.1-flash-1017` | não | `max`, `high`, `low`, `none` (sem `medium`; padrão `high`) |
  | `moonshotai/kimi-k3.1-pro` | não | `max`, `high`, `low`, `none` |
  | `xiaomi/mimo-v2.6-*` | não | não expõe níveis |

  Na mesma cadeia de fallback, use só um nível aceito por todos os modelos (`low`/`high`). O `doctor` do projeto confere isso contra o catálogo.
- **Inspeção TLS local:** em 2026-11-07, o Python com `certifi` recebeu `CERTIFICATE_VERIFY_FAILED` (certificado autoassinado na cadeia) em `openrouter.ai`, de forma intermitente; o `curl` (Schannel) funcionava. A correção é o `truststore`, que usa o repositório do Windows.
- O Haiku 5.5 a US$ 0,10/0,50 custa praticamente o mesmo que DeepSeek V4.1 Flash, MiMo-V2.6-Flash e GLM-5.3-Flash. **Na triagem, a troca por modelo chinês praticamente não reduz custo.**

## 4. Recursos do OpenRouter que importam para o projeto

| Recurso | O que diz a documentação | Uso no projeto |
|---|---|---|
| Roteamento por provedor (`provider`) | campos `order`, `allow_fallbacks` (padrão true), `require_parameters`, `data_collection` ("allow"/"deny"), `zdr`, `enforce_distillable_text`, `only`, `ignore`, `quantizations`, `sort` ("price"/"throughput"/"latency" ou objeto com `partition`), `preferred_min_throughput`, `preferred_max_latency`, `max_price`; atalhos `:floor` (preço) e `:nitro` (vazão) | `zdr: true`, `data_collection: "deny"`, `require_parameters: true`, `quantizations: ["fp8","bf16","fp16","fp32","unknown"]`, `sort: "price"` |
| Zero Data Retention | três níveis de política por endpoint: **ZDR** (sem armazenamento rotineiro), **Safety Retention** (retenção só contra abuso, sem treino) e **Retention and Training**. `zdr: true` por requisição; ou imposição na conta por grupo de modelos ("All other models"), com opção "ZDR only" para excluir Safety Retention. Exceção: triagem de CSAM em trânsito desde 27/10/2026 | política padrão do projeto em **todas** as chamadas; recomendado ligar também na conta |
| Coleta de dados pelo OpenRouter | não armazena prompts nem respostas, salvo opt-in em *logging* ou no uso para melhorar o produto (este último dá 1% de desconto), ambos desligados por padrão; guarda metadados (tokens, latência) | manter os dois opt-ins desligados |
| Saídas estruturadas | `response_format: {type: "json_schema", json_schema: {name, strict: true, schema}}` em Chat Completions (`text.format` na Responses API) | todas as saídas (triagem, extração, ideação) |
| Response Healing | plugin `{"id": "response-healing"}` corrige JSON malformado (chaves, vírgulas, cercas Markdown) em requisições não-streaming com `json_schema`/`json_object` | ligado; a validação Pydantic continua obrigatória |
| Fallback de modelos | campo `models: [...]` em ordem de prioridade; se o primeiro falhar (indisponível, rate limit, moderação), tenta o próximo | 2–3 modelos por etapa, de famílias diferentes |
| Contabilização de uso | toda resposta traz `usage` com tokens nativos, `cost` em créditos (= US$), tokens de raciocínio e de cache; `usage: {include: true}` está obsoleto e não tem efeito | `llm_calls.cost_usd` = custo real, não estimado |
| Cache de prompt | automático e com roteamento "sticky" em DeepSeek, Moonshot, OpenAI e Gemini; Alibaba exige `cache_control`; leituras com desconto | prefixo estável (rubrica, ontologia) no início do prompt |
| Batch API | `POST /api/v1/batches` (requisições inline, sem JSONL), ~50% do preço síncrono em modelos com variante `:batch`, resultado em ≤ 24 h, dados apagados em 30 dias, sem treino; **não oferece ZDR**; endpoints `/v1/chat/completions`, `/v1/responses`, `/v1/messages`, `/v1/embeddings` | **não usado por padrão**: para os modelos escolhidos, o endpoint síncrono ZDR mais barato custa igual ou menos que a variante `:batch` (ex.: V4.1 Flash `:batch` 0,112/0,336 × DeepInfra síncrono 0,078/0,235) |
| Roteamento regional | `eu.openrouter.ai` / `us.openrouter.ai` só nos planos Business/Enterprise | não necessário |
| Taxas | sem markup no preço de inferência; taxa na compra de créditos (o percentual aparece no checkout; a FAQ usa um template que não exibe o número; historicamente ≈ 5,5%) **[verificar no checkout]**; BYOK com franquia mensal e 5% acima dela | incluir ~6% na estimativa |
| Modelos `:free` | 50 req/dia sem créditos; 1.000 req/dia com ≥ 10 créditos comprados | não depender deles |
| Chave e limite | chaves com limite de gasto; o cookbook "API Key Audit" recomenda limite e expiração | chave dedicada ao projeto com limite mensal |

## 5. Recomendação de modelos por etapa (padrão inicial — confirmar no *bake-off*)

| Etapa | Primário | Fallbacks | Raciocínio | Por quê |
|---|---|---|---|---|
| Triagem (centenas/dia) | `deepseek/deepseek-v4.1-flash-1017` | `xiaomi/mimo-v2.6-flash`, `z-ai/glm-5.3-flash` | baixo | faixa Haiku 5.5 high; 34 endpoints elegíveis; cache implícito |
| Segmentação de newsletters | `xiaomi/mimo-v2.6-flash` | `deepseek/deepseek-v4.1-flash-1017` | baixo | barato, contexto 1M |
| Visão (posts do Instagram) | `xiaomi/mimo-v2.6-flash` | `z-ai/glm-5.3-flash`, `minimax/minimax-m3.1-flash` | baixo (GLM e MiniMax não aceitam desligar) | multimodal, US$ 0,14/0,28 |
| Extração de entidades/relações | `deepseek/deepseek-v4.1-flash-1017` | `xiaomi/mimo-v2.6-pro`, `z-ai/glm-5.3` | alto | faixa Sonnet 5.5 medium; JSON estrito |
| Juiz de resolução de entidades | `deepseek/deepseek-v4.1-flash-1017` | `xiaomi/mimo-v2.6-flash` | baixo | decisão binária |
| Digest e mapa semanal | `deepseek/deepseek-v4.1-flash-1017` | `xiaomi/mimo-v2.6-pro` | alto | síntese com fontes |
| Ideação: geração por lentes | rotação entre `deepseek/deepseek-v4.1-flash-1017`, `xiaomi/mimo-v2.6-pro` e `z-ai/glm-5.3` (modo completo: + `moonshotai/kimi-k3.1-pro`) | — | alto | diversidade vem de famílias diferentes, não de mais agentes |
| Ideação: críticos e dossiês | `deepseek/deepseek-v4.1-flash-1017` (max) | `z-ai/glm-5.3` | máximo (aceito pelos dois) | — |
| Ideação: juízes do torneio (3 famílias) | `moonshotai/kimi-k3.1-pro` + `z-ai/glm-5.3` + `deepseek/deepseek-v4.1-flash-1017` (econômico: `xiaomi/mimo-v2.6-pro` no lugar do Kimi) | — | alto | heterogeneidade de juízes; Kimi é o mais próximo do Opus |

## 6. Custo estimado (endpoints ZDR elegíveis; volumes do §13 do SDD)

Premissas: DeepSeek V4.1 Flash 1017 a ~US$ 0,10/0,30 (média dos elegíveis baratos), MiMo-V2.6-Flash 0,14/0,28, MiMo-V2.6-Pro 0,387/0,783, GLM-5.3 ~0,5/2,5, Kimi K3.1 Pro 2/10. Tokens de raciocínio são cobrados como saída: a estimativa dobra a saída nas etapas com raciocínio alto.

| Componente | Anthropic (SDD v1) | Chinês via OpenRouter | Redução |
|---|---|---|---|
| Base diária (segmentação + triagem + extração + juiz + digest + visão) | ≈ US$ 18/mês (Sonnet) | ≈ US$ 3–6/mês | −70 a −85% |
| Mapa semanal | ≈ US$ 4/mês | < US$ 0,10/mês | ~−98% |
| Ideação econômica | ≈ US$ 20/mês | ≈ US$ 3/mês | −85% |
| Ideação completa | ≈ US$ 90/mês | ≈ US$ 18–31/mês (sem e com Kimi K3.1 Pro como juiz) | −65 a −80% |
| Migração do vault (uma vez) | ≈ US$ 11 | ≈ US$ 2 | −80% |

## 7. Riscos e cuidados

1. **Diferença de qualidade na ideação:** Kimi K3.1 Pro tem 46 contra 59 do Opus 5.5 (max). Mitigação: juízes de 3 famílias, críticos com checklists, *bake-off* com o golden set e uma rodada *premium* opcional com Claude (SDK oficial `anthropic`) só no top 5, desligada por padrão.
2. **Rotatividade de modelos:** snapshots datados (`-1017`, `-0902`) e `expiration_date`. Mitigação: modelos fixados por etapa, fallbacks de outra família, `doctor` checando expiração e *bake-off* mensal.
3. **Qualidade do endpoint:** quantização fp4 e provedores instáveis (ex.: DeepInfra *flex* com 10,7% de uptime em 24 h). Mitigação: lista permitida de quantização, `require_parameters`, fallbacks automáticos do OpenRouter.
4. **Saída estruturada inválida:** Mitigação: `strict: true` + Response Healing + validação Pydantic + 1 retentativa com o erro + próximo modelo.
5. **Privacidade e conformidade:** pesos chineses servidos por provedores dos EUA/UE com ZDR. Nenhum dado de paciente ou interno da Rede D'Or entra no sistema (§2.2 do SDD). As ideias, que podem ser propriedade intelectual, só trafegam por endpoints ZDR.
6. **Dependência de um agregador:** o OpenRouter vira ponto único. Mitigação: o gateway isola o provedor; trocar por um provedor direto (DeepInfra e Fireworks são compatíveis com a API da OpenAI) ou pela Anthropic não muda o pipeline.
7. **Preço por horário e taxa de créditos:** a estimativa inclui ~6% de taxa; o custo real vem de `usage.cost`.

## 8. Fontes

- Catálogo e endpoints: https://openrouter.ai/api/v1/models · https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash/endpoints (e equivalentes por modelo) · https://openrouter.ai/api/v1/endpoints/zdr
- Documentação: https://openrouter.ai/docs/guides/routing/provider-selection.md · https://openrouter.ai/docs/guides/features/zdr.md · https://openrouter.ai/docs/guides/privacy/data-collection.md · https://openrouter.ai/docs/guides/features/structured-outputs.md · https://openrouter.ai/docs/guides/features/plugins/response-healing.md · https://openrouter.ai/docs/guides/routing/model-fallbacks.md · https://openrouter.ai/docs/cookbook/administration/usage-accounting.md · https://openrouter.ai/docs/guides/best-practices/prompt-caching.md · https://openrouter.ai/docs/guides/features/batch-api.md · https://openrouter.ai/docs/guides/features/in-region-routing.md · https://openrouter.ai/docs/faq.md
- Qualidade: https://artificialanalysis.ai/leaderboards/models (tabela lida em 2026-11-07); contexto: https://www.benchleader.com/benchmarks/aa_intelligence_index · https://artificialanalysis.ai/articles/recent-open-weights-model-launches · https://codingfleet.com/blog/minimax-m3-vs-deepseek-v4-pro-the-open-weight-chinese-ai-showdown/
