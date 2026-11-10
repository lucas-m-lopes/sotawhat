# SDD — sotawhat 3.0 · Motor de Insights AI ∩ Medicina

**Tipo:** Software Design Document (SDD) — serve também como *spec* para desenvolvimento orientado a especificação (spec-driven).
**Data:** 2026-11-07
**Status:** v2.5 (2026-11-10), com todas as fases (P0–P6) executadas, as newsletters por RSS com texto completo, as aulas no motor HyperFrames e o radar de ferramentas:
- v2.5: radar de ferramentas, pedido em 2026-11-10: skills, plugins, MCPs e afins em alta no GitHub, fora da medicina.
  - Frentes: skills/plugins/MCPs, arquitetura de agentes e evals, economia de tokens e contexto, aulas (vídeo, animação e voz).
  - Todo dia, no fim do `run daily`, o `sotawhat radar scan` faz a descoberta (buscas do GitHub por frente e repositórios no Hacker News) e guarda o retrato das estrelas. Todo domingo, o `run weekly` mede a semana, pede o veredito a um juiz barato (tarefa `radar`) e entrega a seção "Ferramentas em alta": no relatório, no Telegram (🧪 testar · 👍 · 👎 · 🗄️ depois) e na aba Ferramentas da interface.
  - O radar não entra na triagem, no digest nem no grafo. A OSS Insight, o ranking de terceiros escolhido, está fora do ar desde 2026-03-01; o Hacker News faz esse papel.
  - Plano: `docs/superpowers/plans/2026-11-10-radar-ferramentas.md`;
- v2.4: aulas no motor HyperFrames. Você aprovou a aula 6 em 2026-11-10 ("Absolute cinema! ficou excelente.") e pediu a migração.
  - `sotawhat lessons make` agora planeja com modelos de cena (`lesson_plan_v3`): cada cena tem um modelo e um exemplo único atravessa a aula. Os modelos são `graph`, `bars`, `chart`, `timeline`, `compare`, `vectors3d`, `patches` e `volume3d`.
  - O storyboard vem antes da voz.
  - A narração é da ElevenLabs (v4, voz Klaus), e o HyperFrames renderiza o vídeo.
  - O custo da aula soma LLM e voz, em US$ e em R$ pela PTAX do Banco Central (`sotawhat/fx.py`).
  - As aulas 1–5 seguem no motor Manim, retomáveis.
  - Plano: `docs/superpowers/plans/2026-11-10-aulas-motor-hyperframes.md`;
- respostas do usuário de 2026-11-07 incorporadas: Instagram pessoal, Neo4j no Docker Desktop, LLMs chineses via OpenRouter;
- medições da P1 incorporadas: modelo de embeddings e deduplicação por título (§6.3, §6.7, D3);
- decisões de 2026-11-08 incorporadas: digest em duas seções, "IA ∩ Saúde" e "Fronteira de IA" (escolha feita a partir do golden set), e cópia do digest por e-mail (§6.7, §6.11, §16.1);
- v1.4: o Obsidian sai do projeto, e nada lê nem escreve no vault (§9, D12). A interface própria com o grafo vem para a P3, que passa a ser executada antes da P2. O grafo de entidades fica no SQLite, e o Neo4j vira espelho (§6.3, §11, D16);
- v1.5: P2 executada (fontes novas como canais com teto diário, triagem v2 com os tipos de item, Gmail por label; §11). A pedido do usuário ("continue a implantação segundo o plano SDD direto até o final"), as fases seguem sem pausa: P4, P5 e P6;
- v2.3 (+ rodada de qualidade): setas presas às pontas, verificador de layout e revisão visual G4; narração escrita para o ouvido e pausas modeladas; teto de preço por token. Aulas 3D, fases F0 e F1 do relatório `docs/research/reports/Aulas didáticas animadas em 3D.md`. Os detalhes estão no plano `docs/superpowers/plans/2026-11-09-aulas-3d-f0-f1.md`.
  - `sotawhat lessons` transforma um tema do grafo numa aula narrada em pt-BR, animada por código escrito pelo LLM e renderizado no PC: Manim no abstrato, three.js no espacial.
  - Portões: G1 (fatos), G2 (roteiro), G3 (layout e render) e G8 (sua revisão).
  - Entrega: quiz no Telegram, re-quiz em 2 dias e aba Aulas com as cenas 3D interativas.
  - O banco vai para o schema 5 (`lessons`, `lesson_answers`).
  - As ferramentas ficam isoladas em `data/tools/lessons`;
- v2.2: texto completo das newsletters. Quando o feed traz só um trecho (menos de 1.500 caracteres: MedCity, Out-Of-Pocket, Lilian Weng), o texto principal da página do artigo (trafilatura) substitui o trecho antes do filtro de IA. Cada post guarda até 8.000 caracteres, o que a triagem lê. Páginas que bloqueiam robôs ficam com o trecho (§7.1);
- v2.1: newsletters por RSS (`config/newsletters.yaml`, 24 ativas: fronteira e IA ∩ saúde, inclusive brasileiras), digests separados em notícias pelo LLM, filtro de termos de IA em inglês e português, `sotawhat newsletters add` para qualquer Substack. O Gmail fica para a Rundown AI; The Batch e AlphaSignal são ignorados no Gmail porque já têm fonte própria. Runs agendados sem janela de console (pythonw), depois que fechar a janela matou o primeiro run semanal (§7.1, §16.3);
- v2.0: P6 executada. Backup do SQLite, avaliações de triagem, extração e ideias, relatório das metas G1–G4, proposta de calibração, reparo de textos antigos e aba Hoje (§12, §11). O que depende de você está em §16.2;
- v1.7: P5 executada. Captura manual pelo Telegram, varredura do Instagram pelo Apify, curadoria das contas, visão e triagem v3 (§7.2, §11);
- v1.6: P4 executada. Inteligência semanal no SQLite com NetworkX (§6.9), motor de ideias num modo econômico mais enxuto (§8.6), ledger com votos no Telegram e na interface, relatório semanal, abas Ideias e Tendências e ferramentas novas no MCP (§6.11);
- perguntas restantes em §16.2.
**Documentos relacionados:**
- Specs anteriores: `docs/superpowers/specs/2026-06-13-sotawhat-multisource-digest-design.md`, `2026-06-14-medico-ai-intersection-design.md`, `2026-06-14-obsidian-concept-links-design.md`
- Notas de pesquisa que embasam este SDD: `docs/research/2026-11-07-insight-engine/` (fontes, plataformas similares, integrações, stack de grafo, geração de ideias, panorama hospitalar/Brasil, LLMs via OpenRouter)
- Variáveis de ambiente: `.env.example` (raiz do repositório)
- Plano da fase P0: `docs/superpowers/plans/2026-11-07-insight-engine-p0-foundation.md` (executado na branch `feature/insight-engine-p0`)
- Plano da fase P1: `docs/superpowers/plans/2026-11-08-insight-engine-p1-triage-digest.md`
- Plano da fase P3: `docs/superpowers/plans/2026-11-08-insight-engine-p3-graph-interface.md`
- Plano da fase P2: `docs/superpowers/plans/2026-11-08-insight-engine-p2-new-sources.md`
- Plano da fase P4: `docs/superpowers/plans/2026-11-08-insight-engine-p4-intelligence-ideation.md`
- Plano da fase P5: `docs/superpowers/plans/2026-11-08-insight-engine-p5-instagram.md`
- Plano da fase P6: `docs/superpowers/plans/2026-11-08-insight-engine-p6-hardening.md`

---

## 0. Resumo executivo

O `sotawhat` 2.0 é um agregador diário de papers (arXiv, Semantic Scholar, HF Daily Papers, PubMed, RSS) que escreve uma nota Markdown por item num vault Obsidian. Funciona, mas é **passivo**: não prioriza, não resume em português, não entende o conteúdo, não liga entidades reais entre si e não gera nada além de notas.

Este SDD redefine o projeto como um **motor de insights** com cinco capacidades novas:

1. **Ingestão multi-canal** — além das fontes atuais: newsletters (AlphaSignal pelo RSS oficial, The Batch pelo arquivo web, as demais via Gmail), páginas do Instagram seguidas pelo usuário, repositórios GitHub novos/em alta, registries de servidores MCP e de *agent skills*, Hugging Face Hub (modelos/datasets), medRxiv, periódicos médicos via Crossref/PubMed e listas regulatórias (FDA, ANVISA).
2. **Filtro de ruído com critério explícito** — entra a **IA/ML com aplicabilidade médico-hospitalar plausível** e, numa seção própria, a **IA de fronteira forte mesmo sem ligação com saúde** (decisão de 2026-11-08, §16.1); artigos puramente clínicos (sem IA) e notícias de IA sem substância técnica são descartados por um classificador leve treinado com o feedback do usuário mais uma rubrica avaliada por LLM, com regras de inclusão/exclusão explícitas.
3. **Grafo de conhecimento próprio** — substitui o Obsidian por um grafo (Neo4j como escolha primária; ver §6.3 e §15) com entidades extraídas por LLM (técnicas, problemas clínicos/operacionais, organizações, produtos, modelos, datasets, regulações), relações com proveniência e validade temporal, embeddings, comunidades e tendências.
4. **Gerador de ideias** — semanal e sob demanda: combina técnicas recentes × problemas hospitalares (descoberta baseada em literatura + predição de links no grafo + agentes LLM com personas), critica, verifica novidade contra bases externas, pontua com uma rubrica específica de saúde (regulatório, dados, evidência, tempo até piloto) e registra feedback.
5. **Entrega e consulta sem fricção** — digest diário (Telegram e/ou e-mail + Markdown/HTML local), relatório semanal de ideias, servidor MCP para perguntar ao grafo de dentro do Claude Code/Claude Desktop e uma interface web própria e local, com o grafo navegável (sem Obsidian).

```
 FONTES ──► COLETA ──► NORMALIZAÇÃO/DEDUP ──► TRIAGEM (LLM, rubrica) ──► EXTRAÇÃO (entidades/relações)
                                                                                   │
   feedback humano ◄── ENTREGA (digest/Telegram/MCP/web) ◄── IDEAÇÃO ◄── INTELIGÊNCIA DO GRAFO ◄── GRAFO (Neo4j)
```

Tudo roda localmente (Windows 11 + Python 3.12 + Neo4j Community no Docker Desktop), agendado diariamente, com SQLite como registro operacional e o grafo como camada de conhecimento. Os LLMs são modelos chineses de pesos abertos (DeepSeek, Xiaomi MiMo, Z.ai GLM, Moonshot Kimi) acessados pelo **OpenRouter**, apenas por endpoints com retenção zero de dados, ZDR (§6.6). Custo estimado: ≈ US$ 8–11/mês na configuração recomendada, contra ≈ US$ 45–50 com modelos Anthropic (§13).

---

## 1. Contexto e estado atual

### 1.1 O que existe hoje (sotawhat 2.0, junho/2026)

| Componente | Estado |
|---|---|
| Adapters | `arxiv` (API oficial), `semantic_scholar`, `hf_papers`, `pubmed` (E-utilities, com cláusula AND de IA), `rss` (httpx + UA de navegador, falha isolada por feed) |
| Perfis | `geral` (cs.LG/CL/AI + S2 + HF + 8 feeds de labs/blogs) e `medico` (PubMed ∩ IA, arXiv q-bio.QM/cs.LG/cs.CV, 4 feeds de periódicos) |
| Filtro | `require_any: AI_TERMS` (match de palavra inteira) só no perfil `medico` |
| Saída | 1 nota Markdown por item em `<vault>/<perfil>/<fonte>/`, frontmatter YAML, linha `**Conceitos:** [[...]]` ligando a 9 notas-conceito (= keywords de busca) |
| Dedup | `.sotawhat_seen.json` (id → caminho), apenas por id exato |
| Agendamento | `scripts/schedule_digest.ps1` + `schtasks` (08:00) |
| Testes | 49 testes, fixtures gravadas, sem rede — **passando** em 2026-11-07 |
| Dependências | `httpx`, `feedparser` (runtime); `pytest` (dev) |

### 1.2 Medições do vault atual (2026-11-07)

| Métrica | Valor |
|---|---|
| Notas no vault | 2.893 (`geral` 1.349 · `medico` 1.544) |
| Por fonte (top) | PubMed 1.106 · arXiv geral 727 · HF papers 546 · arXiv medico 404 · S2 22 · feeds RSS 88 |
| Notas adicionadas por mês | jun/26: 565 · jul: 1.108 · ago: 1.003 · set: 217 · out–nov: 0 |
| Links de conceito por nota | 1 link: 2.115 (73%) · 2: 433 · 3: 150 · 4: 106 · 5: 89 |
| Notas-conceito | 9 (uma por keyword de perfil) |
| Tarefa agendada `sotawhat-digest` | **não existe mais** no Task Scheduler (última escrita no vault: 2026-09-07) |

### 1.3 Limitações que motivam a mudança

1. **Sem priorização.** Tudo que passa no filtro vira nota: ~35 notas/dia em média, sem ordem de importância, sem "por que isso importa para mim".
2. **"Conceitos" não são conceitos.** As arestas do grafo Obsidian são as keywords que *acharam* o item, não entidades do conteúdo. O grafo tem 9 hubs e milhares de folhas — não revela nada.
3. **Perfil `geral` traz IA sem critério de aplicabilidade.** Papers de RL/difusão/agentes entram sem nenhuma ponte com medicina.
4. **Dedup só por id exato.** O mesmo paper chega via arXiv, HF e S2 com ids diferentes; a mesma notícia chega por 3 newsletters.
5. **Nada em português, nada resumido.** O corpo da nota é o abstract (ou um trecho heurístico).
6. **Canais ausentes:** e-mail (newsletters), Instagram, GitHub, MCP/skills, HF Hub, medRxiv, regulatório.
7. **Armazenamento passivo.** O Obsidian não calcula nada: sem similaridade, comunidades, tendências, lacunas, ideias.
8. **Operação frágil.** A tarefa agendada sumiu e ninguém foi avisado; não há healthcheck nem log.
9. **Feeds silenciosamente quebrados.** Os feeds da Nature (`natmachintell.rss`, `npjdigitalmed.rss`) devolveram página HTML anti-bot em 4/4 sondagens em 2026-11-07; o `parse_feed` atual produz 0 itens sem alertar (§5.1). The Gradient está parado desde fev/2026.

---

## 2. Objetivos, não-objetivos e princípios

### 2.1 Objetivos (mensuráveis)

| ID | Objetivo | Métrica de aceite |
|---|---|---|
| G1 | Ingerir diariamente todos os canais do §5 (Tier 1 e 2) | ≥ 95% das execuções diárias concluem; falha de uma fonte nunca derruba a execução |
| G2 | Reduzir ruído mantendo o essencial | Digest diário com ≤ 15 itens principais (≤ 10 em "IA ∩ Saúde" + ≤ 5 em "Fronteira de IA") + ≤ 10 linhas de "radar"; precisão de relevância ≥ 80% medida por feedback (👍/👎) após 4 semanas de calibração |
| G3 | Grafo de conhecimento próprio, consultável | Entidades extraídas com precisão ≥ 85% em amostra rotulada; consultas por técnica/problema/organização/período respondem em < 2 s; MCP server operando |
| G4 | Gerar ideias genuinamente novas e acionáveis | 5–10 ideias/semana com rubrica preenchida e verificação de novidade; ≥ 30% marcadas pelo usuário como "vale explorar" após calibração |
| G5 | Operação sem fricção | 1 comando/agendamento; nenhuma reautenticação manual por ≥ 60 dias (Gmail, Instagram, GitHub); alerta automático quando algo falha |
| G6 | Custo previsível e baixo | Custo LLM + serviços dentro do orçamento de §13 (meta: ≤ US$ 15/mês na configuração recomendada; corte duro pelo limite mensal da chave do OpenRouter), com custo real por chamada e por execução |
| G7 | Sem lock-in | Export do grafo e dos itens aprovados em JSON/CSV, mais dumps do SQLite e do Neo4j; nada depende do Obsidian |

### 2.2 Não-objetivos (escopo excluído desta versão)

- Produto multiusuário, autenticação de usuários, SaaS.
- Qualquer processamento de **dados de pacientes** ou de dados internos da Rede D'Or (o sistema só consome fontes públicas e as newsletters/posts que o usuário já recebe).
- Publicar/automatizar postagens em redes sociais.
- Substituir a leitura crítica do usuário — o motor **prioriza e sugere**; não decide.
- Scraping agressivo do Instagram ou de sites que bloqueiam bots (ver §7.2 para a estratégia conforme os termos de uso).
- Treinar modelos próprios.

### 2.3 Princípios de design

1. **Local-first, cloud-opcional.** Tudo roda na máquina do usuário; nenhum componente exige servidor externo além das APIs das fontes e do gateway de LLM (OpenRouter).
2. **Duas camadas de verdade.** SQLite é o registro operacional (o que foi coletado, quando, com que score, o que foi entregue). O grafo é a camada de conhecimento (entidades, relações, tendências, ideias). O grafo pode ser reconstruído a partir do SQLite a qualquer momento.
3. **Idempotência e isolamento de falhas.** Reexecutar o dia não duplica nada; cada fonte, cada chamada LLM e cada etapa falham isoladamente, com retry e registro.
4. **LLM barato para volume, LLM forte e diverso para síntese.** Triagem de centenas de itens/dia com o modelo mais barato; extração e síntese com raciocínio alto; ideação com os modelos mais capazes disponíveis, de famílias diferentes. A escolha de cada etapa sai de um *bake-off* com os golden sets do projeto (§6.6, §12).
5. **Critério explícito e auditável.** A rubrica de relevância e a ontologia ficam em arquivos versionados; todo descarte registra o motivo; o usuário pode consultar "por que isso ficou de fora".
6. **Feedback fecha o ciclo.** Cada item e cada ideia aceita 👍/👎/"testar"/"arquivar"; o feedback recalibra pesos e vira exemplo nos prompts.
7. **Português na saída, inglês na busca.** Resumos, "por que importa" e ideias em pt-BR; termos técnicos e consultas às fontes em inglês.
8. **Proveniência sempre.** Toda entidade/relação/ideia aponta para os itens que a originaram.
9. **Sem "AI slop".** Resumos ancorados no texto (números e afirmações só se estiverem na fonte; ids DOI/arXiv/URL só vindos de API, nunca gerados); confiança limitada pelo número de fontes independentes (1 fonte → no máximo 6/10); "nada relevante hoje" → não envia.
10. **Privacidade por padrão no LLM.** Toda chamada exige endpoint com retenção zero (ZDR) e quantização ≥ fp8. Nenhum dado de paciente ou interno entra no sistema, e as ideias, potencial propriedade intelectual, nunca trafegam por endpoint que retenha dados (§6.6, §6.13).

### 2.4 Posicionamento frente ao que já existe

Levantamento completo em `docs/research/2026-11-07-insight-engine/plataformas_similares.md` (~110 produtos/repositórios verificados em 2026-11-07). Resumo:

| Categoria | Exemplos | O que cobrem | O que falta para o nosso caso |
|---|---|---|---|
| Leitores com IA | Feedly AI Feeds (só enterprise, ~US$ 1.600/mês), Inoreader Intelligence, Readwise Reader, Refind | ingestão de RSS/newsletters + resumo; filtros "mute" | sem ranking aprendido por pessoa (exceto caixa-preta), sem grafo, sem ideação, sem Instagram/GitHub/MCP, sem foco médico/Brasil |
| Feeds acadêmicos personalizados | Scholar Inbox (embedding GTE-large + regressão logística por usuário, F1 ≈ 84), Semantic Scholar Research Feeds, Paper Digest, alphaXiv, Emergent Mind | melhor filtro de relevância publicado | só papers; sem grafo nem ideias |
| Motores de pesquisa/relatório | Perplexity, NotebookLM, Elicit, Consensus, Undermind, Edison/FutureHouse (Kosmos ≈ US$ 200/run) | relatório sob demanda | não ingerem as *suas* fontes diariamente; sem memória estruturada |
| Digests OSS com LLM | ArxivDigest, zotero-arxiv-daily, condenseit, daily-arXiv-ai-enhanced, gpt-newspaper | cron → dedup por id → embeddings → LLM barato → e-mail | frágeis operacionalmente (arXiv 406/429, cron que para); nenhum grava grafo; nenhum faz dedup semântico entre fontes |
| PKM/"second brain" com IA | Obsidian + Smart Connections/Copilot/Bases, Logseq, Tana, Mem.ai, claude-obsidian (16 k★), Basic Memory, Khoj | organização e busca no vault | sem ingestão de feeds, sem scoring, sem análise estrutural do grafo |
| Grafo/memória (bibliotecas) | Graphiti (temporal, Pydantic), LightRAG, Cognee, Mem0 (grafo só no tier pago), Kùzu (arquivado) | extração de entidades/fatos | não ingerem feeds, não detectam lacunas/tendências, não escrevem Markdown |
| Ideação | InfraNodus (único com definição determinística de *gap*: clusters importantes pouco conectados — Louvain + betweenness; lexical, na nuvem, sem novidade verificada), idea-generator-2 (37★, júri calibrado), AI co-scientist (fechado), AI Scientist | gerar/criticar/ranquear | partem de um tema, não de um grafo que cresce diariamente; sem rubrica de saúde |
| Trackers de IA em saúde | lista FDA (1.614 dispositivos, 76% radiologia, 335 em 2025), JAMA+ AI (RSS), Doctor Penguin (quase mensal em 2026), `fabianofilho/awesome-medical-ai` (lista semanal em pt-BR) | listas e notícias | nenhum tracker automático; nenhum agregador brasileiro |

**Conclusão:** nenhuma plataforma faz, de ponta a ponta, *fontes heterogêneas pessoais → relevância aprendida → grafo pessoal temporal com análise estrutural → ideias de produto julgadas e verificadas*, e nenhuma tem foco hospitalar nem Brasil. A lacuna estrutural está exatamente na junção **filtrar → grafo → idear**.

**Build × buy × reuse por etapa:** *reutilizar* nas pontas (ingestão — feedparser/httpx já existentes, APIs oficiais; PDF → Markdown com docling; embeddings locais; Neo4j; export JSON), *construir* fino no meio (classificador por perfil, dedup de histórias, inteligência estrutural em GDS/NetworkX, ideação com torneio e verificação de novidade), *comprar* quase nada (tiers gratuitos de Semantic Scholar/OpenAlex/Exa; HikerAPI/Apify para Instagram; opcionalmente InfraNodus Basic como *benchmark* de lacunas). Padrões a copiar, não a depender: `zotero-arxiv-daily` (perfil por biblioteca), `condenseit` (scoring aditivo + orçamento), `idea-generator-2` (júri calibrado + scouts), `NoviScl/AI-Researcher` (overgeneration + dedup + torneio), `SciAgentsDiscovery` (caminho no grafo → ideia), `fabric` (esqueleto de prompts).

---

## 3. Personas e casos de uso

**Persona única:** médico-empreendedor, programador em Python, atua numa rede hospitalar (Rede D'Or) e numa startup de soluções médicas; quer estar atualizado sobre IA aplicável à medicina e transformar isso em produtos/soluções.

| ID | Caso de uso | Critérios de aceite |
|---|---|---|
| US1 | **Digest diário** no celular (Telegram), por e-mail e em Markdown/HTML local: itens ranqueados em duas seções ("IA ∩ Saúde" e "Fronteira de IA"), resumo pt-BR, "por que importa para hospital/startup", link, tags | Chega todo dia no horário configurado; ≤ 10 + 5 itens + radar; cada item mostra o score e a fonte |
| US2 | **Explorar o grafo**: "o que apareceu sobre *ambient scribe* nos últimos 30 dias?", "quais técnicas estão sendo aplicadas a *fluxo de pacientes*?", "quem (orgs) está ativo em *patologia digital*?" | Respostas via CLI, MCP (Claude Code/Desktop) e web local, em < 2 s |
| US3 | **Ideias semanais**: 5–10 *idea cards* com problema, solução, técnicas, evidências (itens do grafo), novidade (arte prévia encontrada), rubrica e próximos passos | Entregues no domingo à noite / segunda cedo; registradas no ledger com versão |
| US4 | **Feedback**: 👍/👎 em itens e ideias; "testar", "arquivar", nota livre | Feedback persistido e usado na calibração; ideias rejeitadas não voltam |
| US5 | **Perguntar ao grafo dentro do Claude Code** ("use o sotawhat para listar modelos open-source de radiologia que apareceram em outubro") | Servidor MCP `sotawhat-graph` registrado em `.mcp.json`, com ferramentas de busca, vizinhança, tendências, ideias e feedback |
| US6 | **Captura manual sem fricção**: compartilhar um link (Instagram, X, LinkedIn, site) para o bot do Telegram ou para um e-mail/label | Item entra no pipeline normal no próximo ciclo, marcado como `manual` (prioridade alta) |
| US7 | **Alertas de tendência**: "a técnica X triplicou de menções em 2 semanas", "primeiro item ligando técnica X ao problema Y" | Seção "Tendências e lacunas" no relatório semanal |
| US8 | **Ferramentas para o próprio motor**: MCPs/skills/repos que melhorariam o pipeline aparecem numa seção própria | Seção "Para o motor" no digest, com sugestão de integração |

---

## 4. Requisitos

### 4.1 Funcionais

| ID | Requisito |
|---|---|
| RF1 | Coletar diariamente de todas as fontes configuradas (§5), com cursor por fonte (último id/data) e janela de retrovisão configurável |
| RF2 | Ler newsletters do Gmail por label/remetente, segmentar cada edição em itens (histórias), resolver links de rastreamento para URLs canônicas |
| RF3 | Ler posts recentes das contas do Instagram configuradas (lista editável), incluindo legenda, imagens (descrição por modelo com visão) e, opcionalmente, transcrição de reels |
| RF4 | Buscar repositórios GitHub novos/em alta por tópicos e consultas configuradas; acompanhar estrelas de repositórios observados para calcular velocidade; acompanhar releases de repositórios-chave |
| RF5 | Consultar registries de MCP e de skills por servidores/skills novos ou atualizados; classificar utilidade (médico-hospitalar / para o próprio motor) |
| RF6 | Consultar o Hugging Face Hub por modelos e datasets novos com tags médicas/biomédicas e por tendência |
| RF7 | Normalizar tudo para um `Item` único; deduplicar por id canônico (DOI/arXiv/URL) e por similaridade semântica; agrupar "mesma história" entre fontes |
| RF8 | Triar cada item com rubrica (§6.7) e regras duras; registrar score, decisão e motivo; respeitar limite diário |
| RF9 | Extrair entidades, relações, claims com métricas, maturidade, nível de evidência e regulatório (§6.8) via saída estruturada |
| RF10 | Persistir no grafo com resolução de entidades, proveniência (item → entidade/relação) e validade temporal |
| RF11 | Calcular comunidades, centralidade, tendências e lacunas; gerar o "mapa semanal" |
| RF12 | Gerar ideias (§8) semanalmente e sob demanda, com verificação de novidade e rubrica; manter ledger com versões e feedback |
| RF13 | Entregar digest diário e relatório semanal (Telegram, Markdown/HTML, e-mail opcional); expor MCP server; expor web local de visualização |
| RF14 | Receber feedback (Telegram/CLI/web) e usá-lo em calibração e prompts |
| RF15 | *(removido em 2026-11-08)* O vault antigo do Obsidian não é lido nem migrado; o grafo começa pelos itens que o próprio sotawhat coleta (§9) |
| RF16 | Exportar o grafo e os itens aprovados em JSON/CSV (`sotawhat graph export`) e manter dumps do SQLite e do Neo4j |
| RF17 | Manter a busca interativa atual (`sotawhat search ...`) funcionando |

### 4.2 Não-funcionais

| ID | Requisito |
|---|---|
| RNF1 | Execução diária completa em < 30 min na máquina do usuário (sem GPU) |
| RNF2 | Falha de qualquer fonte/etapa isolada; retries com backoff; execução reentrante (lock) |
| RNF3 | Segredos apenas em `.env`/arquivos ignorados pelo git; nunca em logs |
| RNF4 | Respeito a rate limits e termos de uso de cada API; User-Agent identificado; sem dados pessoais de terceiros além do público |
| RNF5 | Custo LLM contabilizado por execução e por etapa; teto diário configurável que degrada graciosamente (reduz lote, não quebra) |
| RNF6 | Observabilidade: log estruturado por execução, resumo de execução no digest ("coletados 412 · triados 38 · aprovados 14 · custo US$ 0,61"), alerta em falha |
| RNF7 | Testável sem rede (fixtures) e com *golden sets* para triagem/extração |
| RNF8 | Reconstrução total do grafo a partir do SQLite em < 1 h |
| RNF9 | Provedor e modelos de LLM substituíveis: modelo por etapa em configuração; nenhuma etapa depende de recurso exclusivo de um provedor; troca de modelo sem mudança de código |
| RNF10 | Chamadas de LLM só por endpoints ZDR, com saída estruturada validada; custo real registrado por chamada (`usage.cost`) |

---

## 5. Fontes de conhecimento (catálogo e prioridades)

Catálogo completo (≈ 500 URLs de feed/API sondadas em 2026-11-07 com User-Agent de navegador, status e data do último item) em `docs/research/2026-11-07-insight-engine/fontes_conhecimento.md`. Aqui, as decisões. Toda fonte vive em `config/sources.yaml` com `tier`, `mechanism`, `cadence`, `enabled` e, quando aplicável, `fallback`.

### 5.1 Estado das fontes já mapeadas e alertas

- **OK** (feed devolve itens a cliente não-navegador): Google Research, DeepMind, Hugging Face blog, Ahead of AI, Simon Willison, MarkTechPost, JMIR AI, JMIR Medical Informatics, HF Daily Papers, arXiv API, PubMed E-utilities, Semantic Scholar.
- **Alerta — Nature:** `natmachintell.rss`, `npjdigitalmed.rss` (e `nm.rss`) devolveram **página HTML de desafio anti-bot em 4/4 tentativas**; outros `.rss` da Nature alternaram. O `parse_feed` atual produz 0 itens em silêncio nesse caso → **o pipeline provavelmente está sendo servido com HTML sem perceber**. Correção: 1 fetch/feed/dia com `ETag`/intervalo, detecção de HTML (content-type/`<html`) com alerta, e **fallback por Crossref (`journals/<ISSN>/works`) e PubMed `[jour]`** para Nature Medicine, Nature Machine Intelligence, npj Digital Medicine e npj Health Systems.
- **Parados:** The Gradient (último item fev/2026), AI Tidbits (abr/2026), Doctor Penguin (jul/2026), Saúde Digital Brasil (dez/2025), InovaHC (jan/2026), feed do CFM (2024), The AI Health Podcast (2022); Papers with Code redireciona para HF Papers. Remover ou marcar `enabled: false`.
- **Bloqueados para bots** (usar Google News `site:` ou rota alternativa): Healthcare IT News, HIMSS, Health Affairs, MobiHealthNews, Health Imaging, Becker's (seções), Mayo Clinic Platform, Rock Health, NICE, RSNA Radiology:AI (RSS), Lancet Digital Health (RSS próprio), ANVISA Consultas (Turnstile).

### 5.2 As newsletters citadas pelo usuário

| Newsletter | Achado | Ingestão decidida |
|---|---|---|
| **AlphaSignal** | RSS/Atom oficiais funcionam (`https://alphasignal.ai/feed.xml`, `/atom.xml`, `/feed/news.xml`; itens NEWS/PAPER/MODEL/REPO; arquivo web só por JS; espelho Substack parado em jul/2026; plataforma própria; remetente não publicado) | **RSS primário** (sem depender de e-mail); o e-mail diário fica como redundância via label do Gmail (`from:(@alphasignal.ai)`) |
| **DeepLearning.AI — The Batch** | sem RSS (todas as rotas 404); edições semanais (sexta) em `https://www.deeplearning.ai/the-batch/issue-NNN` (378 = 06/11/2026); `sitemap.xml` lista as 393 edições; estrutura "Dear friends" + 4 matérias (What's new / How it works / Results / Why it matters / We're thinking); formulário HubSpot | **diff diário do `sitemap.xml` + leitura da edição** (uma matéria = um `NewsletterItem`); e-mail (`from:(@deeplearning.ai)`) como fallback |
| **"Runway AI"** | quase certamente a Runway (vídeo generativo; `runwayml.com` → `runway.com`, página "News \| Runway AI"); sem RSS, sem newsletter pública; alternativas com esse nome são irrelevantes (educação/moda) | **Tier 3**: scrape leve de `/news`, `/news/research` e `/changelog` (1×/dia), só se o usuário confirmar interesse (§16, pergunta 1) |

Gmail continua sendo o canal para **tudo que não tem feed/arquivo web** (outras newsletters que o usuário já recebe) e como redundância das duas acima.

### 5.3 Catálogo por tier

**Tier 1 — núcleo (12 trilhos; alto sinal, aplicável a hospital, ingestão verificada)**

| # | Fonte | Mecanismo verificado | Cadência |
|---|---|---|---|
| 1 | NEJM AI | PubMed `"NEJM AI"[jour]` + Crossref ISSN 2836-9386 | diária |
| 2 | The Lancet Digital Health (+ eClinicalMedicine) | ScienceDirect RSS `https://rss.sciencedirect.com/publication/science/25897500` (OK, 58 itens) | diária |
| 3 | Nature Medicine + npj Digital Medicine + npj Health Systems | Crossref/PubMed (fallback obrigatório; RSS da Nature com anti-bot) | diária |
| 4 | JAMA Network — coleção "Artificial Intelligence" + JAMA Network Open | RSS `https://jamanetwork.com/rss/site_9/0_44024.xml` (funcional; poucos itens, todos relevantes) | diária |
| 5 | JAMIA + Radiology: Artificial Intelligence | PubMed `[jour]` / Crossref (RSS bloqueados) | diária |
| 6 | medRxiv (`health_informatics`, `radiology_and_imaging`) + arXiv `eess.IV` | `api.biorxiv.org/details/medrxiv/<de>/<até>/0/json?category=…` + API arXiv já mapeada | diária |
| 7 | STAT — tópico IA | RSS (filtrar itens "STAT+:") | diária |
| 8 | Healthcare Dive — Health IT (+ MedTech Dive) | RSS | diária |
| 9 | FDA — lista de dispositivos com IA (CSV `https://www.fda.gov/media/178541/download?attachment`, 1.614 dispositivos, diff) + openFDA 510(k) + MedWatch RSS | download/API | semanal (CSV) / diária |
| 10 | Google Health (Keyword) RSS + OpenAI news RSS + Claude release notes RSS | RSS, filtro `health\|clinical\|medical` | diária |
| 11 | Hugging Face Hub `filter=medical` (modelos e datasets; `createdAt` + `trendingScore`) + `MONAI` `releases.atom` | API/Atom (§7.6) | diária |
| 12 | Google News RSS — consulta EN (hospital/clinical/FDA + AI) e consulta PT-BR (`"inteligência artificial" (hospital OR Anvisa OR SUS OR "saúde digital") -site:sapo.pt when:2d`) | RSS (resolver redirects; dedupe por URL canônica) | diária |

Mais os canais do §7 (Gmail, Instagram, GitHub, registries MCP, skills) e os trilhos já existentes (arXiv cs.LG/CL/AI/CV + q-bio, Semantic Scholar, HF Daily Papers, PubMed ∩ IA, labs/blogs).

**Tier 2 — manter com filtro por palavra-chave ou baixa frequência:** MedCity (IA) e Fierce Healthcare "AI and Machine Learning"; AuntMinnie (imagem); Substacks AI Health Uncut, Ground Truths (Topol), Second Opinion, Healthcare AI Guy (scrape); podcasts NEJM AI Grand Rounds, RSNA Radiology AI, Stanford AIMI/MedAI (YouTube); ClinicalTrials.gov RSS (`term="artificial intelligence"`, `dateField=LastUpdatePostDate`); JMIR, PLOS Digital Health, JBI/AI in Medicine (ScienceDirect), IEEE JBHI (volume alto → filtrar por LLM/hospital); regulação — Federal Register RSS (`"artificial intelligence" "medical device"`), EU AI Act + MDCG 2025-6 (scrape), MHRA Atom, PHTI; **Brasil** — Futuro da Saúde + Saúde Digital News (filtro `IA|inteligência artificial`), SBIS + JHI, podcast "IA med", **ANVISA Dados Abertos** (diff mensal de `TA_PRODUTO_SAUDE_SITE.csv`, 2026-10-13); AWS healthcare (categorias), Microsoft Research e NVIDIA (site-wide + filtro); um único digest geral de IA (TLDR AI ou Import AI).

**Tier 3 — baixa prioridade / substituível:** AlphaSignal (como feed geral), The Batch (idem), Rundown, Neuron, Ben's Bites, The Sequence, Latent Space, Zvi, Exponential View (IA genérica, já coberta pelos feeds primários dos labs — manter no máximo um); Runway; MIT TR/Ars/Verge/HN/lobste.rs/Reddit (ruído; Reddit com rate-limit e OAuth); Medical Futurist, Sensible Medicine, Hospitalogy, Out-Of-Pocket; CB Insights, Signify, Galen Growth, Epoch, Air Street (relatórios); portais brasileiros de gestão (Medicina S/A, Saúde Business, Setor Saúde, Portal Hospitais Brasil, Healthcare Management), Abstartups, Anahp.

**Ground truth para calibração:** Doctor Penguin (edições até jul/2026) e os itens "Updated AI/ML-based medical devices" da coleção JAMA AI servem como positivos de alta confiança para o classificador (§6.7) e para o golden set.

### 5.4 Sobreposição e dedup

Digests diários de IA ≈ feeds primários dos labs; The Batch ≈ Last Week in AI ≈ Import AI; STAT ≈ MedCity ≈ Medical Xpress ≈ Google News (re-reportam NEJM AI/Nature Medicine/JAMA); CSV FDA ≈ item JAMA AI ≈ AuntMinnie; Becker's ≈ Healthcare Dive ≈ Fierce ≈ MedCity; portais BR de gestão ≈ entre si. Consequência: dedup por DOI/URL canônica **e** por similaridade de título/embedding é obrigatória (§6.7, estágio A); fontes de Tier 2/3 trazem sobretudo duplicatas, logo entram com `confidence` menor e nunca sozinhas no topo do digest.

### 5.5 Detalhes de implementação que importam

User-Agent de navegador; 1 requisição/feed/dia com intervalo e `ETag` para Nature e Reddit; detecção de resposta HTML em vez de XML (alerta + fallback); parse tolerante de datas (Fierce: "Nov 6, 2026 4:12pm"; ScienceDirect sem `pubDate`); resolver redirects do Google News; `mailto=` em OpenAlex/Crossref; tolerar 503 transitório do Europe PMC; `filter=medical` do HF com paginação por data; CSV da FDA com diff por número de submissão.

### 5.6 Medição e poda

A priorização acima usa 1 dia de observação. Após 2–4 semanas, o relatório semanal inclui por fonte: itens coletados, itens aprovados, % de duplicatas, feedback recebido e custo — fontes com aprovação ≈ 0 por 4 semanas são desligadas automaticamente (com aviso).

---

## 6. Arquitetura

### 6.1 Visão geral do pipeline

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  sotawhat run daily  (Task Scheduler, 07:00)                                          │
│                                                                                      │
│  1 COLLECT   fontes → Item bruto (SQLite: items, source_state)         [sem LLM]      │
│  2 NORMALIZE ids canônicos, texto limpo, idioma, hash, mídia           [sem LLM]      │
│  3 DEDUP     exato (DOI/arXiv/URL) + semântico (embeddings) → cluster  [embeddings]   │
│  4 TRIAGE    mutes + classificador por perfil → rubrica LLM → score    [LR + LLM barato] │
│  5 EXTRACT   entidades/relações/claims (saída estruturada)             [LLM forte]    │
│  6 GRAPH     resolução de entidades + upsert Neo4j + proveniência      [embeddings]   │
│  7 DELIVER   digest diário (Telegram/MD/HTML/e-mail) + export JSON     [LLM forte]    │
│                                                                                      │
│  sotawhat run weekly  (domingo 20:00)                                                 │
│  8 INTEL     comunidades, tendências, lacunas, mapa semanal            [GDS/NetworkX + LLM] │
│  9 IDEATE    candidatos → geração → crítica → novidade → ranking       [LLM forte]    │
│ 10 REPORT    relatório semanal + idea cards                                           │
│                                                                                      │
│  contínuo:  bot Telegram (feedback, captura manual) · MCP server · web local          │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Estrutura do repositório (proposta)

```
sotawhat/
  __init__.py
  cli.py                 # run daily|weekly · search · ideate · feedback · serve (web) · serve-mcp · graph up|extract|sync|status|export · auth gmail|instagram · doctor
  config.py              # pydantic-settings: .env + config/*.yaml
  models.py              # Item, Cluster, Triage, Extraction, Entity, Relation, Idea, Feedback, Run (pydantic)
  store/
    db.py                # SQLite (schema versionado, migrações simples): itens, triagem, entidades, menções, relações
    vectors.py           # embeddings locais (fastembed, EmbeddingGemma): novidade, classificador e resolução de entidades
    classifier.py        # classificador de relevância por perfil (embeddings + regressão logística), retreino com feedback
  sources/               # Source base + adapters (existentes + gmail, instagram, github, mcp_registry, skills, hf_hub, medrxiv, regulatory, manual_inbox)
  pipeline/
    daily.py weekly.py   # orquestração de `run daily` / `run weekly`
    collect.py dedup.py triage.py extract.py intelligence.py ideate.py deliver.py feedback.py
  graph/                 # (P3) resolve.py: entidades e aliases · query.py: consultas da interface e do MCP · neo4j_sync.py: espelho · docker.py: `graph up`
  llm/
    openrouter.py        # cliente HTTP fino (httpx) da API OpenRouter: chat completions, json_schema estrito, ZDR, fallbacks, custo real
    gateway.py           # tarefa → modelo(s); validação Pydantic + reparo; orçamento; registro em llm_calls
    tasks.py             # matriz padrão tarefa → modelos/raciocínio/max_tokens (sobrescrita por config/llm.yaml e .env)
    anthropic_provider.py  # opcional, desligado: Claude pelo SDK oficial `anthropic` para uma rodada premium
    prompts/             # prompts versionados (triage_v1.md, extract_v1.md, ideate_*.md, ...)
    schemas.py           # modelos Pydantic das saídas estruturadas
  notify/telegram.py     # envio de mensagens (P0); o bot interativo fica em telegram_bot.py (P1)
  doctor.py              # verificação de chaves, modelos, Docker/Neo4j, última execução, custo
  taxonomy/              # domains.yaml · problems.yaml · techniques.yaml · aliases.yaml (ontologia controlada)
  mcp_server.py          # (P3) servidor MCP (`MCPServer` do SDK `mcp` 2.x) sobre o SQLite, com Cypher só leitura no Neo4j
  web/                   # (P3) FastAPI + sigma.js 3: grafo, busca, itens e votos; arquivos JS no próprio pacote (sem CDN)
  telegram_bot.py        # entrega, feedback por botões, captura manual
compose.yaml             # Neo4j CE 2026.10 no Docker Desktop (volume nomeado, portas só em 127.0.0.1; APOC + GDS na P4)
scripts/                 # schedule_daily.ps1 (run diário; votos e interface ao fazer logon) · backup.ps1; o Neo4j sobe com `sotawhat graph up`
config/                  # sources.yaml · llm.yaml · instagram_accounts.yaml · github_queries.yaml · rubric.yaml · interests.yaml
tests/                   # unit + fixtures + evals/ (golden sets)
docs/                    # sdd/ · research/ · superpowers/
data/ (ignorado)         # insight.db · raw/ · media/ · digests/ · exports/
```

Compatibilidade: `sotawhat search` continua. Os comandos do Obsidian (`digest`, `backfill-links` e a opção `--vault`) saíram em 2026-11-08 (§9).

### 6.3 Armazenamento

| Camada | Tecnologia | Papel |
|---|---|---|
| Operacional | **SQLite** (`data/insight.db`, modo WAL) | Itens brutos e normalizados, clusters, triagem, extrações, **entidades, menções e relações (o grafo que a interface mostra)**, ideias, feedback, execuções, custo LLM, cursores por fonte. Fonte de verdade. |
| Conhecimento | **Neo4j Community 2026.10 no Docker Desktop** (`compose.yaml` na raiz; dados num volume nomeado dentro do WSL2, mais rápido e seguro que montar `D:\`; portas 7474/7687 só em `127.0.0.1`; `restart: unless-stopped`); plugins APOC + Graph Data Science Community via `NEO4J_PLUGINS` só a partir da P4 | Espelho do grafo de entidades guardado no SQLite (D16): consultas Cypher no Neo4j Browser e pelo MCP (só leitura), índice vetorial e, na P4, algoritmos (Leiden, PageRank, similaridade, predição de links). A interface e o MCP não dependem dele. |
| Vetores | Índice vetorial do Neo4j (`Item.embedding`, entidades, ideias) — alternativa: LanceDB local | Dedup semântico, resolução de entidades, busca semântica, novidade de ideias. |
| Embeddings | Modelo local multilíngue: **EmbeddingGemma-300m** via `fastembed` 0.9 (CPU, 768-d, ~1,2 GB baixados uma vez para `data/models/`, ~2,4 itens/s no Ryzen 5 5500). O BGE-M3 não está no `fastembed` (medições em `embeddings_dedup.md`) | Sem custo por chamada; funciona em pt/en. Opcional por flag: Voyage AI `voyage-4-lite` (200 M tokens grátis). |
| Classificador | `scikit-learn` (regressão logística sobre embeddings + sinais sociais), modelo versionado em `data/models/` | Porta de relevância por perfil, retreinada com o feedback (§6.7). |
| Arquivos | `data/raw/<fonte>/<data>/…`, `data/media/…`, `data/digests/…`, `data/exports/…`, `data/auth/…` | Payloads brutos (auditoria), imagens/vídeos do IG, digests, exports JSON/CSV do grafo, tokens. |

**Grafo no SQLite, espelho no Neo4j (D16, 2026-11-08):** as entidades, as menções (item → entidade) e as relações extraídas ficam em tabelas do SQLite (§6.4). A interface web e o MCP consultam essas tabelas e, por isso, funcionam mesmo com o Docker Desktop fechado. `sotawhat graph sync` espelha tudo no Neo4j com `MERGE` idempotente e uma marca d'água por item (`items.graph_synced_at`), o que dispensa o `graph_outbox`; `sotawhat graph sync --rebuild` recria o espelho do zero (RNF8). Com isso, o backend `memory` e a alternativa LadybugDB deixam de ser necessários. A decisão de stack e as alternativas avaliadas (Memgraph, FalkorDB, Kùzu arquivado, AuraDB Free) estão em §15 e em `docs/research/…/grafo_stack.md`.

### 6.4 Modelo de dados operacional (SQLite)

```
items(id TEXT PK, kind, source, source_id, canonical_url, doi, arxiv_id, title, authors_json, published_at,
      fetched_at, lang, text, html, media_json, raw_json, content_hash, cluster_id, status, is_manual,
      graph_synced_at)
clusters(id PK, representative_item_id, created_at)                 -- "mesma história" entre fontes
triage(item_id PK, run_id, pre_score, classifier_version,          -- estágio A (§6.7)
       model, prompt_version, scores_json,                          -- estágio B: A/B/C/D (0–5), total
       decision, reason, summary_pt, why_it_matters_pt,
       tags_json,                                                   -- {domains, problem_types, techniques, evidence_stage, stakeholders, br_applicability, cfm_risk, substance, audience}
       cost_usd)
classifier_models(version PK, trained_at, n_labels, metrics_json, path)
extractions(item_id PK, run_id, status, model, prompt_version, payload_json, error, cost_usd, attempts)  -- Extraction (§6.8)
entities(id PK, type, name, norm, category, first_seen, last_seen, mention_count)  -- UNIQUE(type, norm)
entity_aliases(type, alias_norm, entity_id, alias)                   -- PK(type, alias_norm): nomes alternativos
entity_mentions(item_id, entity_id, role)                            -- main | used | mentioned | tag
entity_relations(subject_id, predicate, object_id, item_id, valid_from)   -- uses, addresses, developed_by, …
entity_merges(id PK, entity_id, name, method, score, decided_at)     -- exact | alias | judge (auditoria)
entity_embeddings(entity_id PK, model, dim, vector)                  -- nomes, para a resolução
ideas(id PK, version, parent_id, created_at, status, title, card_json, scores_json, novelty_json, run_id)
feedback(id PK, target_type, target_id, value, note, created_at, channel)       -- item | idea | entity
runs(id PK, kind, started_at, finished_at, stats_json, cost_usd, ok, error)
source_state(source PK, cursor_json, last_ok_at, last_error, consecutive_failures)
llm_calls(id PK, run_id, task, requested_model, model, provider, generation_id,   -- model/provider efetivos
          input_tokens, output_tokens, reasoning_tokens, cached_tokens,
          cost_usd, latency_ms, status, error, created_at)                -- cost_usd = usage.cost (real)
star_snapshots(repo, date, stars, forks)                            -- velocidade de repositórios
```

`Item.kind ∈ {paper, article, newsletter_item, ig_post, repo, mcp_server, skill, model, dataset, product, regulation, manual}`.

### 6.5 Ontologia do grafo

Princípio: três famílias de nós — **fonte** (`Item` e subtipos, com proveniência), **semânticos** (técnica, capacidade, problema, domínio, dado, organização, produto/solução, modelo, dataset, regulação) e **derivados** (claim, ideia, comunidade, tendência). Vocabulários controlados em `sotawhat/taxonomy/*.yaml` dão chaves estáveis para domínios, tipos de problema e famílias de técnica; nomes específicos (ex.: *MedGemma 1.5*, *Dragon Copilot*) são entidades abertas resolvidas por alias + embedding (§6.8). Taxonomia completa com exemplos em `docs/research/2026-11-07-insight-engine/panorama_saude_ia.md` (KQ5).

**Vocabulários controlados (taxonomy/)**

| Eixo | Chaves | Exemplos |
|---|---|---|
| **A · Domínio clínico/operacional** (23) | A01 documentação clínica · A02 apoio à decisão · A03 radiologia/imagem · A04 patologia/laboratório · A05 terapia intensiva/deterioração · A06 emergência/triagem · A07 centro cirúrgico · A08 oncologia · A09 cardiologia/sinais · A10 farmácia clínica · A11 enfermagem · A12 fluxo/leitos/capacidade · A13 força de trabalho/escalas · A14 ciclo de receita/glosas/autorização · A15 suprimentos/OPME/logística · A16 experiência/acesso do paciente · A17 qualidade/segurança/infecção · A18 monitoramento remoto/wearables/hospital-em-casa · A19 telemedicina · A20 pesquisa clínica/dados/RWE · A21 educação médica · A22 governança de IA/regulação · A23 atenção primária/crônicos | A14 ↔ Rivio, Mater Dei "Maria"; A05 ↔ eCART, UTIs inteligentes do SUS |
| **B · Tipo de problema** (15) | B01 sobrecarga documental/burnout · B02 erro/atraso diagnóstico · B03 deterioração não detectada · B04 segurança do paciente · B05 variabilidade de conduta · B06 ineficiência de fluxo/espera · B07 escassez de força de trabalho · B08 perda de receita/glosas · B09 custo/desperdício · B10 acesso/experiência · B11 fragmentação de dados/interoperabilidade · B12 privacidade/conformidade · B13 confiabilidade/segurança da IA · B14 produtividade em pesquisa · B15 competência/confiança profissional | |
| **C · Família de técnica** (21) | C01 ASR/documentação ambiente · C02 LLMs/RAG/Q&A clínico · C03 agentes/orquestração · C04 modelos de fundação multimodais · C05 visão computacional diagnóstica · C06 patologia computacional · C07 visão ambiente/vídeo · C08 séries temporais/sinais · C09 preditivos tabulares em EHR · C10 generativos de eventos médicos · C11 otimização/pesquisa operacional · C12 PLN de extração/codificação · C13 automação de processos · C14 robótica/controle · C15 edge/wearables · C16 federado/privacidade · C17 dados sintéticos/pacientes simulados · C18 avaliação/benchmarks/monitoramento · C19 modelos pequenos/abertos/fine-tuning local · C20 interoperabilidade/engenharia de dados · C21 XR/BCI | |
| **D · Estágio de evidência** | D0 ideia/opinião · D1 pesquisa de fronteira · D2 estudo revisado por pares · D3 RCT/validação externa · D4 autorização regulatória · D5 implantação comercial em escala · D6 ROI/desfecho independente | |
| **E · Stakeholder** | médico · enfermagem · farmácia · radiologia/patologia · UTI · PS · CC · oncologia · RCM/admin · suprimentos · paciente · qualidade · pesquisa/IDOR · educação · TI/governança · operadora · regulador | |
| **F · Aplicabilidade Brasil** | F0 irrelevante · F1 global adaptável · F2 depende de regulação BR · F3 específico BR (TISS/TUSS/RNDS/SUS/Rede D'Or) | |
| **G · Risco CFM 2.454/2026 (Anexo II)** | baixo (agendamento, logística, chatbots informativos, sumarização interna) · médio (apoio à decisão sem execução autônoma) · alto (influência direta em decisão crítica ou ação automatizada) | |

**Nós**

| Label | Papel | Propriedades principais |
|---|---|---|
| `Item` (+ sublabel: `Paper`, `Article`, `NewsletterItem`, `Post`, `Repo`, `MCPServer`, `Skill`, `ModelRelease`, `DatasetRelease`, `ProductNews`, `RegulationNews`, `Manual`) | unidade ingerida | `id` (canônico: doi / arxiv_id / github_full_name / URL normalizada / ig_shortcode), `title, url, source, published_at, ingested_at, lang, summary_pt, why_it_matters_pt, scores{A,B,C,D,total}, evidence_stage (D0–D6), br_applicability (F0–F3), cfm_risk (G), audience[], embedding, content_hash` |
| `Chunk` (opcional, itens longos) | proveniência fina | `text, order, embedding` + `FROM_ITEM`, `NEXT_CHUNK` |
| `Technique` | método/modelo/capacidade de IA | `name, family (C01–C21), aliases[], description_pt, first_seen, last_seen, mention_count, trend_7d, pagerank, community_id, importance, embedding, merged_from[]` |
| `Capability` | o "B" do modelo ABC (verbo-objeto intermediário) | `name, embedding, first_seen` |
| `Problem` | dor/JTBD clínico ou operacional | `name, type (B01–B15), stakeholder (E), domain (A), metric, frequency, first_seen, last_seen, embedding` |
| `Domain` | A01–A23 (fechado) | `key, name_pt` |
| `DataSource` | tipo de dado exigido | `name, structured, lgpd_sensitivity, availability_rede_dor (desconhecido/parcial/sim)` |
| `Organization` | lab, fornecedor, hospital, operadora, regulador, universidade | `name, kind, country` |
| `Person` | autores/criadores públicos | `name, role, handle` |
| `Model` / `Dataset` | artefatos nomeados | `name, family, params, license, modality, release_date, url` |
| `Solution` | produto/startup/sistema existente (incl. incumbentes) | `name, vendor, country, business_model, regulatory_status, incumbent, cfm_risk` |
| `Regulation` | norma/decisão | `name, jurisdiction, issuer (ANVISA/CFM/ANPD/ANS/MS/FDA/EU), effective_from, class` |
| `Claim` | afirmação com métrica | `text, metric, value, baseline, polarity, confidence, evidence_stage` |
| `Trend` | agregado temporal calculado | `window_start, window_end, velocity, z_score` |
| `Idea` | idea card (§8.5) | `title, version, status, scores{}, confidence, lens, persona, created_at, run_id` |
| `Community` | agrupamento calculado (Leiden/Louvain) | `level, label_pt, summary_pt, algorithm, computed_at` |
| `Source` | origem configurada | `name, tier, kind` |
| `Episode` | execução de ingestão/extração | `run_id, started_at, model, prompt_version, cost_usd` |

**Relações** (todas com `created_at`, `valid_from`, `invalid_at`, `confidence`, `extracted_by` = modelo + versão do prompt, e `source_item_ids[]`/`source_chunk_ids[]` como proveniência)

| Relação | De → Para |
|---|---|
| `MENTIONS` | Item → qualquer nó semântico (`role`) |
| `USES_TECHNIQUE` · `PROPOSES` · `EVALUATED_ON` · `ADDRESSES_PROBLEM` · `IN_DOMAIN` · `PUBLISHED_BY` · `CITES` · `DERIVED_FROM` · `STATES` (→ Claim) · `INGESTED_IN` (→ Episode) · `FROM_SOURCE` | Item → Technique / Technique∣Model / Dataset / Problem / Domain / Organization∣Person / Item / Item / Claim / Episode / Source |
| `SAME_STORY` (`cluster_id`) · `SIMILAR_TO` (`score`, calculada sem LLM) | Item ↔ Item |
| `ENABLES` · `REQUIRES_DATA` | Technique → Capability · Capability∣Solution → DataSource |
| `ADDRESSES` | Capability∣Solution → Problem |
| `USES` · `COMPETES_WITH` · `DEPLOYED_AT` · `REGULATED_AS` | Solution → Technique · Solution ↔ Solution · Solution → Organization · Solution∣Model → Regulation |
| `GOVERNS` | Regulation → Domain∣Technique |
| `SUPERSEDES` | Technique → Technique · Model → Model · Idea → Idea |
| `APPLIED_TO` (**derivada**: `evidence_count, first_seen, last_seen, item_ids[]`) · `CO_OCCURS` (**derivada**: `weight, window`) | Technique → Problem · nó semântico ↔ nó semântico |
| `EVIDENCE_FOR` · `CONTRADICTS` | Claim → Claim∣Idea |
| `COMBINES` · `TARGETS` · `NEEDS` · `INSPIRED_BY` | Idea → Technique · Problem · DataSource · Item∣Claim∣Community |
| `MEMBER_OF` · `COMPOSED_OF` · `AFFILIATED_WITH` | nó semântico → Community · Trend → Technique∣Problem · Person → Organization |

**Padrões permitidos** (lista explícita de triplas `(label origem, relação, label destino)` em `taxonomy/patterns.yaml`): o que a extração propõe fora da lista é rebaixado para `RELATED_TO {needs_review: true}` ou rejeitado — mesma ideia dos `patterns` do neo4j-graphrag e do `edge_type_map` do Graphiti.

**Temporalidade e proveniência:** `valid_from` = data de publicação do item que originou o fato (não a data de ingestão); `invalid_at` é setado por `SUPERSEDES`, por contradição entre `Claim`s ou por decaimento (último `last_seen` antigo + importância baixa) — **nunca se apaga**. Índices vetoriais em `Item.embedding`, `Technique/Problem/Capability/Solution.embedding`, `Idea.embedding`. Índice de unicidade em `Item.id` e `(label, name_normalized)` dos nós semânticos.

### 6.6 Camada LLM (OpenRouter + modelos chineses de pesos abertos)

Decisão do usuário (§16.1, item 12): modelos chineses comparáveis aos da Anthropic, via OpenRouter, para reduzir drasticamente o custo. Evidência, preços por endpoint e documentação em `docs/research/2026-11-07-insight-engine/llm_openrouter.md`, todos consultados diretamente em 2026-11-07.

- **Gateway único** (`llm/gateway.py`) sobre um cliente HTTP fino da API do OpenRouter (`llm/openrouter.py`, `httpx`, `POST /api/v1/chat/completions`; sem SDK de terceiros). O gateway mapeia tarefa → modelo(s) e cuida de saída estruturada, política de privacidade, fallbacks, retries, orçamento e registro do custo real.
- **Saída estruturada:** `response_format: {type: "json_schema", json_schema: {name, strict: true, schema}}`, com o schema gerado a partir do modelo Pydantic, mais o plugin `response-healing` e validação Pydantic no cliente. Se a validação falhar, há 1 retentativa com o erro no prompt; se falhar de novo, o próximo modelo da lista assume. JSON não validado nunca entra no pipeline.
- **Privacidade por padrão (todas as chamadas):** `provider: {zdr: true, data_collection: "deny", require_parameters: true, quantizations: ["fp8","bf16","fp16","fp32","unknown"], sort: "price", allow_fallbacks: true}`. Na conta do OpenRouter: ZDR imposto em "All other models", *logging* e "uso de entradas/saídas" desligados, chave dedicada com limite mensal de gasto. Os pesos são chineses, mas a inferência roda em provedores dos EUA/UE com retenção zero (DeepInfra, Fireworks, Together, DigitalOcean, Nebius, Parasail, Cohere etc.). Modelos servidos só pela nuvem de origem, como Qwen Max/Flash na Alibaba, ficam de fora por não serem ZDR.
- **Fallbacks:** campo `models` com 2–3 modelos de famílias diferentes por etapa; o OpenRouter também troca de provedor sozinho quando um endpoint falha.
- **Custo real:** cada resposta traz `usage.cost` (US$), tokens de entrada, saída, raciocínio e cache, e os `model`/`provider` efetivos, tudo gravado em `llm_calls`. Antes de cada chamada, o gateway compara o gasto do dia/semana/mês com os tetos (§13).
- **Cache:** prefixos estáveis (rubrica, ontologia, few-shot) no início do prompt. DeepSeek e Moonshot fazem cache implícito com roteamento "sticky".
- **Batch:** a Batch API do OpenRouter (~50% do preço, ≤ 24 h) não oferece ZDR e **não é usada**. Nos modelos escolhidos, o endpoint síncrono ZDR mais barato custa o mesmo ou menos que a variante `:batch`. Lotes grandes, como o backfill da extração, rodam síncronos com concorrência de 4–8.
- **Raciocínio:** `reasoning: {effort: low|high|max, exclude: true}` por etapa. Tokens de raciocínio são cobrados como saída; `exclude` só evita trafegá-los. O catálogo de 2026-11-07 impõe duas restrições: GLM-5.3, GLM-5.3-Flash e MiniMax-M3.1-Flash têm raciocínio obrigatório e recusam `none`, e o DeepSeek V4.1 Flash 1017 recusa `medium`. Por isso cada cadeia de fallback usa um nível aceito por todos os seus modelos, e o `doctor` confere cada modelo contra o catálogo vivo.
- **Modelos por etapa:** padrão em `llm/tasks.py`, sobrescrito por `config/llm.yaml` e pelas variáveis `SOTAWHAT_MODEL_*`. O *bake-off* da P1 valida a escolha final.

| Etapa | Primário → fallbacks | Raciocínio | Faixa Anthropic equivalente (AA Index, nov/2026) |
|---|---|---|---|
| Triagem (centenas/dia) | `deepseek/deepseek-v4.1-flash-1017` → `xiaomi/mimo-v2.6-flash` → `z-ai/glm-5.3-flash` | baixo | Haiku 5.5 high (29 × 30) |
| Segmentação de newsletters | `xiaomi/mimo-v2.6-flash` → `deepseek/deepseek-v4.1-flash-1017` | baixo | Haiku 5.5 |
| Visão (imagens do Instagram) | `xiaomi/mimo-v2.6-flash` → `z-ai/glm-5.3-flash` → `minimax/minimax-m3.1-flash` | baixo (GLM e MiniMax não aceitam desligar) | Haiku 5.5 |
| Extração de entidades/relações | `deepseek/deepseek-v4.1-flash-1017` → `xiaomi/mimo-v2.6-pro` → `z-ai/glm-5.3` | alto | Sonnet 5.5 medium (31–33) |
| Juiz de resolução de entidades | `deepseek/deepseek-v4.1-flash-1017` → `xiaomi/mimo-v2.6-flash` | baixo | — |
| Digest, mapa semanal, meta-review | `deepseek/deepseek-v4.1-flash-1017` → `xiaomi/mimo-v2.6-pro` | alto | Sonnet 5.5 medium |
| Ideação — geração por lentes | rotação `deepseek/deepseek-v4.1-flash-1017` · `xiaomi/mimo-v2.6-pro` · `z-ai/glm-5.3` (+ `moonshotai/kimi-k3.1-pro` no modo completo) | alto | Sonnet 5.5 medium; Kimi (46) ≈ Opus 5.5 medium (48) |
| Ideação — críticos e dossiês | `deepseek/deepseek-v4.1-flash-1017` (máximo) → `z-ai/glm-5.3` | máximo | Sonnet 5.5 medium |
| Ideação — juízes do torneio | 3 famílias: `moonshotai/kimi-k3.1-pro` + `z-ai/glm-5.3` + `deepseek/deepseek-v4.1-flash-1017` (econômico: `xiaomi/mimo-v2.6-pro` no lugar do Kimi) | alto | — |

- **Limite honesto:** nenhum modelo chinês alcança o Opus 5.5 em esforço alto ou máximo. O melhor de pesos abertos, Kimi K3.1 Pro, marca 46 contra 59. Nas etapas de volume a diferença é irrelevante. Na ideação, juízes heterogêneos a compensam em parte (menos viés de autopreferência), e o *bake-off* mede o que sobra. Há um caminho **opcional e desligado**: `llm/anthropic_provider.py` (SDK oficial `anthropic`, `ANTHROPIC_API_KEY`) para uma rodada *premium* só no top 5 de ideias (≈ US$ 1–2/semana), ativado apenas se o *bake-off* mostrar ganho claro.
- **Bake-off de modelos** (`sotawhat eval models`, na P1 e depois mensal): roda os golden sets de triagem e extração (§12) em 3–4 candidatos por etapa e compara acurácia, taxa de JSON válido, qualidade do pt-BR, latência e custo. O vencedor vira o padrão em `config/llm.yaml`. Como o catálogo muda todo mês (snapshots datados, `expiration_date`), o `doctor` avisa quando um modelo configurado expira, some ou perde endpoints ZDR elegíveis.
- **Prompts versionados** em `llm/prompts/*.md`; a versão fica gravada em cada triagem/extração para permitir reprocessamento quando o prompt mudar.
- **Idioma:** instruções e exemplos em inglês; campos de saída `summary_pt`, `why_it_matters_pt` em português.

### 6.7 Triagem — relevância em dois estágios

**Estágio A — sem LLM (barato, determinístico, personalizável):** (1) *mute filters* editáveis (`config/mute.yaml`: termos, domínios, autores, fontes); (2) dedup exato por id canônico; (3) mesma história por **título quase idêntico** (normalização + Jaccard de tokens ≥ 0,8 ou SequenceMatcher ≥ 0,92, números iguais) → `SAME_STORY`. Medição de 2026-11-07: em 5 modelos locais, o cosseno não separa "mesma história" de "mesmo tema, outro trabalho" (gap de −0,05 a −0,12), então o embedding entra na novidade D e no classificador, não na fusão. No vault antigo, a regra achou 11 duplicatas reais em 2.893 títulos, 9 entre fontes diferentes, sem falso positivo (`embeddings_dedup.md`). Um juiz LLM para pares de notícias parecidas entra com as newsletters (P2); (4) **classificador leve por perfil** (embedding local + regressão logística treinada com os 👍/👎 do usuário, padrão Scholar Inbox — F1 ≈ 84 publicado) + sinais sociais (upvotes HF, estrelas/velocidade GitHub, nº de fontes independentes) → `pre_score`. **Arranque a frio:** enquanto houver < 100 avaliações, o estágio A só deduplica e aplica os *mutes*, e o estágio B roda em todos os itens restantes (com o modelo de triagem isso custa centavos/dia); a partir de 100 avaliações o classificador vira a porta e o LLM só vê o top-N (N = 80/dia). Retreino a cada execução; *active learning* opcional (pedir voto em 2–3 itens "incertos" por dia).

**Estágio B — LLM (modelo de triagem, padrão `deepseek/deepseek-v4.1-flash-1017`, saída estruturada), por item (texto truncado a ~2.500 tokens):**

| Eixo | Pergunta | 0 | 5 |
|---|---|---|---|
| **A · Fronteira de IA/ML** | O item traz avanço técnico, resultado forte, release relevante ou ferramenta nova de IA/ML? | sem conteúdo de IA | avanço claro, com resultado/artefato |
| **B · Aplicabilidade médico-hospitalar** | Há aplicação direta ou plausível (≤ 2 anos) em medicina, hospital, bioengenharia médica ou gestão hospitalar? | nenhuma plausível | aplicação direta demonstrada ou óbvia |
| **C · Acionabilidade** | Dá para usar/testar: código, modelo, dataset, API, produto disponível, caminho regulatório claro? | nada disponível | artefato aberto e pronto |
| **D · Novidade para o grafo** | Já temos isso? Calculada sem LLM: maior cosseno com os itens dos últimos 30 dias, com limiares em `config/rubric.yaml` (0,70 · 0,76 · 0,82 · 0,88 · 0,94); a mesma história vira `SAME_STORY` | duplicado | inédito |

- **Regras de inclusão** (qualquer uma basta; mais regras → mais pontos): (1) produto/plataforma de IA em uso por hospitais, redes, laboratórios, operadoras ou SUS, com substância (clientes nomeados, nº de sítios, resultados, autorização regulatória, preço); (2) evidência sobre IA em saúde (RCT, validação externa, avaliação independente, relatos de falha/incidente/recall); (3) regulação e governança (ANVISA, CFM, ANPD, ANS, MS/RNDS, PL 2338, FDA, EU AI Act, CHAI, FHIR/TISS); (4) **capacidade de IA de fronteira com ponte plausível**, mesmo sem contexto médico (novos modelos multimodais/3D/longo contexto, ASR multilíngue, agentes com ferramentas/MCP, modelos pequenos abertos ou on-device, avaliação/calibração/detecção de alucinação/drift, privacidade, robótica, BCI, visão em vídeo) — regra: entra se mapear para ≥ 1 tipo de problema B01–B15 e ≥ 1 família C01–C21; (5) movimentos de incumbentes e capital (Epic, Oracle Health, Microsoft, Google, OpenAI, Anthropic, NVIDIA, Philips, GE, Siemens, MV/Tasy, Dasa, Einstein, Rede D'Or; rodadas/M&A de healthtechs com IA); (6) operações, ciclo de receita e operadoras quando há componente de dados/IA; (7) Brasil/LatAm em saúde digital/IA; (8) dispositivos e bioengenharia com validação ou status regulatório; (9) educação médica/força de trabalho com IA; (10) metodologia de avaliação, segurança, viés, desidentificação, dados sintéticos em saúde.
- **Regras de exclusão (ruído):** (1) pesquisa clínica sem IA/dados (fármacos, técnica cirúrgica convencional, epidemiologia, guidelines) — salvo se tratar de ferramenta digital ou mudar um protocolo que um produto de IA implementa; (2) IA genérica sem ponte (apps de consumo, chips/datacenters, IA em finanças/varejo/jogos, disputas corporativas, "AGI"/opinião); (3) marketing sem substância (press release sem números/clientes/evidência, listicles, webinars, prêmios, vagas); (4) opinião/"thought leadership" sem fato novo, explicadores introdutórios; (5) descoberta de fármacos/bioinformática muito a montante sem ligação com hospital/IDOR (baixa prioridade, não núcleo); (6) wellness de consumo sem validação; (7) política/reembolso sem componente digital; (8) duplicatas, republicações, conteúdo > 18 meses sem caráter fundacional; (9) itens com dado de paciente identificável (descartar e não armazenar); (10) regras puramente locais de outro país sem lógica transferível.
- **Regras duras (descartam antes da nota):** exclusões 1, 2, 3 e 9 acima; duplicata (`D = 0`) vira `SAME_STORY`. A exclusão 2 vale só para notícia de IA sem substância técnica; paper, modelo, ferramenta ou resultado técnico sem ligação com saúde é avaliado normalmente (com `B` 0–1) e pode entrar em "Fronteira de IA". Notícia excluída pela regra 2 com `A ≥ 4` ainda vira linha no *Radar*.
- **Score:** `total = 0,35·A + 0,35·B + 0,20·C + 0,10·D` (pesos em `config/rubric.yaml`, recalibrados com feedback); penalidades: fonte só do fornecedor sem terceiro (−0,5), fonte fraca/agregador (−0,5), conflito entre fontes não resolvido (sinalizar). Aprovado em **"IA ∩ Saúde"** se `total ≥ 3,2` **e** `B ≥ 2`. O que não entrou vai para **"Fronteira de IA"** se `A ≥ 4`, substância ≥ 2 e `total_fronteira = 0,60·A + 0,25·C + 0,15·D − penalidades ≥ 3,6` (decisão de 2026-11-08: no golden set, 24 dos 51 itens "incluir" eram IA de fronteira sem ligação com saúde). Sem ligação com saúde (`B ≤ 1`) e com `A ≥ 4`, o resto vira linha no *Radar*. Limite diário: 10 em "IA ∩ Saúde" (ordenados por `total`, desempate por `B`), 5 em "Fronteira de IA" (por `total_fronteira`; o excedente desce para o radar), 10 no radar. Limiares e pesos em `config/rubric.yaml`, a recalibrar com o golden set e os votos.
- **Saídas da triagem:** `scores{A,B,C,D,total}`, `decision`, `reason` (1 frase), `summary_pt` (≤ 60 palavras), `why_it_matters_pt` (≤ 40 palavras, foco hospital/startup), `domains[] (A)`, `problem_types[] (B)`, `techniques[] (C)`, `evidence_stage (D0–D6)`, `stakeholders[] (E)`, `br_applicability (F0–F3)`, `cfm_risk (G)`, `substance (0–3)`, `audience` (clínico/gestão/engenharia/motor).
- **Few-shot no prompt:** exemplos rotulados como "FDA libera Aidoc CARE com 14 indicações" → incluir (A03; B02, B03; C04, C05; D4; F1; G alto); "Google lança modelo aberto 4B com entrada de volumes 3D" (sem menção clínica) → incluir pela ponte (A03/A04; C04, C19; B02); "novo chip para datacenters" → excluir; "ensaio fase III de anticorpo em asma" → excluir; "ANS muda indicadores de glosa" → incluir (A14; B08, B11; F3). Lista completa em `panorama_saude_ia.md` (KQ6).
- **Calibração:** *golden set* rotulado pelo usuário (≥ 150 itens) em `tests/evals/triage/`; métricas precision/recall; o feedback diário alimenta o set.

### 6.8 Extração de entidades e relações

Implementação na P3 (`sotawhat/pipeline/extract.py`, `sotawhat/graph/resolve.py`, prompt `extract_v1.md`). Entram os itens aprovados na triagem (`main`, `frontier` e `radar`); duplicatas, rejeitados e silenciados ficam de fora. Saída estruturada (Pydantic, JSON estrito) por item:

```python
EntityType = Literal["technique", "model", "dataset", "organization", "product", "problem", "regulation"]

class ExtractedEntity(BaseModel):
    name: str            # nome canônico em inglês; nomes próprios como escritos no texto (com a versão)
    type: EntityType
    category: str        # C01–C21 para técnica/modelo, B01–B15 para problema, "none" no resto
    role: Literal["main", "used", "mentioned"]

class ExtractedRelation(BaseModel):
    source: str
    relation: Literal["uses", "addresses", "developed_by", "evaluated_on", "compared_with", "builds_on",
                      "regulated_by"]
    target: str

class ExtractedClaim(BaseModel):
    text_pt: str         # pt-BR; números só se estiverem no texto
    metric: str
    value: str

class Extraction(BaseModel):
    entities: list[ExtractedEntity]          # até 12
    relations: list[ExtractedRelation]       # até 10, só entre as entidades listadas
    claims: list[ExtractedClaim]             # até 5
    maturity: Literal["research", "prototype", "product", "deployed", "regulated", "unclear"]
    data_modalities: list[Literal["imaging", "ehr", "text", "audio", "signals", "genomics", "video", "other"]]
```

Pessoas ficam de fora nesta versão (LGPD, §6.13); as organizações respondem "quem está ativo". As categorias da triagem (domínios A, tipos de problema B e famílias de técnica C) também viram nós do grafo, sem custo de LLM, ligados a todos os itens aprovados.

**Resolução de entidades (upsert):**
1. Normalização: minúsculas, sem acentos nem pontuação, sem "the". O acrônimo entre parênteses vira alias: "retrieval-augmented generation (RAG)". Técnicas e problemas ficam no singular.
2. Correspondência exata por (tipo, nome normalizado) na tabela de aliases, que começa com `config/aliases.yaml`. Modelo e produto formam um grupo só, porque a fronteira entre eles varia de texto para texto.
3. Candidatos parecidos, sempre com os mesmos números ("GPT-4o" ≠ "GPT-4.1", "MedGemma 1.5" ≠ "MedGemma 2"): semelhança de texto, um nome contido no outro ("DeepMind" ⊂ "Google DeepMind") ou cosseno alto entre os embeddings dos nomes. Os candidatos vão a um juiz LLM barato (tarefa `resolve`), com teto de chamadas por run. Acima do teto, ou sem resposta, cria-se uma entidade nova, porque separar é melhor que fundir errado.
4. Toda fusão fica registrada em `entity_merges` (método, nota, data), para auditoria. Relações fora dos padrões permitidos (tipo de origem × tipo de destino, por relação) são descartadas e contadas.

### 6.9 Inteligência do grafo (semanal + diário leve)

| Função | Método | Uso |
|---|---|---|
| Comunidades | Leiden (GDS) ou Louvain (NetworkX) sobre `CO_OCCURS`/`USES`/`ADDRESSES` | agrupar o mapa semanal; rotular com LLM |
| Importância | PageRank ponderado por recência e feedback | ordenar entidades no digest/MCP |
| Tendências | contagem de itens por entidade em 7 d vs 28 d anteriores (z-score) | "em alta" / "esfriando" |
| Lacunas (base da ideação) | (a) **lacunas estruturais** no estilo InfraNodus: pares de comunidades importantes (alto PageRank agregado) e pouco conectadas, e nós-ponte de alta *betweenness*; (b) técnicas recentes sem `APPLIED_TO` para problemas hospitalares; (c) problemas com muitas menções e poucas técnicas; (d) caminhos A–B–C (descoberta baseada em literatura via `Capability`) | candidatos a ideias (§8.3, estágio 1) |
| Similaridade | `SIMILAR_TO` via índice vetorial (k-NN) | dedup, "relacionados", novidade |
| Mapa semanal | LLM resume cada comunidade ativa (o que mudou, por quê, próximos sinais) | relatório semanal |

**Como ficou na P4** (`sotawhat/graph/intelligence.py`): tudo roda no SQLite com NetworkX 3.7, numa projeção dos últimos 90 dias de itens aprovados. Assim o GDS do Neo4j não é necessário (D16).
- **Comunidades:** Louvain ponderado, com semente fixa, sobre as coocorrências e as relações tipadas (estas contam em dobro). As 8 maiores ganham rótulo e resumo do LLM; as demais ficam com os três nomes principais.
- **Tendências:** z de Poisson, (recentes − esperado) / √(esperado + 1), nos 7 dias contra os 28 anteriores, mais as entidades que surgiram na semana.
- **Lacunas:** (b) técnicas recentes sem ligação com os problemas mais citados, (a) pontes entre comunidades de técnicas e de problemas que quase não se tocam, e serendipidade (pares a 3 ou mais saltos de distância).
- **Ficaram para depois:** PageRank, o item (c) e os caminhos via `Capability`. A ontologia de ideação (§8.2) ainda não tem nós `Capability`.

### 6.10 Motor de ideias

Ver §8.

### 6.11 Entrega e interfaces

| Canal | Conteúdo | Implementação |
|---|---|---|
| **Telegram** (principal) | digest diário (resumo + itens com botões 👍/👎/🧪), relatório semanal (P4: um cabeçalho e uma mensagem por ideia com 👍 explorar · 👎 · 🧪 testar · 🗄️ engavetar), alertas de falha; recebe links para captura manual | bot próprio (`telegram_bot.py`, long polling) — sem servidor público |
| **Markdown/HTML local** | `data/digests/YYYY-MM-DD.md` + `.html`; relatório semanal em `data/weekly/` (`AAAA-MM-DD-semana`, e `AAAA-MM-DD-ideias-<run>` para o `ideate`) | sempre gerado |
| **E-mail** (opcional, ligado em 2026-11-08) | cópia do digest diário (as duas seções e o radar; os votos continuam no Telegram) | SMTP com STARTTLS em `smtp.gmail.com:587`, reaproveitando `GMAIL_ADDRESS` + a senha de app de `GMAIL_APP_PASSWORD` (a mesma da leitura das newsletters na P2); destinatário em `DIGEST_EMAIL_TO`. HTML só com estilos inline. Uma senha que não tem o formato de senha de app é recusada antes de conectar, para que a senha da conta nunca seja enviada |
| **MCP server** (P3) | `search`, `entity`, `neighbors`, `recent_items`, `graph_stats` e `cypher` (só leitura, no Neo4j); na P4, `trends`, `gaps`, `list_ideas` e `idea` | `sotawhat serve-mcp` (stdio, `MCPServer` do SDK `mcp` 2.x) sobre o SQLite; registrado em `.mcp.json` |
| **Interface web** (P3; antes P6) | grafo navegável das entidades (técnicas, modelos, datasets, organizações, produtos, problemas, regulações e as categorias da taxonomia); filtros por período, tipo e número de menções; busca; painel da entidade (itens, vizinhos, relações) e do item (resumo, por que importa, votos 👍/👎/🧪). Na P4, as abas **Ideias** (cards com rubrica, novidade, prior art, críticas, dossiê, fatos do grafo e votos, inclusive 👎 com motivo e 🛠️ construí) e **Tendências** (em alta, mapa rotulado, lacunas e regras do meta-review) | `sotawhat serve`: FastAPI em `127.0.0.1:8765`, lendo do SQLite; sigma.js 3 + graphology com os arquivos JS no próprio pacote; pode subir ao fazer logon |
| **Export** (sem lock-in) | grafo (nós e arestas) e itens aprovados | `sotawhat graph export`: JSON + CSV em `data/exports/` |

**Regras de cadência e formato (evidência em `plataformas_similares.md`, P8–P9):** nota diária curta (tipicamente ≤ 10 itens: 1 frase + "por que importa para você" + score + link + fonte), seção *Radar* com 1 linha por item; **"nada relevante hoje" → não envia**; síntese semanal mais longa (3–5 itens no estilo Doctor Penguin + tendências + lacunas + ideias) e *catch-up* automático após dias sem leitura; medicina tende a cadência semanal, ML a diária — o digest diário é predominantemente ML∩medicina aplicada e o semanal consolida. Cada item traz score visível e número de fontes independentes.

### 6.12 Agendamento e operação

- `sotawhat run daily` às **07:00** e `sotawhat run weekly` aos domingos às **20:00** via Task Scheduler. `scripts/schedule_daily.ps1` registra as tarefas com *wake to run*. O Docker Desktop é um aplicativo da sessão do usuário e não roda sem logon. Por isso nada no run diário depende do Neo4j: a extração e a resolução gravam no SQLite, e o espelho no Neo4j é sincronizado quando ele responde (no próprio run ou com `sotawhat graph sync`). O ouvinte de votos e a interface web podem rodar como tarefas "ao fazer logon"; o MCP sobe sob demanda, pelo Claude Code.
- `sotawhat graph up` testa `docker info`. Se o Docker Desktop estiver fechado, abre-o (`"$Env:ProgramFiles\Docker\Docker\Docker Desktop.exe"`) e espera até 120 s; depois roda `docker compose up -d neo4j` (idempotente) e espera o Neo4j responder. O run diário só tenta conectar: se o Neo4j não responder, o resumo avisa, e a próxima sincronização aplica o atraso (marca d'água em `items.graph_synced_at`). Pré-requisito: no Docker Desktop, Settings → General → "Start Docker Desktop when you sign in".
- Lock file por run; retries por fonte (3×, backoff exponencial); `source_state.consecutive_failures ≥ 3` gera alerta.
- `sotawhat doctor` verifica:
  - chaves e tokens: OpenRouter (saldo e limite via `GET /api/v1/key`), Telegram (`getMe`), Gmail, Apify, GitHub e HF;
  - modelos configurados: existência no catálogo, `expiration_date` e endpoints ZDR elegíveis; `doctor --llm` faz uma chamada de fumaça com JSON estrito por etapa, a custo de centavos;
  - Docker Desktop e Neo4j, espaço em disco, idade da última execução e custo acumulado no mês.
- Backup: `scripts/backup.ps1` copia `insight.db` e um `neo4j-admin database dump` semanal (`docker compose exec neo4j …`, gravado num diretório montado `./data/backups/`) com rotação de 8 semanas.

### 6.13 Segurança e privacidade

- Segredos somente em `.env` (ignorado pelo git) e em `data/auth/` (tokens OAuth, sessões); `.env.example` documenta cada variável.
- O sistema **não** toca dados de pacientes nem sistemas internos; só fontes públicas e conteúdos que o usuário já recebe.
- Instagram: somente métodos permitidos pelos termos de uso como caminho principal (§7.2); qualquer alternativa não oficial é *opt-in* explícito e com conta secundária.
- Logs sem conteúdo de tokens; `llm_calls` guarda contagens, não textos.
- LLM: todas as chamadas exigem endpoint ZDR (`zdr: true` + imposição na conta do OpenRouter) e `data_collection: "deny"`. A chave do OpenRouter é exclusiva do projeto, tem limite mensal de gasto e pode ser revogada a qualquer momento. As ideias, potencial propriedade intelectual, nunca saem por endpoint sem ZDR, o que exclui a Batch API.
- Neo4j: portas publicadas só em `127.0.0.1`; senha em `.env` (`NEO4J_PASSWORD`), nunca no `compose.yaml`.
- LGPD: dados pessoais no grafo limitam-se a nomes públicos de autores/criadores; há comando `sotawhat forget --entity <nome>`.

---

## 7. Integrações por canal

Detalhes, limites e fontes primárias em `docs/research/2026-11-07-insight-engine/integracoes.md` (verificado em 2026-11-07, com sondagens ao vivo). Abaixo, as decisões.

### 7.1 Gmail (newsletters)

| Opção | Prós | Contras | Decisão |
|---|---|---|---|
| **IMAP + App Password** (`imapclient.gmail_search` → extensão `X-GM-RAW` com a sintaxe de busca do Gmail) | zero projeto no Cloud, 1 segredo, `X-GM-MSGID` = id estável, somente leitura com `readonly=True` | exige verificação em 2 etapas; revogado ao trocar a senha; desaconselhado (não descontinuado) pelo Google | **backend padrão** (`GMAIL_BACKEND=imap`) |
| **Gmail API + OAuth** (app *Desktop*, público *External*, **publicado "In production" sem verificação**) | oficial; labels/ids/history nativos; quota folgada (80 M unidades/dia em projetos novos) | setup no Console; tela "app não verificado"; **em status "Testing" o refresh token morre em 7 dias**; morre também com troca de senha, 6 meses sem uso ou > 100 tokens | backend alternativo (`GMAIL_BACKEND=api`), mesma interface `fetch_messages(query)` |
| Pub/Sub push | tempo real | `watch()` renovado a cada 7 dias, endpoint, sem corpo | não |

- **Organização na caixa:** filtro do Gmail `from:(@alphasignal.ai OR @deeplearning.ai OR <remetente Runway> OR <outras newsletters>)` → pular caixa de entrada, aplicar label `newsletters/ai`, nunca marcar spam. AlphaSignal e The Batch entram primariamente por RSS/arquivo web (§5.2); o e-mail é redundância e cobre as newsletters sem feed. Ingestão com `label:newsletters-ai newer_than:2d` (janela de 2 dias tolera um dia perdido); dedupe por `X-GM-MSGID` + `Message-ID`. Remetentes exatos **não puderam ser confirmados** (AlphaSignal: `alphasignal.ai` e/ou Substack; The Batch: provavelmente `@deeplearning.ai` via HubSpot; "Runway": ambíguo — ver §16) → confirmar no header `From`/`List-Id` do primeiro e-mail e ajustar `config/sources.yaml`.
- **Parsing:** `email` stdlib (`get_body(preferencelist=('html','plain'))`) → `html2text` (`body_width=0`, `ignore_images=True`) → **segmentação por LLM** (modelo de segmentação, padrão `xiaomi/mimo-v2.6-flash`, saída estruturada): cada edição vira N `NewsletterItem` (título, resumo, links, categoria), com `parent_issue_id`. Links de rastreamento (beehiiv `link.mail.beehiiv.com`, Substack `substack.com/redirect`, Mailchimp `list-manage.com/track`, SendGrid `ct.sendgrid.net`, HubSpot `hubspotlinks.com` etc.) são resolvidos com `httpx` (`follow_redirects`, `head` → `get` em 403/405), limpos com `w3lib.url.url_query_cleaner` (`utm_*`, `ref`, `fbclid`, `_hsenc`, `_hsmi`, `_bhlid`, `mc_cid`, `ck_subscriber_id`, …) e cacheados; **nunca** seguir `List-Unsubscribe`, "manage preferences", pixels ou `mailto:`. Quando o link canônico é arXiv/GitHub/HF, o item é **fundido** com o item da fonte primária (`SAME_STORY`) em vez de duplicado; páginas de blog são enriquecidas com `trafilatura` (opcional).
- **Falhas e mitigação:** `invalid_grant` (OAuth) → publicar o app antes de consentir, alerta e reconsentimento local, nunca `run_local_server` em CI; `[AUTHENTICATIONFAILED]` (IMAP) → regenerar App Password; "too many simultaneous connections" → 1 conexão por run; `doctor` testa o login diariamente.

### 7.2 Instagram (páginas seguidas)

**Fato central:** não existe endpoint oficial que devolva o feed das contas que você segue (a Basic Display API foi desligada em 2024-12-04). A única porta oficial para posts de terceiros, a **Business Discovery**, exige que **a conta que faz a chamada seja profissional** (Business/Creator) e que haja um app na Meta. **A conta do usuário é pessoal e ele não quer criar app na Meta (§16.1, item 6), então a API oficial fica fora.** Se um dia a conta for convertida para Creator (gratuito e reversível) ou surgir uma conta profissional secundária, o caminho oficial volta a ser possível sem custo; ver `integracoes.md` §5. Também não há API de "Salvos". A lista de seguidos vem da exportação JSON do Accounts Center ("Baixar suas informações" → "Seguidores e seguindo").

**Estratégia (ordem de preferência):**

| Camada | Para quem | Como | Risco / custo |
|---|---|---|---|
| **T2 · Captura manual "compartilhar para"** (sempre ligada) | qualquer post que o usuário achar relevante, inclusive de contas privadas | no app: Compartilhar → Telegram → chat do bot (ou e-mail para si mesmo com a label do Gmail); regex `instagram\.com/(p|reel|reels)/([A-Za-z0-9_-]+)` → post resolvido por URL via T3 (`directUrls`) | zero risco; 1 toque por post; entra com prioridade alta no digest; *updates* do bot expiram em 24 h → coletor a cada 6–12 h |
| **T3 · Varredura diária por serviço de terceiros** (automática) | contas **públicas** da lista de seguidos já filtrada (`config/instagram_accounts.yaml`) | **Apify `apify/instagram-scraper`** com `directUrls` dos perfis, `resultsType: "posts"`, `onlyPostsNewerThan: "1 day"` e `resultsLimit` baixo; alternativa **HikerAPI** (`x-access-key`, US$ 0,001/req, saldo não expira) | nenhuma conta própria exposta; ≈ US$ 0,4–4/mês para 150–1.500 posts/mês, **dentro do crédito grátis de US$ 5/mês da Apify**; contas privadas ficam de fora (só T2) |
| **T4 · `instagrapi` com conta secundária** (opt-in explícito, **desligado**) | último recurso | conta dedicada só-leitura, sessão persistida, nunca a conta principal, nunca em CI | o próprio README considera a automação "frágil em produção"; viola os Termos; risco de checkpoint/ban da conta usada |
| Não recomendados | — | RSSHub (exige cookie de sessão), RSS-Bridge (sem mantenedor), espelhos Picuki/Imginn (403), instaloader anônimo (429/login wall) | quebram em silêncio |

- **Lista de contas:**
  1. Exportar `following.json`.
  2. O LLM pré-classifica cada conta (bio + 3 últimos posts, via T3) em "IA/ML", "saúde/medtech" ou "fora do escopo".
  3. O usuário confirma no Telegram, e o resultado vai para `config/instagram_accounts.yaml` (até 50 contas no início).
  4. Reexportar a cada 1–3 meses.
- **Extração multimodal:**
  - Legenda + descrição das imagens pelo modelo de visão (padrão `xiaomi/mimo-v2.6-flash`, ZDR).
  - As imagens são baixadas na mesma execução, porque as URLs de CDN expiram. Antes do envio em base64, ficam com ≤ 800 px no lado maior, até 3–4 por carrossel.
  - Reels: `videoUrl` do provedor → `ffmpeg` → transcrição local com `faster-whisper` (`base`/`small` em CPU).
  - Esquema interno único `{shortcode, owner, caption, media[], timestamp, type, provider}`, com dedupe por `shortcode`.
- **Custo estimado:** ≈ US$ 0–4/mês para a varredura (na maioria dos meses dentro do crédito grátis da Apify) + ≈ US$ 0,1–0,7/mês de visão.
- **Setup (uma vez):** criar conta Apify no plano Free → `APIFY_TOKEN` (ou HikerAPI → `HIKERAPI_TOKEN`) e exportar "Seguidores e seguindo" em JSON. A captura manual usa o bot do Telegram (§7.7). Nada a configurar na Meta.
- **Falhas:** fornecedor fora do ar ou mudança no Instagram → camada de adaptação (Apify ↔ HikerAPI) + alerta; perfil que virou privado → sai da varredura e é sinalizado; nunca retentar em loop.

**Como ficou na P5** (`sotawhat/sources/{apify,instagram,inbox}.py`, `sotawhat/pipeline/{media,accounts}.py`; medições no adendo do plano da P5):
- **T2, captura manual.** O ouvinte guarda todo link mandado ao bot (inclusive os embutidos no texto) e confirma no chat. No run diário:
  - posts e reels são resolvidos pelo Apify (`directUrls` do post), de qualquer conta pública;
  - os demais links viram item com o título e a descrição da página. Só http(s), e cada salto de redirecionamento precisa resolver para endereço público;
  - na triagem, esses itens (fonte `manual:telegram`) não passam pelo silêncio nem pelo classificador, vêm primeiro e nunca são rejeitados (no pior caso, radar). Um item que a varredura já tinha guardado vira seu e volta para a triagem.
- **T3, varredura.** O ator `apify/instagram-scraper` é chamado com o token no cabeçalho, `maxTotalChargeUsd` por run (padrão US$ 0,15) e `resultsLimit` por conta.
  - A janela começa numa marca d'água (no máximo 3 dias atrás), e os shortcodes vistos não voltam.
  - Contas "ia" entram no perfil geral e "saude" no médico.
  - Plano Free medido em 2026-11-08: US$ 5/mês e US$ 0,0027 por post.
  - O HikerAPI fica como alternativa ainda não implementada.
- **Curadoria.** `sotawhat instagram import following.json --yes` busca os perfis (Apify `details`) e classifica em lotes de 20 (tarefa `accounts`). O YAML resultante preserva as suas escolhas a cada nova importação.
- **Multimodal.**
  - Imagens só das CDNs do Instagram, até 3 por carrossel, reduzidas a 800 px e enviadas à tarefa `vision` (prompt `vision_v1`, schema `PostVision`).
  - A transcrição dos reels usa `faster-whisper` em CPU e só liga com o extra opcional `[audio]` (dispensa o `ffmpeg`, porque o PyAV decodifica).
  - Estourar o orçamento desliga só a visão pelo resto do run.

### 7.3 GitHub (repositórios novos e em alta)

- **Busca** (`GET /search/repositories`, 30 req/min autenticado, ≤ 1.000 resultados, `per_page=100`): uma query por tópico com `created:>{D-7} stars:>3 sort=stars` (novos) e `pushed:>{D-1} stars:>1000 sort=updated` (ativos), mais queries por termo (`"medical" "LLM" in:name,description created:>{D-7}`). Tópicos: `medical-imaging` (7.085 repos), `healthcare-ai`, `fhir`, `medical-ai`, `ehr`, `medical-image-analysis`, `radiology`, `biomedical`, `pathology`, `clinical-nlp`, `digital-pathology`, `monai`; para agentes/MCP/skills: `mcp-server` (41 k), `model-context-protocol`, `agent-skills` (40 k), `claude-skills`, `claude-code-plugin` — volume de centenas/dia exige piso de estrelas/forks e dedupe contra os registries (§7.4–7.5). Chamadas em série, `ETag`/`If-None-Match` (304 não conta na quota), `X-GitHub-Api-Version: 2026-03-10`, `retry-after` respeitado.
- **"Trending" sem API oficial:** a API do OSS Insight está **inoperante desde 2026-03-01** (`data_quality.status: "unavailable"`); não usar. Substituto: Search API como proxy + **velocidade de estrelas própria** (`star_snapshots`: 1 `GET /repos/{o}/{r}` por repositório observado/candidato por dia) + opcional GH Archive no BigQuery (`WatchEvent`, 1 TB/mês grátis) + diff diário de *awesome lists* (`raw.githubusercontent.com`). Scraping de `github.com/trending` só como último recurso.
- **Releases:** feeds `https://github.com/{owner}/{repo}/releases.atom` (sem auth, sem quota) pelo adapter RSS existente para repositórios-chave (`Project-MONAI/MONAI`, `modelcontextprotocol/*`, `anthropics/skills`, `anthropics/claude-plugins-official`, `huggingface/huggingface_hub`, `getzep/graphiti`, `neo4j/graph-data-science`, …).
- **Token:** fine-grained PAT **sem permissões** (leitura pública já incluída), validade 366 dias com lembrete no `doctor`; em CI, `secrets.GITHUB_TOKEN`.
- **Enriquecimento para a triagem:** README bruto (primeiros ~3 k caracteres), licença, tópicos, estrelas/forks, data de criação, último push.

### 7.4 Registries de servidores MCP

| Fonte | Mecanismo | Estado |
|---|---|---|
| **Registry oficial** `registry.modelcontextprotocol.io` | `GET /v0.1/servers?limit=100&updated_since=<checkpoint>&version=latest` + cursor; `_meta["io.modelcontextprotocol.registry/official"].status ∈ {active, deprecated, deleted}`; `search=` por {fhir, pubmed, clinical, medical, dicom, health, hl7, radiology, pathology, genomic}; checkpoint só após aplicar todas as páginas | público, sem chave; **preview** (pode haver *breaking changes*); servidor 1.8.8 |
| **Docker MCP Catalog** | `https://desktop.docker.com/mcp/catalog/v2/catalog.yaml` (510 KB; `dateAdded`, `toolsUrl`) + `docker/mcp-registry/servers/*/server.yaml` | público |
| **awesome-mcp-servers** (`punkpeye`, 97 k★) | diff diário do README | público |
| Smithery / Glama | APIs com chave (Glama exige atribuição visível — licença de dados) | opcionais |
| PulseMCP | API pública v0beta **descontinuada (HTTP 410)**; v0.1 só parceiros | não usar |
| mcp.so | sem API | não usar |

Servidores de saúde já conhecidos (semente do grafo e lista de `releases.atom`): `wso2/fhir-mcp-server`, `pcmedsinge/mcp-fhir`, `cyanheads/pubmed-mcp-server`, `cyanheads/clinicaltrialsgov-mcp-server`, Medplum (`com.medplum/mcp`, hospedado), AWS HealthLake/HealthImaging/HealthOmics (`awslabs/mcp`), `genomoncology/biomcp` (72 fontes biomédicas), servidores DICOMweb; marketplaces da Anthropic **`anthropics/healthcare`** (prior auth, ICD-10, FHIR, CMS, NPI, ClinicalTrials, PubMed) e **`anthropics/life-sciences`** (diff do `marketplace.json`). Epic e Oracle Health não publicam MCP oficial.

### 7.5 Agent Skills

- Padrão aberto (agentskills.io): `SKILL.md` com `name` (≤ 64, kebab-case = pasta) e `description` (≤ 1.024) obrigatórios. Descoberta diária, por custo/benefício: (1) diff de `.claude-plugin/marketplace.json` de `anthropics/claude-plugins-official`, `anthropics/skills`, `anthropics/healthcare`, `anthropics/life-sciences`; (2) Search API `topic:agent-skills|claude-skills|claude-code-plugin created:>{D-1} stars:>2`; (3) code search `fhir filename:SKILL.md`, `radiology filename:SKILL.md` (10 req/min); (4) diff das *awesome lists* (`ComposioHQ/awesome-claude-skills`, `VoltAgent/awesome-agent-skills`, `hesreallyhim/awesome-claude-code`). A API do skills.sh exige token OIDC da Vercel (401 sem ele) — não usada.
- Para cada candidato: baixar `SKILL.md` via `raw.githubusercontent.com`, validar o frontmatter, triar com `audience=motor` (útil para o próprio pipeline) ou `clínico/gestão`.

### 7.6 Hugging Face Hub

- `huggingface_hub` 2.4 (`httpx2`): `HfApi().list_models(filter=["medical"], sort="trending_score", limit=50)`, `list_models(search="radiology", sort="created_at")`, `list_datasets(filter="medical", sort="last_modified")`, `list_datasets(task_categories="image-segmentation", sort="trending_score")`; REST em camelCase (`sort=trendingScore|lastModified|createdAt`, snake_case → 400); `/api/daily_papers` (já usado) e `/api/trending?type=model`. `HF_TOKEN` (fine-grained, leitura) eleva o limite para 1.000 req/5 min. **Atenção:** esta máquina mostrou `CERTIFICATE_VERIFY_FAILED` intermitente em `huggingface.co` (inspeção TLS por antivírus/proxy) → `pip install truststore` + `truststore.inject_into_ssl()` ou `SSL_CERT_FILE`; nunca `verify=False`.

### 7.7 Telegram (entrega, feedback e captura manual)

- Bot próprio via @BotFather (`TELEGRAM_BOT_TOKEN`); *long polling* `getUpdates` (updates expiram em 24 h → coletor a cada 6–12 h ou bot residente como tarefa "ao iniciar sessão"); `TELEGRAM_ALLOWED_USER_ID` ignora terceiros; teclado inline para 👍/👎/🧪/🗄️; links em `message.entities[type=url]`. `python-telegram-bot` 22.8. Alternativa sem limite de 24 h: canal privado + Telethon (`TELEGRAM_API_ID/HASH`).

### 7.8 Demais fontes

arXiv, Semantic Scholar (chave opcional `SEMANTIC_SCHOLAR_API_KEY` eleva o limite), PubMed (`NCBI_API_KEY` → 10 req/s), HF Daily Papers e RSS continuam como hoje; novos: medRxiv/bioRxiv (API/RSS por categoria), lista FDA de dispositivos com IA (download periódico), OpenAlex (`OPENALEX_EMAIL` para o *polite pool*), feeds de regulação BR (ANVISA, CFM, ANPD, MS/RNDS) — catálogo e tiers em §5.

---

## 8. Motor de ideias

Fundamentação completa (com as citações) em `docs/research/2026-11-07-insight-engine/geracao_ideias.md`. Esta seção traduz a evidência em decisões de projeto.

### 8.1 O que a evidência (2024–2026) diz — e o que isso muda no desenho

| Evidência | Consequência no desenho |
|---|---|
| LLMs geram ideias julgadas *mais novas* que especialistas, mas a vantagem desaparece ou inverte quando as ideias são executadas (Si et al. 2024/2025); novidade julgada por LLM anticorrelaciona com realização futura (HindSight 2026, ρ = −0,29) | "Novidade" é um **filtro fraco**, nunca o critério principal; o peso vai para viabilidade (dados, integração, regulação, tempo até piloto) e para o feedback de execução do usuário |
| Sistemas com validação real (Google Co-Scientist, Virtual Lab, Robin/Kosmos, Hakken) seguem o padrão *gerar muito → criticar com papéis distintos → ranquear por comparação pareada → evoluir → validador externo* | Pipeline em estágios separados; o "validador externo" aqui é o próprio usuário + sinais de mercado (prior art, conversas com stakeholders) |
| Colapso de diversidade é estrutural: ~5% de ideias únicas em 4.000 geradas; grupos com "líder" colapsam; mais agentes/rodadas **reduzem** diversidade por agente (Vendi/N 1,03 → 0,47) | Geração **independente** (técnica de grupo nominal), personas horizontais, sementes por lentes diferentes, nichos explícitos (MAP-Elites), seleção por portfólio; nunca um agente "coordenador" |
| Juízes-LLM de novidade são instáveis (pequenas mudanças de prompt viram > 50% dos vereditos); avaliadores "purpose-built" perdem para prompts simples | ≥ 3 juízes com troca de ordem e limiar de concordância; abstenção quando divergem; prior art reportado como **vizinhos + diferenças por faceta**, não como nota |
| Subgrafos compactos ≈ grafo inteiro; baseline sem grafo recupera muito do conteúdo (Compressive KG); pares escolhidos por grafo não aumentaram o interesse de 100+ líderes de grupo (SciMuse, média 2,4/5) | O grafo vale pela **amostragem** (recência — "why now"), rastreabilidade e controle de diversidade; passar 20–50 triplas por candidato, nunca o grafo inteiro; manter 10% de candidatos "controle sem grafo"; modelo de interesse pessoal treinado com feedback |
| LLMs executam TRIZ/SCAMPER de forma consistente, mas "não discriminam viabilidade técnica" no modo criativo (Chulvi 2025) | Lentes clássicas como **operadores de diversidade**; viabilidade julgada por críticos separados com checklists e ferramentas |
| Few-shot com ideias bem avaliadas melhora a qualidade (Girotra et al.); memória de direções que falharam (EvoScientist) e meta-review que injeta regras nos prompts (Co-Scientist) personalizam sem fine-tuning; reward model treinado em notas humanas supera SOTA em até 27% (Bao et al. 2026) | Ledger com motivo da rejeição; few-shot com curtidas; meta-review semanal; modelo de interesse quando houver ≥ 200–300 avaliações |
| Modelos nunca propõem hipóteses nulas/contrárias espontaneamente (Bao et al. 2026) | Lente "negativa/contrária" obrigatória em todo lote |

### 8.2 Extensão da ontologia para ideação

Além dos nós do §6.5, o motor usa:

| Nó | Papel | Atributos |
|---|---|---|
| `Capability` | o "B" do modelo ABC de Swanson — capacidade intermediária que uma técnica habilita e um problema exige (ex.: *transcrever e estruturar consulta em pt-BR*, *segmentar volume 3D com poucos rótulos*) | `name, embedding, first_seen` |
| `DataSource` | tipo de dado necessário (PEP/EHR, imagem, laudo, sinais vitais, áudio, RNDS) | `availability_rede_dor (desconhecido/parcial/sim), lgpd_sensitivity, structured` |
| `Solution` (= `Product` existente) | produto/startup/paper aplicado já existente — base para ERRC, `COMPETES_WITH` e prior art interno | `vendor, country, business_model, regulatory_status, incumbent` |
| `Regulation` | restrição (classe SaMD RDC 657/2022 e RDC 751/2022, LGPD art. 11, CFM, FDA/CE) | `jurisdiction, class` |

Relações: `Technique-[:ENABLES]->Capability`, `Capability-[:ADDRESSES]->Problem`, `Capability-[:REQUIRES_DATA]->DataSource`, `Solution-[:ADDRESSES]->Problem`, `Solution-[:USES]->Technique`, `Solution-[:COMPETES_WITH]->Solution`, `Solution-[:REGULATED_AS]->Regulation`, `Idea-[:COMBINES]->Technique`, `Idea-[:TARGETS]->Problem`, `Idea-[:NEEDS]->DataSource`, `Idea-[:INSPIRED_BY]->Item|Claim|Community`, `Idea-[:SUPERSEDES]->Idea`. Todas datadas (`valid_from` = data de publicação do item que originou o fato), o que permite avaliar o motor por *time-slicing* (congelar o grafo em T, gerar, medir depois quais ideias viraram produtos/papers).

### 8.3 Pipeline (job semanal `sotawhat run weekly` + sob demanda `sotawhat ideate --tema "UTI" --n 10`)

| # | Estágio | Mecanismo | Modelo |
|---|---|---|---|
| 1 | **Amostragem de candidatos** (pares Técnica × Problema e caminhos) | três amostradores com cotas 40/30/30: (a) predição de links `Technique→Capability→Problem` para pares sem aresta direta, priorizando técnicas surgidas há < 12 meses ("why now"); (b) lacunas estruturais entre comunidades (clusters de técnicas vs. de problemas pouco conectados); (c) caminhos aleatórios entre nós distantes (serendipidade, à la SciAgents). Cada candidato recebe um **subgrafo compacto** (20–50 triplas datadas com caminhos de evidência); 10% dos candidatos são "controle sem grafo" | sem LLM (GDS/NetworkX) |
| 2 | **Geração independente por lentes** | para cada candidato, geradores que **não se veem** (técnica de grupo nominal), cada um com uma lente: *tech-push*; *JTBD/How-Might-We* (3–5 HMW); *SCAMPER* (um operador por chamada); *TRIZ* (contradição explícita + 2 princípios); *ERRC* contra o incumbente; *analogia inter-setorial* (análogo a distância controlada — logística/aviação → bloco cirúrgico); *adjacent possible / cenário 2029 num hospital da Rede D'Or*; e a lente **negativa** ("por que este par NÃO deveria virar produto; que hipótese nula o mercado ignora"). Personas horizontais e específicas (residente de clínica médica, enfermeira de UTI, gestor de leitos, engenheiro de dados do hospital, fundador de healthtech que já falhou) — sem persona "chefe". *Chain-of-thought*, few-shot com 3–6 ideias **curtidas** no ledger, lista de rejeitadas a evitar | rotação de famílias por lente: `deepseek/deepseek-v4.1-flash-1017` · `xiaomi/mimo-v2.6-pro` · `z-ai/glm-5.3` (+ `moonshotai/kimi-k3.1-pro` no modo completo); raciocínio alto; síncrono, ZDR |
| 3 | **Dedup e diversidade de portfólio** | dedup 1: embedding (cosseno ≥ 0,80); dedup 2: facetas (mesmo problema + mesma técnica + mesmo modelo de negócio); nichos MAP-Elites `setor × família de técnica × forma/modelo de negócio`, ≤ 2 ideias por célula no lote final; exclusão de ideias com similaridade ≥ 0,85 a rejeitadas **com o mesmo motivo** (re-proposta permitida se o motivo era "imaturo/sem dado" e o grafo mudou); métrica de diversidade do lote (Vendi score) com alarme | embeddings locais + `xiaomi/mimo-v2.6-flash` para facetas |
| 4 | **Dossiê** (só sobreviventes) | Lean Canvas resumido; MVP/piloto de 90 dias em uma unidade; plano de evidência (retrospectivo → prospectivo → RCT se SaMD classe III/IV); classe SaMD estimada (IMDRF: significância × situação de saúde); base legal LGPD (art. 11, II, *f* para assistência; art. 7º, IV e art. 13 para pesquisa; atenção ao § 4º do art. 11); integração (FHIR, PEP vigente, RNDS); dependências de dados reais. Toda afirmação factual aponta para triplas/itens | `deepseek/deepseek-v4.1-flash-1017` (raciocínio máximo) |
| 5 | **Crítica multi-papel com kill criteria** (gerador ≠ crítico) | críticos com checklists objetivos e acesso ao grafo: *Clínico* (segurança, workflow, aceitação), *Operações/CFO* (quem paga, ROI, custo de implantação), *Regulatório/LGPD*, *Dados/Integração* (o dado existe? qualidade? FHIR? latência?), *Cientista de ML* (a técnica entrega a capacidade? generalização?), *Paciente/Ética*. Cada crítico devolve `veredito`, `kill_criteria_acionados`, `o_que_mudaria_o_veredito`. Máximo 2 rodadas gerador↔crítico; "pré-mortem" ("esta ideia fracassou na Rede D'Or em 2028 — por quê?"); *gate* NASSS (≥ 3 domínios "complexos" → rebaixar) | `deepseek/deepseek-v4.1-flash-1017` (máximo) → `z-ai/glm-5.3`; crítico sempre de família diferente do gerador da ideia |
| 6 | **Prior art por facetas, 4 camadas** | (1) grafo interno (soluções/itens já ingeridos); (2) literatura — Semantic Scholar (busca + SPECTER2 + recomendações) e OpenAlex; (3) patentes — Lens.org ou EPO OPS (4 GB/semana grátis; famílias BR via Espacenet/DOCDB, pois o INPI não tem API confiável); (4) mercado/código — GitHub, Exa `findSimilar`, Product Hunt/Crunchbase conforme licença. Saída: 5–10 vizinhos por camada + **matriz de diferenças por faceta** (problema, técnica, dado, integração, modelo de negócio, geografia/BR); ≥ 3 juízes com ordem trocada classificam cada faceta em {igual, parcial, não encontrado} com confiança; divergência → "a verificar pelo humano" | APIs + `xiaomi/mimo-v2.6-flash` (consultas) + 3 juízes de famílias diferentes (§6.6) |
| 7 | **Ranking pareado e rubrica** | torneio suíço (5 rodadas) por eixo com 3 juízes e troca de posição; agregação só com ≥ 2 concordando; eixos 1–10 combinados pela rubrica (§8.4); gates duros antes da rubrica; seleção final por **portfólio** (maximizar score sujeito a cotas de nicho e penalidade de similaridade): 5–10 ideias/semana, ≤ 2 por célula, ≥ 1 aposta contrária | 3 juízes de famílias diferentes: `moonshotai/kimi-k3.1-pro` (econômico: `xiaomi/mimo-v2.6-pro`) + `z-ai/glm-5.3` + `deepseek/deepseek-v4.1-flash-1017` |
| 8 | **Ledger, feedback e personalização** | ações: gostei / não gostei (motivo: não interessa, já existe, inviável agora, errado clinicamente, fora do foco) / testar / engavetar / construí; edição gera nova versão (`parent_id`). Uso imediato: few-shot de curtidas, memória de rejeições por motivo, **meta-review semanal** que resume padrões das decisões e críticas em ≤ 10 regras injetadas nos prompts ("rejeita tudo que depende de wearable próprio"; "prefere operações de UTI"). Com ≥ 200–300 avaliações: modelo de interesse (features do grafo + embeddings + lente) para re-ranquear; controladores "mais novidade ↔ mais viabilidade". Resultados de conversas/pilotos entram como evidência no grafo e como rótulo de realização | `deepseek/deepseek-v4.1-flash-1017` (meta-review, raciocínio alto) |
| 9 | **Evolução e entrega** | mensalmente, as 20% melhores passam por combinação/mutação (trocar modelo de negócio, unidade-alvo, técnica) em ilhas por nicho, com crítica e prior art repetidos; relatório semanal = dossiês + "delta do grafo que habilitou cada ideia" + lista explícita do que foi descartado e por quê | rotação de famílias (como no estágio 2) |

**Como ficou na P4** (`sotawhat/ideation/`; medições em §8.6):
- **Dedup (estágio 3).** Com o EmbeddingGemma, o cosseno não separa ideias do mesmo domínio: a mediana entre ideias diferentes do primeiro lote real foi 0,81, e um par claramente distinto chegou a 0,908. Por isso:
  - o "dedup 2: facetas" virou um juiz barato por par técnica × problema, que decide quais rascunhos são o mesmo produto (mesmo usuário, tarefa e mecanismo) e quais repetem uma ideia anterior do par no ledger (finalista, votada ou rejeitada);
  - o embedding só pega textos quase idênticos (≥ 0,95);
  - os pares usados nas últimas 4 semanas só completam o lote depois dos pares novos.
- **Gates (estágio 7).** Seguindo a regra "agregação só com ≥ 2 concordando", um gate descarta a ideia só quando todos os juízes o apontam. O gate de um juiz só fica "em disputa", com −0,1 na confiança, e aparece no card para você decidir.
- **Prior art (estágio 6):** o grafo interno, OpenAlex, Semantic Scholar (sem chave, tolerando 429), GitHub (por relevância no nome e na descrição) e Exa (com `EXA_API_KEY`). Patentes ficam "não verificado".
- **Ficaram para depois:** o torneio suíço, a evolução mensal (estágio 9), a métrica de Vendi e o modelo de interesse (com ≥ 200 avaliações).

### 8.4 Rubrica de pontuação (pesos iniciais — recalibrar após ~100 decisões no ledger)

| Eixo | Peso | Âncoras |
|---|---|---|
| Valor clínico-operacional (JTBD) | 20% | tamanho e frequência da dor; impacto em desfecho/custo/tempo; dono claro no hospital |
| Viabilidade técnica e de dados | 15% | maturidade da técnica (TRL), dado existe e é acessível, qualidade/rotulagem, integração FHIR/PEP |
| Viabilidade de negócio | 15% | pagador identificado (hospital B2B / operadora / B2B2C / SaaS / dispositivo), ROI, vantagem injusta (acesso Rede D'Or, especialidade) |
| Novidade por facetas | 15% | facetas "não encontradas" com concordância de juízes |
| Carga regulatória e privacidade | 10% | classe SaMD (I/II *in-house* isento vs. III/IV), base legal LGPD, risco do § 4º art. 11 |
| Evidência exigida e tempo até piloto | 10% | meses até piloto em 1 unidade; tipo de estudo necessário |
| Fit pessoal/estratégico | 10% | alinhamento com perfil, rede e teses do usuário (ledger) |
| Complexidade de adoção (NASSS) | 5% | nº de domínios complexos; mudança de comportamento exigida |
| Confiança (multiplicador 0,5–1,0) | — | força da evidência nas triplas; concordância entre críticos |

**Gates duros:** sem base legal LGPD; dado inexistente e inobtenível; SaMD classe IV sem plano; viola CFM/ANVISA; duplica incumbente consolidado sem diferenciação.

### 8.5 *Idea card* (saída estruturada, schema Pydantic resumido)

```
IdeaCard: id, version, parent_id, titulo, problema_jtbd, stakeholder_dono, setor,
  tecnica[], capacidade_intermediaria, dado_necessario[], mecanismo, forma (produto|plataforma|dispositivo|servico_corporativo),
  integracao (FHIR|PEP|RNDS|standalone), modelo_negocio, evidencia_paths[] (ids de triplas/itens), lente, persona,
  why_now, o_que_e_novo_por_faceta{}, riscos[], prior_art{camada: [vizinhos], matriz_facetas},
  criticas[{papel, veredito, kill_criteria[], o_que_mudaria}], scores{eixo: nota}, confianca, score_final,
  dossie (lean_canvas, piloto_90d, plano_evidencia, classe_samd, base_legal_lgpd, integracao_detalhe),
  status (nova|curtida|rejeitada|testar|engavetada|construida), feedback[], created_at, run_id
```

### 8.6 Custos e modos de operação

Todos os custos com os modelos chineses via OpenRouter, endpoints ZDR e tokens de raciocínio contados como saída (§13, `llm_openrouter.md`):

- **Modo econômico** (padrão nas 4 primeiras semanas): 30 candidatos × 6 lentes, dossiês e críticas nos 20 melhores, 10 finalistas com 3 juízes (DeepSeek V4.1 Flash, GLM-5.3, MiMo-V2.6-Pro). Volume: ≈ 2,2 M tokens de entrada + 0,8 M de saída por semana → **≈ US$ 0,8/semana (≈ US$ 3/mês)**. Com modelos Anthropic, o mesmo modo custava ≈ US$ 20/mês.
- **Como ficou na P4 (medido em 2026-11-08).** O modo econômico implementado é mais enxuto que o acima, porque o limite da chave do OpenRouter (US$ 5) não renova.
  - **Configuração:** 12 candidatos × 3 lentes (em rotação pelas 6), mais a contrária em 25% do lote; dedup com um juiz por par técnica × problema; crítica, prior art e 2 juízes nos 10 melhores; 6 finalistas.
  - **Primeiro run real** (`ideate --n 4`): 13 rascunhos e 34 chamadas, US$ 0,038, 12 min. O MiMo-V2.6-Pro custa por chamada o dobro do DeepSeek V4.1 Flash, e o GLM-5.3-Flash é o mais barato.
  - **Segundo run real**, já com o dedup por par e os gates por concordância: 13 rascunhos, 12 mantidos, 6 criticados e 4 finalistas, US$ 0,062, 21 min.
  - **Projeção do `run weekly`:** ≈ US$ 0,13 por semana (≈ US$ 0,55/mês) e ≈ 30 min.
- **Modo completo:** ~60 candidatos × 8 lentes em rotação de 3–4 famílias, dossiês e críticas em ~40 sobreviventes, prior art e torneio entre ~20 finalistas com 3 juízes (Kimi K3.1 Pro, GLM-5.3, DeepSeek V4.1 Flash). Volume: ≈ 5 M de entrada + 2,2 M de saída por semana → **≈ US$ 4–7/semana (≈ US$ 18–31/mês)**, conforme o Kimi entre ou não como juiz. Antes: ≈ US$ 90/mês.
- **Como decidir:** depois das 4 semanas iniciais, rodar 2 semanas no modo completo e comparar no ledger a taxa de ideias marcadas "vale explorar". Ficar no completo só se a taxa subir de forma clara.
- Sob demanda (`ideate --tema`), o usuário escolhe o modo. O teto `SOTAWHAT_LLM_BUDGET_USD_RUN_WEEKLY` (§13) interrompe a execução graciosamente.

### 8.7 Código reutilizável (referência, não esqueleto)

`NoviScl/AI-Researcher` (MIT: recuperação → geração semeada → dedup → ranking pareado → filtro de novidade; custos conhecidos), `lamm-mit/SciAgentsDiscovery` (Apache-2.0: amostragem de caminhos no grafo + schema JSON de hipótese), `openevolve` (Apache-2.0: MAP-Elites/ilhas para a fase de evolução), `mikecreighton/ai-brainstorm` (MIT: MCTS de ideias). Evitar como base: `AI-Scientist-v2` (licença RAIL, GPU), `Future-House/robin` (API paga), `HKUDS/AI-Researcher` (sem licença clara).

### 8.8 Armadilhas explicitamente evitadas

1. Nota de novidade como sinal principal. 2. Juiz único / Elo auto-avaliado. 3. Mais agentes ou rodadas "para ter diversidade". 4. Grafo inteiro no prompt, sem controle sem-grafo. 5. Mesmo prompt gerando e julgando viabilidade. 6. Revisões de literatura de agentes sem verificação externa. 7. Re-propor rejeitadas / homogeneizar o portfólio. 8. Esquecer a hipótese nula. 9. Ignorar SaMD/LGPD/INPI cedo. 10. Reusar "AI scientists" completos. 11. Não fechar o ciclo com execução (o que foi tentado/pilotado).

---

## 9. Sem Obsidian (decisão de 2026-11-08)

O usuário pediu "uma interface com um grafo construído por nós" e nenhum uso do Obsidian. Consequências:

1. Nada lê nem escreve no vault (`D:\Lucas\obsidian_vaults\ml_ai_med_vault`), que fica intacto como arquivo pessoal do usuário. Em 2026-11-08 a tarefa agendada foi registrada de novo, sem `--vault`, antes de qualquer escrita.
2. Saem do código os comandos `digest` e `backfill-links`, a opção `--vault` de `run daily` e de `eval golden draft`, os módulos `obsidian.py` e `backfill.py` e o script `schedule_digest.ps1` (P3, tarefa 1).
3. As 2.893 notas antigas não são migradas (escolha "Ignorar o vault"). O grafo começa com os itens que o próprio sotawhat coletou desde a P0 e cresce a cada run. O golden set v1, que já usou uma amostra dessas notas, continua valendo como dado de avaliação.
4. A interface é a página web da P3 (§6.11). A cópia de segurança sem lock-in é o export JSON/CSV mais os dumps (G7, D12).

---

## 10. Requisitos de configuração (.env e pré-requisitos)

O arquivo `.env.example` na raiz do repositório lista todas as variáveis com comentários; copie para `.env` (ignorado pelo git) e preencha. Tudo que é segredo fica em `.env` ou em `data/auth/` (tokens OAuth, sessões); listas e parâmetros editáveis ficam em `config/*.yaml` (versionados).

### 10.1 Pré-requisitos a executar uma vez (checklist)

| # | Item | Onde | Observação |
|---|---|---|---|
| 1 | Conta no OpenRouter, créditos e chave dedicada | openrouter.ai → **Credits**: comprar US$ 10–20 (o checkout mostra a taxa). → **Keys**: criar a chave "sotawhat" com **limite mensal** (ex.: US$ 30) → `OPENROUTER_API_KEY`. → **Settings → Privacy**: ligar ZDR em "All other models" e manter desligados o *logging* e o "uso de entradas/saídas" | o código também envia `zdr: true`; os tetos internos ficam em `SOTAWHAT_LLM_BUDGET_USD_*` (§13) |
| 2 | Python 3.12 + `uv` (já instalados) e `ffmpeg` (reels) | `winget install ffmpeg` | `faster-whisper` baixa o modelo no 1º uso |
| 3 | Docker Desktop + Neo4j Community 2026.10 | No Docker Desktop (já instalado): Settings → General → "Start Docker Desktop when you sign in". Opcional: `%UserProfile%\.wslconfig` com `[wsl2]` `memory=6GB`. A partir da P3: `sotawhat graph up` na raiz do repositório | APOC + GDS só na P4; `NEO4J_PASSWORD` no `.env`; portas só em 127.0.0.1 |
| 4 | Gmail: verificação em 2 etapas + App Password | `myaccount.google.com/apppasswords` | ou projeto no Google Cloud (Gmail API, app *Desktop*, publicado "In production") |
| 5 | Filtro/label `newsletters/ai` no Gmail | Gmail → Configurações → Filtros | remetentes confirmados pelo header do 1º e-mail |
| 6 | Instagram: nada a configurar na Meta (conta pessoal, §7.2) | — | captura manual pelo bot do Telegram + varredura via Apify |
| 7 | Exportação da lista de seguidos (`following.json`) | Accounts Center → Exportar suas informações (JSON) | mensal; semente de `config/instagram_accounts.yaml` |
| 8 | Conta Apify (plano Free) **ou** HikerAPI | apify.com → Settings → API & Integrations → `APIFY_TOKEN` (ou hikerapi.com → `HIKERAPI_TOKEN`) | Apify: crédito grátis de US$ 5/mês ≈ 1.800 posts; HikerAPI: pré-pago, saldo não expira |
| 9 | Bot do Telegram | @BotFather → `/newbot` | enviar `/start` e capturar `chat.id`/`from.id` |
| 10 | GitHub fine-grained PAT (sem permissões, 366 dias) | Settings → Developer settings → Fine-grained tokens | `gh` já autenticado localmente |
| 11 | Token Hugging Face (leitura) | huggingface.co/settings/tokens | resolver a inspeção TLS local (§7.6) |
| 12 | Chaves opcionais: Semantic Scholar, NCBI, OpenAlex (e-mail), Voyage AI, Exa, Lens.org/EPO OPS, Smithery/Glama, GCP (BigQuery) | respectivos portais | só quando a fase correspondente for ativada |
| 13 | Tarefas agendadas (`scripts/schedule_daily.ps1`) | Task Scheduler | *wake to run*, "executar mesmo sem login"; o `doctor` verifica se existem |

### 10.2 Variáveis de ambiente (resumo; detalhes em `.env.example`)

| Grupo | Variáveis | Expiração / rotação |
|---|---|---|
| Núcleo e LLM | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_ZDR` (`true`), `OPENROUTER_DATA_COLLECTION` (`deny`), `OPENROUTER_QUANTIZATIONS`, `SOTAWHAT_DATA_DIR`, `SOTAWHAT_TZ`, `SOTAWHAT_LOG_LEVEL`, `SOTAWHAT_LLM_BUDGET_USD_DAY`, `SOTAWHAT_LLM_BUDGET_USD_RUN_WEEKLY`, `SOTAWHAT_LLM_BUDGET_USD_MONTH`, `SOTAWHAT_MODEL_TRIAGE`, `SOTAWHAT_MODEL_SEGMENT`, `SOTAWHAT_MODEL_VISION`, `SOTAWHAT_MODEL_EXTRACT`, `SOTAWHAT_MODEL_SYNTH`; opcional `ANTHROPIC_API_KEY` (rodada *premium*, desligada) | chave do OpenRouter: limite mensal na própria chave; rotacionar se vazar |
| Grafo, interface e vetores | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` (vazio = espelho desligado; a interface funciona igual), `NEO4J_DATABASE`, `NEO4J_HEAP_MAX`, `NEO4J_PAGECACHE`, `SOTAWHAT_WEB_PORT` (8765), `EMBEDDINGS_BACKEND` (`fastembed`∣`voyage`), `VOYAGE_API_KEY` (opcional) | — |
| Gmail | `GMAIL_BACKEND` (`imap`∣`api`), `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` · ou `GOOGLE_CLIENT_SECRET_FILE`, `GMAIL_TOKEN_FILE` (ou `GOOGLE_OAUTH_CLIENT_ID/SECRET` + `GMAIL_REFRESH_TOKEN` em CI); `GMAIL_LABEL`, `GMAIL_QUERY` | App Password: revogada ao trocar a senha; refresh token: 7 dias se app em "Testing", senão até troca de senha / 6 meses sem uso / > 100 tokens |
| Instagram | `APIFY_TOKEN` (padrão) ∣ `HIKERAPI_TOKEN` (∣ `SCRAPECREATORS_API_KEY`, `BRIGHTDATA_API_TOKEN`); T4: `IG_UNOFFICIAL_ENABLED=false`, `IG_USERNAME`, `IG_PASSWORD`, `IG_SESSION_FILE`, `IG_TOTP_SECRET`, `IG_PROXY_URL`. API oficial **não usada** (conta pessoal): `IG_*`/`FB_*` ficam comentadas no `.env.example` para o caso de conversão futura | crédito da Apify renova todo mês; saldo HikerAPI não expira; sessão T4 até `LoginRequired` |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID`, `TELEGRAM_CHAT_ID`; opcional `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` | sem expiração; `/revoke` no BotFather |
| GitHub | `GITHUB_TOKEN` (`gh` também lê `GH_TOKEN`); opcional `GOOGLE_APPLICATION_CREDENTIALS`, `BIGQUERY_PROJECT` | PAT 1–366 dias (lembrete no `doctor`) |
| Hugging Face | `HF_TOKEN`, `HF_HUB_DISABLE_TELEMETRY=1`, opcional `SSL_CERT_FILE` | sem expiração |
| Acadêmicas / regulatórias | `SEMANTIC_SCHOLAR_API_KEY` (opcional; sem ela o Semantic Scholar devolve 429 com frequência), `NCBI_API_KEY` (opcional), `OPENALEX_EMAIL`, `CROSSREF_MAILTO` (polite pool; periódicos Nature/NEJM AI desde a P0), `PUBMED_EMAIL` | sem expiração |
| Prior art (ideação) | `EXA_API_KEY` (opcional), `LENS_API_TOKEN` (opcional), `EPO_OPS_KEY`/`EPO_OPS_SECRET` (opcional, 4 GB/semana grátis) | — |
| Registries MCP (opcionais) | `MCP_REGISTRY_BASE_URL`, `DOCKER_MCP_CATALOG_URL`, `SMITHERY_API_KEY`, `GLAMA_API_KEY` | registry oficial e catálogo Docker não precisam de chave |
| E-mail de saída (opcional) | `DIGEST_EMAIL_TO`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` (ou escopo `gmail.send` no OAuth) | — |

Mínimo por fase:
- P0: `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.
- P2: `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD`, `GITHUB_TOKEN`, `HF_TOKEN`.
- P3: `NEO4J_PASSWORD`, gerada localmente e usada só pelo Neo4j em 127.0.0.1.
- P5: `APIFY_TOKEN`. O registry MCP, o catálogo Docker, feeds Atom do GitHub, arXiv, PubMed e RSS funcionam sem credenciais.

---

## 11. Plano de implementação por fases

| Fase | Entregas | Critério de aceite | Esforço (estimado) |
|---|---|---|---|
| **P0 · Fundação** (semana 1) | `config.py`, SQLite + schema, `Item` + ids canônicos, **gateway LLM OpenRouter** (JSON estrito, ZDR, fallbacks, custo real em `llm_calls`, tetos de orçamento), adapters atuais ligados ao novo `collect`, **correção dos feeds da Nature** (detecção de HTML + fonte Crossref por ISSN) e remoção dos feeds mortos (§5.1), `run daily` mínimo (coleta + normalização + dedup exato) agendado, `doctor` (com teste de fumaça dos modelos), Telegram de alerta. Plano: `docs/superpowers/plans/2026-11-07-insight-engine-p0-foundation.md` | run diário completa e manda resumo no Telegram; testes antigos continuam verdes; nenhum feed devolve HTML em silêncio; `doctor --llm` valida JSON estrito nos modelos padrão | 3–4 dias |
| **P1 · Triagem + digest** (semana 2) | *mute filters*, rubrica, prompt v1, saída estruturada, dedup semântico (embeddings locais), classificador por perfil (treina quando houver ≥ 100 avaliações), digest MD/HTML/Telegram com botões de feedback, golden set inicial (50 itens), **bake-off de modelos** (`sotawhat eval models`) e `config/llm.yaml`. Plano: `docs/superpowers/plans/2026-11-08-insight-engine-p1-triage-digest.md` | digest diário com ≤ 15 itens; feedback persistido; modelo de triagem escolhido por dados | 3–4 dias |
| **P2 · Novas fontes I** (executada depois da P3; plano `docs/superpowers/plans/2026-11-08-insight-engine-p2-new-sources.md`) | Tier 1 do §5 (Crossref/PubMed `[jour]`, ScienceDirect, JAMA AI, medRxiv API, FDA CSV, Google News), AlphaSignal RSS, The Batch via sitemap, Gmail (newsletters → itens), GitHub (busca + estrelas + releases), HF Hub, MCP registry, skills | cada fonte com fixture + teste; itens aparecem no digest com proveniência | 4–5 dias |
| **P3 · Grafo + interface** (executada antes da P2, decisão de 2026-11-08) | remoção do Obsidian; extração v1 (entidades, relações e números) dos itens aprovados; resolução de entidades com aliases e juiz LLM; categorias da taxonomia como nós; **interface web própria** (FastAPI + sigma.js, lendo do SQLite); espelho no Neo4j (`compose.yaml`, `sotawhat graph up` e `sync`); MCP server; export JSON/CSV; extração e espelho no run diário. Plano: `docs/superpowers/plans/2026-11-08-insight-engine-p3-graph-interface.md` | grafo navegável em `localhost:8765` com os itens já aprovados; consultas pelo MCP no Claude Code; Neo4j espelhado; nada do Obsidian no código | 4–6 dias |
| **P4 · Inteligência + ideação** (executada em 2026-11-08; plano `docs/superpowers/plans/2026-11-08-insight-engine-p4-intelligence-ideation.md`) | comunidades/tendências/lacunas, mapa semanal, pipeline de ideação (§8), ledger, novidade, relatório semanal, feedback de ideias | 1º relatório semanal com 5–10 idea cards e verificação de novidade | 6–8 dias |
| **P5 · Instagram** (executada em 2026-11-08; plano `docs/superpowers/plans/2026-11-08-insight-engine-p5-instagram.md`) | adapter conforme §7.2 (varredura de contas públicas via Apify/HikerAPI + captura manual pelo Telegram + curadoria da lista de seguidos), extração multimodal | posts das contas configuradas no digest; custo dentro do teto | 3–5 dias |
| **P6 · Endurecimento** (executada em 2026-11-08; plano `docs/superpowers/plans/2026-11-08-insight-engine-p6-hardening.md`) | evals de extração/ideação, backup, documentação, calibração de pesos com 4 semanas de feedback, melhorias da interface (a primeira versão veio na P3) | métricas G2–G4 medidas e reportadas | 3–4 dias |

Cada fase vira um *plan* no padrão `docs/superpowers/plans/` (TDD, tarefas pequenas), como nas entregas anteriores do repositório. Ordem de execução desde 2026-11-08: P0 → P1 → P3 → P2 → P4 → P5 → P6.

---

## 12. Testes e avaliação

| Nível | O quê | Como |
|---|---|---|
| Unitário | adapters (fixtures gravadas), normalização, dedup, store, export | `pytest`, sem rede |
| Contrato LLM | montagem da requisição ao OpenRouter (`json_schema` estrito, `provider` com ZDR, `models`, plugins, raciocínio), leitura de `usage.cost`, retries e fallbacks, validação Pydantic e reparo | `httpx.MockTransport` + respostas gravadas (`tests/fixtures/openrouter/`), sem rede |
| Eval · triagem | precision/recall vs golden set (≥ 150 itens rotulados; cresce com feedback) | `sotawhat eval triage` imprime matriz de confusão e custo |
| Eval · extração | precisão de entidades/relações em 40 itens anotados manualmente | `sotawhat eval extract` |
| Eval · modelos (*bake-off*) | os mesmos golden sets em 3–4 modelos por etapa; acurácia, % de JSON válido, qualidade do pt-BR (amostra julgada pelo usuário), latência, custo real | `sotawhat eval models --task triage` (P1; depois mensal ou quando o `doctor` acusar modelo expirando) |
| Eval · ideação | notas humanas (novidade, utilidade, viabilidade 1–5) por ideia; taxa "vale explorar" | ledger + relatório mensal |
| Integração | run diário em modo `--dry-run` com fontes reais (opcional, marcado `network`) | manual/semanal |
| Operação | `doctor`, resumo de execução, alerta de falha, custo por etapa | automático |

**Como ficou na P6** (medido com os dados reais em 2026-11-08; detalhes no adendo do plano da P6):
- **Metas.** `sotawhat eval report [--send]` mede G1–G4 a partir do banco, sem LLM, e mostra cada taxa com a contagem por trás ("poucos dados" abaixo de um mínimo). O `run weekly` grava o relatório toda semana e manda a tabela no primeiro domingo do mês.
- **Primeira medição:**
  - G1: 100% de 3 runs diários;
  - G2: digest no teto (10 + 5 e 4 no radar) e precisão de 100% em 19 votos;
  - G3: consultas do grafo em 21 ms (grafo de 30 dias) e 3 ms (busca); a precisão da extração ainda depende da anotação;
  - G4: nenhuma ideia decidida ainda.
- **Triagem por votos:** `sotawhat eval triage` usa o último voto de cada item contra a decisão. O golden set e o bake-off continuam em `sotawhat eval golden` e `sotawhat eval models`.
- **Extração:** `sotawhat eval extract draft` gera uma amostra de 40 itens em Markdown, você desmarca o que está errado, e `sotawhat eval extract import` calcula a precisão por tipo.
- **Ideias:** `sotawhat eval ideas` mostra a taxa "vale explorar" (👍, 🧪 ou 🛠️ sobre as decididas) por lente, amostrador e família do gerador.
- **Calibração:** `sotawhat calibrate [--apply]` só propõe; grava em `config/` apenas com `--apply`. Precisa de 100 votos para os cortes da triagem, que só podem subir, porque só itens entregues recebem voto; para baixar um corte use o golden set. Os pesos da rubrica de ideias precisam de 30 finalistas decididas.
- **Backup:** `sotawhat backup` toda semana no `run weekly`, guardando as 8 cópias mais novas; `--restore` para restaurar. O espelho Neo4j se reconstrói do SQLite (`graph sync --rebuild`), e o export JSON/CSV continua (G7).
- **Reparo:** `sotawhat repair cjk` corrigiu 17 resumos com tokens chineses que vinham do run da manhã de 2026-11-08 (MiniMax, antes do validador), sem mudar nenhuma decisão.

---

## 13. Custos (estimativa)

Preços de 2026-11-07, em US$ por milhão de tokens (entrada/saída), nos **endpoints ZDR elegíveis** (quantização ≥ fp8 e saída estruturada):

| Modelo | Entrada/saída |
|---|---|
| DeepSeek V4.1 Flash 1017 | ≈ 0,08–0,10 / 0,24–0,30 |
| MiMo-V2.6-Flash | 0,14 / 0,28 |
| MiMo-V2.6-Pro | 0,387 / 0,783 |
| GLM-5.3 | ≈ 0,5 / 2,5 |
| Kimi K3.1 Pro | 2 / 10 |
| *Referência Anthropic:* Haiku 5.5 · Sonnet 5.5 · Opus 5.5 | 0,10 / 0,50 · 2 / 10 · 4 / 20 |

Tokens de raciocínio contam como saída; nas etapas com raciocínio alto, a estimativa dobra a saída. Volumes assumidos por dia: ~300 itens coletados após dedup, ~25 aprovados, 5 edições de newsletter e 5–50 posts de Instagram. Fontes e endpoints em `docs/research/2026-11-07-insight-engine/llm_openrouter.md`.

| Componente | Cálculo | Por dia | Por mês |
|---|---|---|---|
| Coleta, embeddings locais, dedup, classificador | sem LLM | 0 | 0 |
| Segmentação de newsletters (MiMo-V2.6-Flash) | 5 × (6 k entrada + 1,5 k saída) | < US$ 0,01 | US$ 0,2 |
| Triagem (DeepSeek V4.1 Flash, raciocínio baixo, rubrica em cache) | 300 × (2,5 k + 0,8 k) | US$ 0,08–0,15 | US$ 2,5–4,5 (≈ US$ 1 quando o classificador virar porta, com 80 itens/dia) |
| Extração de entidades (DeepSeek V4.1 Flash, raciocínio alto) | 25 × (4 k + 3 k) | US$ 0,03 | US$ 1 (com MiMo-V2.6-Pro: US$ 3) |
| Juiz de resolução de entidades | ~10 pares/dia | < US$ 0,01 | < US$ 0,1 |
| Resumo e ordenação do digest | 1 × (20 k + 4 k) | < US$ 0,01 | US$ 0,1 |
| Visão em posts do Instagram (MiMo-V2.6-Flash) | 5–50 × ~2,5 k | ≤ US$ 0,02 | ≤ US$ 0,7 |
| **Subtotal diário** | | | **≈ US$ 4–7** (≈ US$ 3 depois do classificador). Antes: US$ 18 com Sonnet, US$ 26 com Opus |
| Mapa semanal + meta-review | 10 comunidades × (6 k + 1,8 k) + 1 | — | < US$ 0,1 (antes: US$ 4) |
| Ideação — modo econômico | §8.6: ≈ 2,2 M entrada + 0,8 M saída por semana | — | ≈ US$ 3 (antes: US$ 20) |
| Ideação — modo completo | §8.6: ≈ 5 M entrada + 2,2 M saída por semana | — | ≈ US$ 18–31 (antes: US$ 90) |
| Instagram T3 (Apify/HikerAPI) | até 50 contas/dia | — | US$ 0 dentro do crédito grátis da Apify (≈ 1.800 posts/mês); acima disso, Starter US$ 19 ou HikerAPI ≈ US$ 1,5 |
| Taxa de compra de créditos do OpenRouter | ≈ 5–6% sobre os créditos [confirmar no checkout] | — | ≈ US$ 0,5 |
| Neo4j, Telegram, GitHub, HF, registry MCP, embeddings locais | — | — | 0 |
| Opcionais: Voyage, Exa, Lens/EPO OPS, BigQuery; rodada *premium* com Claude (desligada) | — | — | 0 (rodada *premium*: ≈ US$ 4–8) |
| **Configuração recomendada inicial** (diário + mapa semanal + ideação econômica + IG) | | | **≈ US$ 8–11/mês** (antes: ≈ US$ 45–50, uma redução de ~80%) |
| Configuração com ideação completa | | | ≈ US$ 25–40/mês |
| Extração dos itens já aprovados (uma vez, P3) | ~65 itens (DeepSeek V4.1 Flash, síncrono, ZDR) | — | < US$ 0,10 (a migração do vault saiu do escopo, §9) |

**Controle de gasto (três camadas):**
1. **Corte duro fora do código:** limite mensal na própria chave do OpenRouter (ex.: US$ 30; US$ 50 no modo completo).
2. **Tetos internos:**
   - `SOTAWHAT_LLM_BUDGET_USD_DAY` (padrão 1,00) vale para o `run daily`, cujo custo esperado fica em US$ 0,15–0,25.
   - `SOTAWHAT_LLM_BUDGET_USD_RUN_WEEKLY` (padrão 8,00) vale para o `run weekly` e a ideação.
   - `SOTAWHAT_LLM_BUDGET_USD_MONTH` (padrão 25; subir para 45 no modo completo).
   - Ao atingir 80% de qualquer teto, o pipeline degrada nesta ordem: desliga o radar, passa a extração para raciocínio baixo e muda a ideação para o modo econômico ou a adia. O Telegram avisa. A coleta nunca é interrompida, porque não consome tokens.
3. **Visibilidade:** o custo real por etapa, lido de `usage.cost`, aparece no rodapé de cada digest e no `doctor`.

---

## 14. Riscos e mitigações

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Instagram: sem API oficial para conta pessoal; a varredura depende de terceiros (Apify/HikerAPI), que podem quebrar com mudanças do Instagram | alta | médio | captura manual pelo Telegram sempre disponível; dois fornecedores intercambiáveis; alerta quando a varredura falha; nunca a conta principal em método não oficial (§7.2) |
| Token OAuth do Gmail expirar (app em "Testing" expira refresh token em 7 dias) | alta se mal configurado | alto | publicar o app OAuth ("In production") ou usar IMAP com senha de app; `doctor` avisa 10 dias antes |
| Ruído persistente / rubrica mal calibrada | média | alto | golden set, feedback diário, revisão mensal de pesos, limite diário |
| Extração inconsistente gera entidades duplicadas | média | médio | aliases, limiar vetorial, juiz LLM, auditoria de merges, comando de merge manual |
| Custo LLM acima do esperado (raciocínio longo, preço por horário, troca de provedor) | média | baixo | limite na chave do OpenRouter; tetos internos por dia, semana e mês; custo real por chamada (`usage.cost`); `sort: "price"`; cache de prompt; degradação em ordem (§13) |
| Qualidade dos modelos chineses abaixo do Opus 5.5 na ideação (Kimi K3.1 Pro 46 × Opus 59 no AA Index) | média | médio | juízes de 3 famílias, críticos de família diferente do gerador, *bake-off* com golden sets, rodada *premium* opcional com Claude só no top 5 (§6.6) |
| Modelo/snapshot descontinuado, endpoint ZDR some ou preço muda (o catálogo muda todo mês) | alta | médio | 2–3 fallbacks de famílias diferentes por etapa; `doctor` checa `expiration_date` e endpoints elegíveis; *bake-off* mensal |
| Saída estruturada inválida (JSON fora do schema) | média | baixo | `json_schema` estrito + `require_parameters` + `response-healing` + validação Pydantic + 1 retentativa com o erro + próximo modelo |
| Retenção ou uso indevido de dados pelo provedor de inferência | baixa | alto | ZDR por requisição e na conta, `data_collection: "deny"`, nenhum dado sensível no sistema, ideias só por ZDR, sem Batch API |
| Inspeção TLS local intermitente (antivírus/proxy) derruba chamadas Python que usam o bundle `certifi` (`CERTIFICATE_VERIFY_FAILED` visto em `openrouter.ai` e `huggingface.co` em 2026-11-07) | média | alto | `truststore` (repositório de certificados do Windows) injetado no início do CLI desde a P0; nunca `verify=False` |
| OpenRouter fora do ar ou mudança na API | baixa | médio | gateway isolado atrás de uma interface de provedor; plano B por provedores com API compatível com a da OpenAI (DeepInfra, Fireworks) ou Claude pelo SDK oficial; a coleta não depende de LLM |
| Neo4j indisponível no horário (Docker Desktop fechado ou usuário sem sessão) | média | baixo | `start_graph.ps1` abre o Docker Desktop e espera o *healthcheck*; backend `memory` + `graph_outbox`; tarefa "ao fazer logon" sincroniza o atraso; alerta |
| Feeds que passam a devolver HTML anti-bot ou ficam vazios em silêncio (caso Nature hoje) | alta | médio | detecção de HTML/zero itens por fonte, fallback Crossref/PubMed, `source_state.consecutive_failures`, poda automática (§5.6) |
| Máquina desligada no horário | média | médio | *wake to run*; opção futura: mini-PC/NAS/VPS com o mesmo `docker compose` |
| Ideias genéricas/homogêneas | média | alto | candidatos vindos do grafo (lacunas), personas, crítica adversarial, verificação de novidade, memória de rejeições (§8) |
| Mudança de APIs (GitHub, HF, registries, Meta) | média | baixo | adapters isolados, fixtures, `doctor` detecta falhas consecutivas |

---

## 15. Decisões de arquitetura (resumo ADR)

| ID | Decisão | Alternativas consideradas | Motivo |
|---|---|---|---|
| D1 | **Grafo: Neo4j Community 2026.10 no Docker Desktop** (escolha do usuário, §16.1 item 11; `compose.yaml`, volume nomeado, portas só em localhost), plugins APOC + GDS Community; interface `GraphStore` fina; **LadybugDB** (fork MIT do Kùzu, embutido, `pip install ladybug`) documentado como alternativa "zero-ops" | Memgraph (ótimo MAGE, mas só Docker/WSL e licença BSL), FalkorDB (SSPL, Docker, sem Louvain/Leiden), **Kùzu (arquivado em 2025-10-10 — não usar)**, LadybugDB como primário, AuraDB Free (pausa após 72 h, apaga após 30 d, 200k nós), só NetworkX, só Obsidian | o usuário citou Neo4j; GDS CE traz Leiden, similaridade e predição de links in-database (insumos diretos da ideação); Neo4j Desktop/Bloom dá visualização imediata; servidor MCP oficial `mcp-neo4j-cypher` (Neo4j Labs, PyPI 0.6.0) permite consultar o grafo do Claude Code desde a fase P3; `neo4j-graphrag` 1.23 tem retrievers híbridos (o LLM continua passando pelo gateway próprio); é o único backend comum a todos os frameworks avaliados. Risco: JVM (~1–2 GB RAM) dentro do WSL2 e dependência do Docker Desktop aberto na sessão do usuário — mitigado por `sotawhat graph up` e, desde a v1.4, pelo fato de a interface e o MCP lerem do SQLite (D16). Detalhes: `grafo_stack.md` (KQ1, KQ7) |
| D2 | SQLite como registro operacional, grafo reconstruível | só grafo; Postgres | simplicidade local, auditoria, reprocessamento |
| D3 | Embeddings locais por padrão (**EmbeddingGemma-300m** via `fastembed` 0.9, CPU, multilíngue; o BGE-M3 previsto antes não existe no `fastembed`); a fusão "mesma história" usa título quase idêntico, não cosseno (medição 2026-11-07); **Voyage AI `voyage-4-lite`** como opção por flag (US$ 0,02/M tokens, 200 M tokens grátis; a Anthropic não oferece embeddings) | OpenAI/Gemini embeddings; sentence-transformers pesados | custo zero e offline por padrão; troca sem migração (dimensão fixa por índice; reindexar ao trocar) |
| D4 | Instagram: conta pessoal, logo **sem API oficial**. Captura manual pelo Telegram sempre ligada + varredura diária das contas públicas via Apify (HikerAPI como alternativa); método não oficial só por opt-in, desligado | converter a conta para Creator e usar Business Discovery; só instagrapi | escolha do usuário (§16.1, item 6); risco zero para a conta pessoal; custo dentro do crédito grátis da Apify |
| D5 | Modelos chineses de pesos abertos via OpenRouter, um por etapa: DeepSeek V4.1 Flash 1017 (triagem, extração, síntese), MiMo-V2.6-Flash (segmentação, visão), rotação DeepSeek · MiMo-V2.6-Pro · GLM-5.3 (+ Kimi K3.1 Pro) na ideação, juízes de 3 famílias | Anthropic Haiku/Sonnet/Opus (v1.0 deste SDD); um único modelo para tudo | escolha do usuário (§16.1, item 12); custo ~80% menor com qualidade na faixa Haiku/Sonnet nas etapas de volume; limite reconhecido na ideação (§6.6) |
| D6 | Telegram como canal principal | só e-mail; app web | fricção zero no celular, botões de feedback, captura manual |
| D7 | Local-first (Task Scheduler + Docker) | GitHub Actions + Aura; VPS | tokens e grafo locais; migração para VPS/NAS possível com o mesmo compose |
| D8 | Manter o pacote `sotawhat` e a CLI | novo repositório | continuidade de testes, histórico e docs |
| D9 | Relevância em dois estágios: classificador leve por perfil (embeddings + regressão logística com 👍/👎) como porta após 100 avaliações; LLM barato (modelo de triagem) só para rubrica, "por que importa" e extração | LLM em tudo; só regex/keywords | padrão com métrica publicada (Scholar Inbox F1 ≈ 84); custo 10× menor; responde à crítica "LLM é overkill" sem a fragilidade do regex |
| D10 | Gateway próprio e fino sobre a API do OpenRouter (`httpx`, Chat Completions, `json_schema` estrito + validação Pydantic), com interface de provedor; Claude opcional pelo SDK oficial `anthropic` | SDK `openai` com `base_url`; SDK do OpenRouter; litellm/instructor/pydantic-ai | controle total dos campos próprios do OpenRouter (`provider`, `models`, `plugins`, `usage.cost`); nenhuma dependência nova além de `pydantic`; testes com `httpx.MockTransport`; trocar de provedor não mexe no pipeline |
| D11 | Vocabulários controlados (A/B/C/D–G) + entidades abertas resolvidas por alias/embedding/juiz | ontologia totalmente aberta; ontologia totalmente fechada | chaves estáveis para scoring e consultas, sem perder nomes específicos (modelos, produtos) |
| D12 | **Sem Obsidian** (v1.4): nada lê nem escreve no vault; o export é JSON/CSV mais dumps do SQLite e do Neo4j | export Markdown compatível com Obsidian como visão de transição (v1.0–v1.3); Markdown como fonte de verdade (padrão Letta/Basic Memory/claude-obsidian) | pedido do usuário em 2026-11-08 ("não quero usar o vault do Obsidian ou o Obsidian whatsoever"); a interface própria (D16) substitui a visão do vault |
| D13 | Ideação com geração independente por lentes, críticos separados, prior art por facetas, torneio multi-juiz, seleção por portfólio e ledger com motivo de rejeição | agente único "coordenador"; Elo único; nota de novidade como critério principal | evidência 2024–2026 (§8.1) |
| D14 | Privacidade de LLM: ZDR obrigatório em todas as chamadas (`zdr: true` + imposição na conta), `data_collection: "deny"`, quantização ≥ fp8, sem Batch API (que não oferece ZDR) | Batch API para economizar; aceitar endpoints que retêm dados | as ideias são propriedade intelectual; exigir ZDR quase não custa nada nos modelos escolhidos, porque o endpoint ZDR elegível mais barato costuma ser o mais barato de todos |
| D15 | Modelo de cada etapa escolhido por *bake-off* periódico com os golden sets do projeto | confiar só em benchmarks públicos | índices públicos divergem entre versões e trazem números autodeclarados; o catálogo muda todo mês |
| D16 | **Grafo de entidades no SQLite; interface e MCP leem do SQLite; Neo4j como espelho**, sincronizado por marca d'água | interface lendo do Neo4j com fallback NetworkX (v1.0–v1.3); LadybugDB embutido | a interface funciona com o Docker Desktop fechado (o run das 07:00 pode acontecer sem sessão); uma só implementação das consultas, testável sem Docker; o Neo4j continua útil para Cypher, Neo4j Browser e, na P4, GDS |

---

## 16. Perguntas abertas para o usuário

As respostas mudam a implementação; onde não houver resposta, a suposição indicada vale.

### 16.1 Respostas incorporadas (2026-11-07 e 2026-11-08)

| # | Pergunta | Resposta do usuário | Consequência no SDD |
|---|---|---|---|
| 6 | Conta do Instagram profissional? Página do Facebook? App na Meta? | "não. é pessoal" | Sem API oficial, porque Business Discovery exige conta profissional e app na Meta. No lugar: captura manual pelo Telegram + varredura de contas públicas via Apify/HikerAPI (§7.2, D4); P5 ajustada; variáveis `IG_*`/`FB_*` comentadas no `.env.example` |
| 11 | Neo4j: serviço nativo, Docker Desktop ou LadybugDB? | "Docker Desktop" | `compose.yaml` na raiz, volume nomeado no WSL2, portas só em localhost; `start_graph.ps1` abre o Docker Desktop e espera o *healthcheck*; `graph_outbox` e tarefa "ao fazer logon" para quando o Docker não estiver de pé (§6.3, §6.12, §10.1, D1) |
| 12 | Orçamento e modelo de extração | "Quero usar modelos chineses comparáveis aos da Anthropic via OpenRouter para redução drástica de custo" | Camada LLM refeita sobre o OpenRouter com DeepSeek/MiMo/GLM/Kimi, só por endpoints ZDR (§6.6, D5, D10, D14, D15). A configuração recomendada cai de ≈ US$ 45–50 para ≈ US$ 8–11/mês (§13). Limite reconhecido na ideação (Kimi K3.1 Pro 46 × Opus 5.5 59) e *bake-off* na P1. Evidência: `llm_openrouter.md` |
| 13 | Fable 5.1 na rodada final? | sem resposta; superada pela 12 | Fable não entra. A rodada *premium* com Claude fica **opcional e desligada** (`ANTHROPIC_API_KEY` vazio) |
| 3 | Perfil `geral` (IA pura): radar ou desligado? | No golden set (2026-11-08), 24 dos 51 itens "incluir" eram IA de fronteira sem ligação com saúde; diante disso, a escolha foi "Duas seções" | O digest ganha duas seções principais: "IA ∩ Saúde" (≤ 10) e "Fronteira de IA" (≤ 5, com botões de voto); o radar fica com o resto. Regras em §6.7; pesos e limites em `config/rubric.yaml`; o prompt deixou de pedir pontes médicas inventadas |
| 9 | Canal: Telegram, e-mail ou ambos? | "Gostaria que o digest viesse na minha caixa de e-mail tbem" | Ambos. Telegram para ler e votar, e e-mail com a cópia do digest pelo SMTP do Gmail, usando a senha de app (§6.11, `DIGEST_EMAIL_TO`) |
| 16 | Export Markdown no vault por 60 dias? Migrar as 2.893 notas antigas? | "quero uma interface com um grafo construído por nós. Não quero usar o vault do Obsidian ou o Obsidian whatsoever"; depois, "Ignorar o vault" | Obsidian fora do projeto: nada lê nem escreve no vault, a tarefa diária foi registrada de novo sem `--vault`, os comandos do Obsidian saem do código e as notas antigas não são migradas (§9, D12, RF15) |
| — | Próxima fase depois da P1 | "Grafo + interface" | A P3 é executada antes da P2 e traz a interface web, antes prevista na P6 (§6.11, §11) |

### 16.2 Perguntas ainda abertas (valem as suposições)

**Fontes**
1. **"Runway AI"** — qual newsletter exatamente? Não há página de assinatura da RunwayML; há "Runway Magazine" (moda), "The Runway Ventures" (beehiiv), "Rethink the Runway" (Substack). Envie o endereço do remetente (header `From`) ou um e-mail de exemplo. *Suposição:* fica fora até confirmação.
2. *(P2, 2026-11-08: a label `newsletters/ai` ainda não existe; a busca por remetente achou 37 e-mails do AlphaSignal/DeepLearning.AI em 30 dias, que já entram por RSS/sitemap. O `doctor` avisa até o filtro ser criado.)* Além de AlphaSignal/The Batch/Runway, quais outras newsletters já chegam na sua caixa que devem entrar (ex.: TLDR AI, The Rundown, Import AI, Latent Space, STAT Health Tech, HTN Daily Brief)? *Suposição:* tudo o que receber a label `newsletters/ai`.
3. *(Respondida em 16.1: seção "Fronteira de IA".)*
4. Quais domínios da taxonomia (A01–A23) e stakeholders importam mais para a startup e para o seu papel na Rede D'Or? Há áreas a excluir (ex.: descoberta de fármacos, wellness de consumo)? *Suposição:* pesos iguais; exclusões conforme §6.7.

**Gmail e Instagram**
5. Usar a conta `lmlopes33@gmail.com`? Prefere **IMAP + senha de app** (exige verificação em 2 etapas) ou criar um projeto no Google Cloud (Gmail API)? *Suposição:* IMAP.
6. *(respondida — §16.1)*
7. Quantas contas do Instagram quer monitorar, e pode exportar a lista de seguidos (`following.json`)? Aceita a Apify no plano Free (crédito de US$ 5/mês; acima disso, Starter a US$ 19/mês) ou prefere a HikerAPI (pré-paga, ≈ US$ 1,5/mês)? Aceita o modo T4 (conta secundária, não oficial)? *Suposição:* até 50 contas, Apify Free, T4 desligado.
8. Captura manual via **bot do Telegram** (compartilhar post → bot) é aceitável? *Suposição:* sim; alternativa: e-mail para si mesmo.

**Entrega e operação**
9. Horário do digest (*suposição:* 07:00) e do relatório semanal (*suposição:* domingo 20:00)? Resumos em pt-BR (*suposição:* sim). *(Canal e limites respondidos em 16.1.)*
10. O PC fica ligado **e com sessão aberta** no horário? O Docker Desktop só roda com o usuário logado. Sem sessão, o run diário segue normalmente e o grafo sincroniza no próximo logon. Se a máquina costuma ficar desligada, considerar um mini-PC/NAS/VPS com o mesmo `compose.yaml`. *Suposição:* ligado, com logon diário.
11. *(respondida — §16.1)*

**Modelos, privacidade e orçamento**
12. *(respondida — §16.1)* 
13. *(superada pela 12 — §16.1)*
18. Ligar a imposição de ZDR **também na conta** do OpenRouter (além de cada requisição) e criar uma chave dedicada com limite mensal de US$ 30? *Suposição:* sim.
19. Habilitar a rodada *premium* com Claude (SDK oficial, só no top 5 de ideias, ≈ US$ 1–2/semana) se o *bake-off* mostrar ganho claro na ideação? *Suposição:* não, até haver evidência.

**Ideação**
14. Cadência semanal com 5–10 ideias está boa? Que **formas** interessam mais (SaaS B2B hospitalar, dispositivo/bioengenharia, solução corporativa para a Rede D'Or, B2B2C)? Restrições conhecidas (PEP usado pela Rede D'Or — MV/Tasy/outro —, acesso a dados, programa de inovação interno, orçamento de piloto)? *Suposição:* todas as formas; sem restrições além de §2.2.
15. Para verificação de novidade: liberar acesso à **Lens.org** (requer e-mail institucional) e/ou **EPO OPS** (grátis até 4 GB/semana)? Usar **Exa** (crédito grátis)? *Suposição:* Semantic Scholar + OpenAlex + GitHub + EPO OPS.

**Transição**
16. *(respondida — §16.1: sem Obsidian e sem migração)*
17. Manter o nome `sotawhat` (versão 3.0) ou renomear o repositório? *Suposição:* manter.

### 16.3 Ações que dependem de você (2026-11-08, ao fim da P6)

1. **Chave do OpenRouter.** O limite de US$ 5 da chave não renova (`limit_reset` vazio; o `doctor` avisa). O pipeline gasta ≈ US$ 0,10 por dia mais ≈ US$ 0,13 por semana, ou seja, ≈ US$ 4 por mês, e a chave se esgota em ~5 semanas. Defina a renovação mensal e um limite de ≈ US$ 15–20/mês.
2. **Gmail.** Crie o filtro que aplica a label `newsletters/ai` às newsletters sem RSS (§16.2, item 2).
3. **Instagram.**
   - Exporte "Seguidores e seguindo" em JSON no Accounts Center e rode `sotawhat instagram import following.json --yes`.
   - Revise `config/instagram_accounts.yaml`.
   - A captura manual já funciona: no app, Compartilhar → Telegram → o bot.
4. **Votos.** Vote nos digests e nas ideias:
   - o classificador começa com 100 votos por perfil;
   - a calibração da triagem, com 100 votos;
   - os pesos da rubrica de ideias, com 30 decisões.
5. **Anotação da extração** (meta G3). Rode `sotawhat eval extract draft`, desmarque o que estiver errado no Markdown e rode `sotawhat eval extract import`.
6. **Opcionais:**
   - chave do Semantic Scholar (hoje dá 429);
   - chaves do Lens.org ou do EPO OPS (patentes no prior art);
   - `uv pip install -e ".[audio]"` para transcrever reels;
   - no Docker Desktop, "Start Docker Desktop when you sign in", para o espelho Neo4j.

---

## 17. Apêndices

### A. Notas de pesquisa (2026-11-07, `docs/research/2026-11-07-insight-engine/`)

| Arquivo | Conteúdo | Observação |
|---|---|---|
| `fontes_conhecimento.md` | catálogo de fontes verificadas (newsletters, periódicos, preprints, agregadores, regulatório, Brasil), tiers e sobreposição | base do §5 |
| `plataformas_similares.md` | ~110 produtos/repositórios; arquiteturas; reclamações de usuários e padrões anti-ruído; build × buy × reuse; 8 componentes OSS | base do §2.4, §6.7, §6.11 |
| `integracoes.md` | Gmail, Instagram (oficial, terceiros, legal), GitHub, registries MCP, skills, HF Hub; tabela consolidada de `.env` | base do §7 e §10 |
| `grafo_stack.md` | bancos de grafos (Kùzu arquivado → LadybugDB; Neo4j; Memgraph; FalkorDB…), frameworks GraphRAG, resolução de entidades, visualização, migração do Obsidian, ontologia | base do §6.3, §6.5, §6.8, §15 |
| `geracao_ideias.md` | estado da arte 2024–2026 em ideação com LLM/agentes, LBD/KG, métodos clássicos, prior art, arquitetura recomendada, armadilhas | base do §8 |
| `panorama_saude_ia.md` | produtos com tração e evidência em hospitais, dores por stakeholder, tendências, contexto Brasil (CFM 2.454/2026, ANVISA, LGPD, PL 2338, RNDS, Rede D'Or/IDOR, pares, funding), taxonomia A–G, critérios incluir/excluir | base do §6.5, §6.7 e da taxonomia |
| `llm_openrouter.md` | catálogo e endpoints do OpenRouter (preço, quantização, ZDR, saída estruturada), AA Intelligence Index dos modelos chineses × Anthropic, recursos do OpenRouter (roteamento, ZDR, Batch, cache, custo real), matriz por etapa, custos e riscos | base do §6.6, §13, D5, D10, D14, D15; consultas diretas às APIs em 2026-11-07 |
| `embeddings_dedup.md` | benchmark de 6 modelos do `fastembed` em CPU (velocidade e separação "mesma história" × "outro trabalho"), deduplicação por título no vault (2.893 notas), limiares da novidade D | base do §6.3, §6.7 e D3; medido nesta máquina em 2026-11-07/08 |

Limitação comum: a cota de busca web da sessão esgotou-se durante a pesquisa; itens marcados **[incerto]**/**[não verificado]** nas notas devem ser confirmados antes de virar fato no grafo.

### B. Bibliotecas e serviços escolhidos (versões verificadas em 2026-11-07)

| Função | Escolha | Alternativa |
|---|---|---|
| LLM | API do OpenRouter via `httpx` (Chat Completions, `json_schema` estrito, `provider` com ZDR, `models` para fallback, `usage.cost`) + `pydantic` 2 para os schemas | SDK `openai` apontado para o OpenRouter; `anthropic` 2.6 só na rodada *premium* opcional |
| Configuração | `pydantic-settings` 2 (`.env` + variáveis de ambiente) | `python-dotenv` |
| TLS | `truststore` (verificação pelo repositório do Windows; resolve a inspeção TLS local) | `SSL_CERT_FILE` |
| Embeddings | `fastembed` 0.9 (`google/embeddinggemma-300m`) | Voyage `voyage-4-lite`; `minishlab/potion-multilingual-128M` (estático, 150× mais rápido, mais fraco) |
| Dedup | títulos normalizados + Jaccard/`difflib` (stdlib) com índice invertido | juiz LLM para notícias (P2); `datasketch` (MinHash LSH) se o volume crescer |
| Classificador | `scikit-learn` 1.9 (`LogisticRegression`, validação cruzada estratificada) | — |
| Configuração editável | `pyyaml` 6 (`config/rubric.yaml`, `mute.yaml`, `llm.yaml`) | — |
| Grafo | entidades no SQLite; espelho com o driver `neo4j` 6.4 e a imagem `neo4j:2026.10.1-community` no Docker Desktop (APOC + GDS CE na P4); opcional `neo4j-graphrag` 1.23 (retrievers) | `networkx` 3.7 para algoritmos fora do GDS |
| MCP | `mcp` 2.3 (`MCPServer`): servidor próprio sobre o SQLite, com Cypher só leitura no Neo4j | `mcp-neo4j-cypher` 0.6 (Neo4j Labs) |
| Gmail | `imapclient` 4.1 (`gmail_search`/X-GM-RAW) | `google-api-python-client` 2.201 + `google-auth-oauthlib` 1.5 |
| HTML/links | `html2text` 2025.4, `trafilatura` 2.3, `w3lib` 2.6, `httpx` | `readability-lxml` |
| Instagram | Graph API via `httpx`; `apify-client` 3.4 ou HikerAPI via `httpx` | `instagrapi` 3.2 (T4, opt-in) |
| GitHub | `httpx` (REST + ETag) e `feedparser` (`releases.atom`); `gh` para protótipos | `PyGithub` 2.10 |
| HF | `huggingface_hub` 2.4 + `truststore` | — |
| Vídeo/áudio | `ffmpeg`, `faster-whisper` 1.2 | — |
| PDF (opcional) | `docling` | `pymupdf4llm` (AGPL) |
| Telegram | `python-telegram-bot` 22.8 | `aiogram`, `telethon` |
| Web | FastAPI + uvicorn; sigma.js 3.0.3, graphology 0.26 e graphology-library 0.8 (ForceAtlas2 e Louvain no navegador), arquivos no pacote, sem CDN. O sigma.js 4 saiu em outubro de 2026 e ainda é novo demais | Neo4j Browser/Bloom, NeoDash, Gephi Lite |

### C. Glossário

AA Index — Artificial Analysis Intelligence Index (índice agregado de benchmarks; usado só como ordenação grosseira). · ABC (Swanson) — modelo de descoberta baseada em literatura: A (técnica) → B (capacidade intermediária) → C (problema). · BD — Business Discovery (endpoint oficial do Instagram). · CFM 2.454/2026 — resolução que normatiza IA na medicina no Brasil (vigente desde 26/08/2026). · GDS — Graph Data Science (biblioteca de algoritmos do Neo4j). · JTBD — Jobs-to-be-Done. · LBD — descoberta baseada em literatura. · MAP-Elites — algoritmo de qualidade-diversidade com nichos. · NASSS — framework de não-adoção/abandono/escala/difusão/sustentabilidade (Greenhalgh 2017). · NGT — técnica de grupo nominal (geração independente antes da discussão). · OpenRouter — agregador de APIs de LLM: uma chave e um endpoint para centenas de modelos e provedores, com roteamento por preço, privacidade e quantização. · SaMD — *software as a medical device* (RDC 657/2022). · Vendi score — métrica de diversidade de um conjunto. · ZDR — *Zero Data Retention*: endpoint que não armazena prompts nem respostas após o processamento.
