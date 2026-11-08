# Fontes de conhecimento: fronteira de IA ∩ medicina/hospitais — catálogo verificado (2026-11-07)

Método: (1) ~500 URLs candidatas de feed/API sondadas de uma máquina Windows com `urllib` e User-Agent de Chrome (o mais próximo do pipeline `httpx` do usuário), com parse RSS/Atom/JSON e contagem de itens; (2) leitura direta das páginas-chave (WebFetch); (3) um subagente cobriu notícias/newsletters/podcasts/YouTube/VC/big-tech com `curl` + iTunes Search API (fatos marcados "subagente"). O orçamento de busca web da sessão esgotou após 2 consultas, portanto nada abaixo veio de buscadores: tudo é fetch direto do publicador ou de API pública. Datas de "último item" são as do feed em 2026-11-07.

Legenda de status: **OK(n=N, data)** = feed devolvido a cliente não-browser com N itens e data do item mais recente; **BLOQ** = 403/429/desafio Cloudflare/Akamai/F5 para cliente não-browser; **404** = inexistente; **HTML** = página sem feed; **VAZIO** = XML válido sem itens; **NV** = não verificado. Nos feeds de Google News, Crossref, OpenAlex e Europe PMC a própria URL é a fonte.

## Q1 — AlphaSignal, DeepLearning.AI "The Batch" e "Runway AI"

### Takeaway
AlphaSignal e The Batch podem ser ingeridos sem e-mail (AlphaSignal tem RSS/Atom oficiais; The Batch não tem RSS, mas o sitemap lista todas as edições `issue-NNN`); nenhum dos dois expõe o endereço remetente nas páginas (filtre por domínio). "Runway AI" é quase certamente a Runway (runwayml.com → redireciona para runway.com, título de página "News | Runway AI"): sem RSS, sem newsletter pública, relevância hospitalar baixa.

### Cited Findings

**AlphaSignal (Lior Alexander)**
- Site "The Front Page of AI"; o arquivo llms.txt oficial lista: "Main RSS: https://alphasignal.ai/feed.xml", "News RSS: https://alphasignal.ai/feed/news.xml", "Atom: https://alphasignal.ai/atom.xml", "Newsletter: https://newsletter.alphasignal.ai/", twins em Markdown `https://alphasignal.ai/news/<slug>.md`, servidor MCP `https://api.alphasignal.ai/mcp` — [Source](https://alphasignal.ai/llms.txt)
- Feeds verificados: [feed.xml](https://alphasignal.ai/feed.xml) OK(n=14, 2026-11-06); [atom.xml](https://alphasignal.ai/atom.xml) OK(n=14, 2026-11-06); [feed/news.xml](https://alphasignal.ai/feed/news.xml) OK(n=20, 2026-11-07). O conteúdo são as matérias do site (ex.: "Nous Research's Arete-27B…"), não as edições de e-mail; `/feed` e `/rss` → 404 — [Source](https://alphasignal.ai/feed.xml)
- Página da newsletter: "Get a daily 5-min email summary of the most important breakthroughs in the industry. All signal. No Noise."; "Join 300,000+ engineers and subscribers. Free."; cadastro "CONTINUE WITH Google / GitHub"; itens etiquetados NEWS, PAPER, MODEL, REPO; barra "THIS WEEK" (announcements/papers/models/repos); nenhum marcador beehiiv/Substack/Mailchimp (plataforma própria); links apenas para feed.xml/atom.xml — [Source](https://newsletter.alphasignal.ai/)
- About: "most-read independent publication in AI, with over 300,000 subscribers"; "first autonomous editorial system… no human in the editorial loop"; fundador Lior Alexander, Editorial Lead Ben Dickson; contato editorial@alphasignal.ai; publisher "Alpha Signal, LLC" — [Source](https://alphasignal.ai/about)
- Arquivo público: https://alphasignal.ai/archive ("Browse past AlphaSignal newsletter issues") existe, mas a lista é renderizada por JS (HTML sem URLs de edições; sitemap sem URLs de newsletter) — [Source](https://alphasignal.ai/archive)
- Espelho Substack: [alphasignalai.substack.com/feed](https://alphasignalai.substack.com/feed) OK(n=20, último 2026-07-13; descrição "The most read technical newsletter in AI… 5 min daily") — aparentemente descontinuado em jul/2026 — [Source](https://alphasignalai.substack.com/feed); a página About do Substack dizia "three emails a week… research, code, news" (snippet de busca, não aberto) — [Source](https://alphasignalai.substack.com/about)
- Remetente de e-mail: não aparece em nenhuma página (NV). Domínio: alphasignal.ai; imagens do e-mail servidas de newsletter.alphasignal.ai — [Source](https://newsletter.alphasignal.ai/)

**DeepLearning.AI — The Batch**
- Semanal: "delivers weekly AI news and insights"; "Every issue includes a personal letter from Andrew Ng"; navegação com seções Weekly Issues, Andrew's Letters, Data Points, ML Research, Business, Science, Culture, Hardware, AI Careers; tags `/the-batch/tag/letters`, `/tag/data-points`, `/tag/research`, `/tag/business` — [Source](https://www.deeplearning.ai/the-batch/about/)
- Padrão de URL e cadência: edições `https://www.deeplearning.ai/the-batch/issue-NNN` datadas em sextas-feiras consecutivas (issue-378 = 06/11/2026, 377 = 30/10, 376 = 23/10, 375 = 16/10, 374 = 09/10, 373 = 02/10) — [Source](https://www.deeplearning.ai/the-batch/)
- Estrutura da edição 378 (06/11/2026, "16 min read"): "Dear friends," (carta assinada "Andrew" + P.S.); "A MESSAGE FROM DEEPLEARNING.AI" (patrocínio); "News" com 4 matérias, cada uma com subtítulos "What's new / How it works (ou The offering, Key insight) / Results (ou Performance) / Behind the news / Why it matters / We're thinking"; anúncio de curso; bloco "Subscribe to The Batch"; player ElevenLabs; sem "Data Points" nesta edição — [Source](https://www.deeplearning.ai/the-batch/issue-378/)
- RSS: inexistente — `/the-batch/feed/`, `/feed/`, `/rss.xml`, `/the-batch/rss/` → 404 — [Source](https://www.deeplearning.ai/the-batch/feed/); diretório de feeds confirma "no RSS feed of its own" — [Source](https://feeder.co/discover/0a52ae6a62/deeplearning-ai-the-batch)
- Ingestão sem e-mail: o sitemap lista 393 URLs `the-batch/issue-…` (diff diário = novas edições) — [Source](https://www.deeplearning.ai/sitemap.xml); a página da listagem expõe os links `/the-batch/issue-375…378` — [Source](https://www.deeplearning.ai/the-batch/)
- Plataforma de inscrição: marcadores `hsforms`/`Hubspot` no HTML da listagem (formulário HubSpot) — [Source](https://www.deeplearning.ai/the-batch/); endereço remetente não aparece (NV); domínio deeplearning.ai.

**"Runway AI" — candidatos**
- (i) Runway (empresa de vídeo generativo): `runwayml.com` → 308 para `https://runway.com/`; página de notícias intitulada "News | Runway AI"; seções "Research News" (`/news/research`), "Customer Stories" (`/news/customers`), "News" (`/news`), "Changelog" (`/changelog`); **sem RSS e sem formulário de newsletter** na home e na página de notícias; hub de pesquisa `https://runway.com/research` e `https://runway.com/research/publications`; programas Runway Studios, Gen:48, AI Festival, AI Summit 2026, Academy — [Source](https://runway.com/news), [Source](https://runway.com/); `runwayml.com/rss.xml` e `/feed` → 404, `/research/feed` → 500 — [Source](https://runwayml.com/feed)
- (ii) "The AI Runway: Preparing education for the ascent ahead" (Substack sobre educação; 4 posts, último 2026-03-06) — não é IA médica — [Source](https://airunway.substack.com/feed)
- (iii) `therunway.substack.com` (1 post, 2023, morto), `runwayai.substack.com` → 404, `therunway.ai` → DNS falha, `runway.ai` → redireciona para runway.com — [Source](https://therunway.substack.com/feed)

| Newsletter | Plataforma | Remetente (p/ filtro Gmail) | Cadência | Arquivo web / RSS | Ingestão recomendada |
|---|---|---|---|---|---|
| AlphaSignal | própria (login Google/GitHub); espelho Substack inativo | NV; domínio `alphasignal.ai` (+ `newsletter.alphasignal.ai`) | diária | arquivo JS-only; RSS oficiais feed.xml / atom.xml / feed/news.xml | RSS feed.xml (sem e-mail) |
| The Batch | HubSpot (formulário) | NV; domínio `deeplearning.ai` | semanal (sexta) | `/the-batch/issue-NNN`; sem RSS | diff do sitemap.xml + scrape da edição |
| Runway (AI) | — | NV; domínios `runwayml.com`/`runway.com` | irregular | `/news`, `/news/research`, `/changelog`; sem RSS | scrape HTML (baixa prioridade) |

### Inferences
- Para filtros Gmail, usar domínio (`from:(@alphasignal.ai)`, `from:(@deeplearning.ai)`) em vez de endereço exato, já que nenhum remetente foi verificado.
- O feed.xml do AlphaSignal cobre o mesmo noticiário dos e-mails (mesma redação "autônoma"), logo substitui o e-mail para o pipeline; o Substack de jul/2026 indica que o canal Substack foi abandonado.
- "Runway AI" dificilmente se refere a uma publicação médica; se o usuário recebe um e-mail "Runway" sobre IA generativa de vídeo, é a Runway; relevância hospitalar baixa (Tier 3).

### Gaps
- Endereços remetentes das três newsletters: não publicados nas páginas; verificar no cabeçalho de um e-mail recebido.
- Seções canônicas do e-mail diário do AlphaSignal (além das etiquetas NEWS/PAPER/MODEL/REPO) não puderam ser confirmadas porque o arquivo é renderizado por JS.
- Possível newsletter do LinkedIn chamada "Runway AI" (LinkedIn não tem RSS) não pôde ser pesquisada (sem orçamento de busca).

## Q2 — Outras newsletters/digests de IA de fronteira, feeds de laboratórios, substitutos do Papers with Code e comunidades

### Takeaway
Quase todos os digests têm RSS funcional (TLDR AI, Rundown, Neuron, Ben's Bites, Import AI, Latent Space, Interconnects, The Sequence, Zvi, One Useful Thing, Exponential View); os feeds primários dos laboratórios que funcionam são OpenAI news, Google Keyword (AI e Health), Mistral, NVIDIA, Microsoft Research, AWS, Apple e o novíssimo feed de release notes do Claude; Anthropic news e Meta AI blog não têm RSS. Papers with Code morreu (redireciona para HF Papers); alphaXiv/Emergent Mind não expõem feed.

### Cited Findings

**Status das fontes já mapeadas (liveness em 2026-11-07)**
- OK: [Google Research](https://research.google/blog/rss/) (n=100, 2026-11-05), [DeepMind](https://deepmind.google/blog/rss.xml) (n=100, 2026-11-05), [HF blog](https://huggingface.co/blog/feed.xml) (n=899, 2026-11-06), [Ahead of AI](https://magazine.sebastianraschka.com/feed) (2026-10-24), [Simon Willison](https://simonwillison.net/atom/everything/) (2026-11-06), [MarkTechPost](https://www.marktechpost.com/feed/) (2026-11-07), [JMIR AI](https://ai.jmir.org/feed/atom) (2026-11-06), [JMIR Med Inform](https://medinform.jmir.org/feed/atom) (2026-11-06), [HF daily_papers](https://huggingface.co/api/daily_papers) (n=50).
- Lentos/parados: [BAIR](https://bair.berkeley.edu/blog/feed.xml) último post 2026-07-29; [The Gradient](https://thegradient.pub/rss/) último post 2026-02-18 (9 meses sem conteúdo).
- Atenção: [natmachintell.rss](https://www.nature.com/natmachintell.rss) e [npjdigitalmed.rss](https://www.nature.com/npjdigitalmed.rss) devolveram página HTML de desafio anti-bot (assets `/_fs-ch-…`) em todas as 4 tentativas do dia (UAs Chrome/Firefox/custom), enquanto nature.rss, natbiomedeng.rss, npjhealthsyst.rss e commsmed.rss vieram como RSS 1.0 na 1ª rodada e HTML nas rodadas seguintes → proteção intermitente por volume/IP — [Source](https://www.nature.com/nm.rss)

**(a) Newsletters/digests de IA (todos gratuitos; ruído "alto" = IA genérica sem foco médico)**

| Fonte | Tipo | Feed (verificado) | Plataforma / remetente | Cadência | Sinal | Ruído p/ hospital |
|---|---|---|---|---|---|---|
| The Rundown AI | newsletter | [therundown.ai/feed](https://www.therundown.ai/feed) OK(n=50, 2026-11-06) | própria (ex-beehiiv; `rundown.beehiiv.com` redireciona para `rundown.runtheday.com`); remetente NV | diária | lançamentos + "how to apply" | alto |
| TLDR AI | newsletter | [tldr.tech/api/rss/ai](https://tldr.tech/api/rss/ai) OK(n=20, 2026-11-06); arquivo [tldr.tech/ai/archives](https://tldr.tech/ai/archives) | própria; remetente NV | diária (dias úteis) | manchetes curtas com links | alto |
| The Neuron | newsletter | [theneuron.ai/feed](https://www.theneuron.ai/feed/) OK(Atom n=10, 2026-11-06); beehiiv [rss.beehiiv.com/feeds/N4eCstxvgX.xml](https://rss.beehiiv.com/feeds/N4eCstxvgX.xml) OK(n=20) | beehiiv | diária | mainstream | alto |
| Ben's Bites | newsletter | [bensbites.com/feed](https://www.bensbites.com/feed) OK(n=20, 2026-11-05; "What I'm learning building with agents") | própria | 2-3/sem | ensaios sobre agentes | alto |
| Import AI (Jack Clark) | newsletter | [importai.substack.com/feed](https://importai.substack.com/feed) OK(n=20, #479 2026-11-02); espelho [jack-clark.net/feed](https://jack-clark.net/feed/) | Substack (`importai@substack.com` padrão Substack, NV) | semanal (seg) | pesquisa + política de IA | médio |
| Latent Space | newsletter+podcast | [latent.space/feed](https://www.latent.space/feed) OK(n=20, 2026-11-07; inclui [AINews] diário); podcast [podcast.latent.space/feed.xml](https://podcast.latent.space/feed.xml) (294 eps, subagente) | Substack | diária/semanal | engenharia de IA | alto |
| Interconnects (N. Lambert) | newsletter | [interconnects.ai/feed](https://www.interconnects.ai/feed) OK(n=20, 2026-11-04) | Substack | semanal | modelos abertos/RLHF | alto |
| The Sequence | newsletter | [thesequence.substack.com/feed](https://thesequence.substack.com/feed) OK(n=20, #966 2026-11-05) | Substack | várias/sem | pesquisa | alto |
| Last Week in AI | newsletter+podcast | [lastweekin.ai/feed](https://lastweekin.ai/feed) OK(n=20, #346 2026-10-09 — irregular); podcast [rss.art19.com/last-week-in-ai](https://rss.art19.com/last-week-in-ai) (subagente) | Substack | semanal (falhas) | resumo semanal | alto |
| AI Tidbits | newsletter | [aitidbits.ai/feed](https://www.aitidbits.ai/feed) OK(n=20, último 2026-04-14 — parado) | Substack | parado | — | — |
| One Useful Thing (Mollick) | newsletter | [oneusefulthing.org/feed](https://www.oneusefulthing.org/feed) OK(2026-10-20) | Substack | ~quinzenal | uso prático de LLMs | médio |
| Don't Worry About the Vector (Zvi) | newsletter | [thezvi.substack.com/feed](https://thezvi.substack.com/feed) OK(2026-11-06) | Substack | várias/sem (longuíssimo) | cobertura exaustiva | alto |
| Exponential View | newsletter | [exponentialview.co/feed](https://www.exponentialview.co/feed) OK(2026-11-06) | Substack | semanal | macro/estratégia | alto |
| AI Snake Oil → Normal Technology | newsletter | [aisnakeoil.com/feed](https://www.aisnakeoil.com/feed) → `normaltech.ai/feed` OK(2026-10-19) | Substack | mensal | ceticismo/avaliação | médio |
| Superhuman AI | newsletter | `superhuman.ai/feed` → 404 | beehiiv | — | — | — |
| Hugging Face newsletter | — | não encontrado feed/arquivo público; HF blog e daily_papers já cobrem | — | — | — | — |

**(b) Blogs/feeds de laboratórios e produtos**

| Fonte | Feed | Status | Último item | Notas |
|---|---|---|---|---|
| Anthropic news | — | `/rss.xml`, `/news/rss.xml`, `/feed` → 404; [anthropic.com/news](https://www.anthropic.com/news) HTML | — | scrape HTML; `rsshub.app/anthropic/news` → 403 |
| Claude Platform release notes | [platform.claude.com/docs/en/release-notes/feed.xml](https://platform.claude.com/docs/en/release-notes/feed.xml) | OK(n=165) | 2026-11-05 | descoberto via `<link rel=alternate>` de [docs.claude.com/en/release-notes/overview](https://docs.claude.com/en/release-notes/overview) |
| OpenAI news | [openai.com/news/rss.xml](https://openai.com/news/rss.xml) | OK(n=1368) | 2026-11-06 | `/blog/rss.xml` redireciona; `/research/rss.xml` 404; filtrar "health" |
| Google The Keyword — AI | [blog.google/technology/ai/rss/](https://blog.google/technology/ai/rss/) → `blog.google/innovation-and-ai/technology/ai/rss/` | OK(n=20) | 2026-11-05 | |
| Google The Keyword — Health | [blog.google/innovation-and-ai/technology/health/rss/](https://blog.google/innovation-and-ai/technology/health/rss/) | OK(n=20) | 2026-11-04 ("framework for building safer and more helpful AI for health") | alto sinal p/ saúde |
| Google DeepMind | já mapeado | OK | 2026-11-05 | |
| Meta AI blog | `ai.meta.com/blog/rss/` e `/feed/` → 400 | BLOQ | — | alternativas OK: [about.fb.com/news/feed/](https://about.fb.com/news/feed/) (n=10), [engineering.fb.com/feed/](https://engineering.fb.com/feed/) (n=9) |
| Mistral AI | [mistral.ai/news/rss](https://mistral.ai/news/rss) | OK(n=94) | 2026-11-05 | `/rss.xml` redireciona para `/news/rss` |
| NVIDIA blog | [blogs.nvidia.com/feed/](https://blogs.nvidia.com/feed/) | OK(n=18) | 2026-11-06 | categoria healthcare `/blog/category/healthcare/feed/` → 404 (slug inexistente) |
| NVIDIA Technical Blog | [developer.nvidia.com/blog/feed](https://developer.nvidia.com/blog/feed) | OK(Atom n=100) | 2026-11-06 | [category/healthcare/feed/](https://developer.nvidia.com/blog/category/healthcare/feed/) devolveu Atom **vazio** em 3 testes (subagente reportou itens via curl → inconsistente) |
| Microsoft Research | [microsoft.com/en-us/research/feed/](https://www.microsoft.com/en-us/research/feed/) | OK(n=10) | 2026-11-05 | o feed `group/health-futures/feed/` entrega "Microsoft Research Asia Articles" (errado) |
| Microsoft Source / blogs | [news.microsoft.com/source/feed/](https://news.microsoft.com/source/feed/) OK; [blogs.microsoft.com/feed/](https://blogs.microsoft.com/feed/) OK; `blogs.microsoft.com/ai/feed/` → 410 | OK | 2026-11-05 | |
| AWS ML blog | [aws.amazon.com/blogs/machine-learning/feed/](https://aws.amazon.com/blogs/machine-learning/feed/) | OK(n=20) | 2026-11-06 | ver Q4 p/ categoria healthcare |
| Amazon Science | [amazon.science/index.rss](https://www.amazon.science/index.rss) | OK(n=25) | 2026-11-05 | |
| Apple ML Research | [machinelearning.apple.com/rss.xml](https://machinelearning.apple.com/rss.xml) | OK(n=10) | 2026-11-05 | |
| Epic / Oracle Health | sem feed (`epic.com/feed/` 404; `oracle.com/news/rss.xml` 404; `blogs.oracle.com/health` 403) | — | — | HIStalk cobre Epic diariamente (ver Q3) |
| xAI / Cohere | não sondados | NV | — | |

**(c) Substitutos do Papers with Code**
- Papers with Code: `paperswithcode.com` redireciona para `https://huggingface.co/papers/trending` (morto) — [Source](https://paperswithcode.com/)
- alphaXiv: homepage sem `<link>` de feed; `/feed` redireciona para a home (sem RSS/API pública encontrada) — [Source](https://www.alphaxiv.org/feed)
- Emergent Mind: `/feed` → 404 — [Source](https://www.emergentmind.com/feed)
- Paper Digest: [paperdigest.org/feed/](https://www.paperdigest.org/feed/) responde 200 mas XML malformado ("unclosed CDATA") — feedparser tolerante pode ler — [Source](https://www.paperdigest.org/feed/)
- Cool Papers: [papers.cool/arxiv/eess.IV/feed](https://papers.cool/arxiv/eess.IV/feed) OK(Atom n=6, 2026-11-04) — espelho por categoria arXiv com resumo — [Source](https://papers.cool/arxiv/eess.IV/feed)
- arXiv RSS oficial: [rss.arxiv.org/rss/eess.IV](https://rss.arxiv.org/rss/eess.IV) e cs.LG responderam 200 com 0 itens no sábado (feed só lista anúncios do dia); a API [export.arxiv.org/api/query?search_query=cat:eess.IV](http://export.arxiv.org/api/query?search_query=cat:eess.IV&sortBy=submittedDate&sortOrder=descending&max_results=5) OK(n=5, 2026-11-05) — [Source](https://rss.arxiv.org/rss/eess.IV)
- HF trending: `api/models?sort=trending` → 400; usar `sort=trendingScore` (ver Q4) ou [huggingface.co/api/trending?type=model](https://huggingface.co/api/trending?type=model&limit=3) OK — [Source](https://huggingface.co/api/trending?type=model&limit=3)

**(d) Comunidades**
- Hacker News: [hnrss.org/newest?q=medical+AI](https://hnrss.org/newest?q=medical+AI) OK(n=20, último 2026-11-02; teve 502 transitório); [Algolia](https://hn.algolia.com/api/v1/search_by_date?query=medical%20AI&tags=story&hitsPerPage=20) OK(JSON n=20) — [Source](https://hn.algolia.com/api/v1/search_by_date?query=medical%20AI&tags=story&hitsPerPage=20)
- Reddit: `.rss` funciona com UA de browser em requisições isoladas ([r/medicine/new/.rss](https://www.reddit.com/r/medicine/new/.rss) OK n=25; r/healthIT OK em requisição única) mas 429 em rajada (r/MachineLearning, r/artificial, r/LocalLLaMA); `.json` → 403 sem OAuth — [Source](https://www.reddit.com/r/MachineLearning/new.json?limit=25)
- Lobste.rs tag ai: [lobste.rs/t/ai.rss](https://lobste.rs/t/ai.rss) OK(n=25, 2026-11-07) — [Source](https://lobste.rs/t/ai.rss)

### Inferences
- Digests diários (AlphaSignal/TLDR/Rundown/Neuron/Ben's Bites) são permutáveis: cobrem os mesmos lançamentos que os feeds primários dos laboratórios já mapeados (OpenAI/DeepMind/Google/Mistral/HF); manter no máximo um (TLDR AI, pelo RSS limpo e arquivo).
- Para Anthropic, a combinação "release notes RSS + scrape de /news" cobre produto; notícias de saúde da Anthropic aparecem também em STAT/Healthcare Dive.
- Reddit só é viável com 1 requisição a cada vários segundos e cache; `.json` exige app OAuth.

### Gaps
- Remetentes de e-mail de todas as newsletters (NV).
- Subreddits dedicados a IA médica ativos em 2025-26: não verificados (sem busca).
- alphaXiv pode ter API não documentada (NV).

## Q3 — Fontes específicas de medicina ∩ IA

### Takeaway
Os periódicos de maior sinal (NEJM AI, Lancet Digital Health, Radiology: AI, JAMIA, Cell Reports Medicine, Nature Medicine) bloqueiam RSS para bots ou servem desafio JS, mas todos têm rota alternativa gratuita e verificada: ScienceDirect RSS (resolve o Lancet Digital Health), PubMed `[jour]`, Crossref `journals/<ISSN>/works` e Europe PMC; JAMA Network tem coleção "Artificial Intelligence" com RSS funcional; medRxiv tem API com filtro de categoria. Entre notícias, STAT (tópico IA), Healthcare Dive (health-IT), MedCity (categoria IA), Fierce (feed "AI and Machine Learning" com `%20`) e AuntMinnie funcionam; Healthcare IT News, HIMSS, Health Affairs, Becker's (seções) e Mayo Clinic Platform estão bloqueados (contornáveis por Google News `site:`).

### Cited Findings

**3a. Periódicos (rota direta e alternativa)**

| Periódico | Feed direto | Status | Rota alternativa verificada | Cadência | OA? |
|---|---|---|---|---|---|
| NEJM AI | `https://ai.nejm.org/action/showFeed?type=etoc&feed=rss&jc=ai` | BLOQ 403 (Atypon; home também 403; UA Safari idem) — [Source](https://ai.nejm.org/action/showFeed?type=etoc&feed=rss&jc=ai) | PubMed `"NEJM AI"[Journal]` → 330 registros — [Source](https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=%22NEJM+AI%22%5Bjour%5D&sort=date&retmax=3&retmode=json); Crossref ISSN 2836-9386 ("NEJM AI", 332 works, DOI 10.1056/aie2601363 em 2026-11-06) — [Source](https://api.crossref.org/journals/2836-9386/works?sort=published&order=desc&rows=2&select=DOI,title,published&mailto=probe@example.com); podcast NEJM AI Grand Rounds (3e) | mensal + online | não (assinatura) |
| Nature Medicine | `https://www.nature.com/nm.rss` | HTML de desafio em 4/4 tentativas — [Source](https://www.nature.com/nm.rss) | Crossref 1546-170X (2163 DOIs correntes) — [Source](https://api.crossref.org/journals/1546-170X/works?sort=published&order=desc&rows=5&mailto=probe@example.com); PubMed `"Nat Med"[jour]`; subject feed [nature.com/subjects/machine-learning.rss](https://www.nature.com/subjects/machine-learning.rss) OK(n=30) na 1ª rodada, HTML depois | semanal | híbrido |
| Lancet Digital Health | `thelancet.com/rssfeed/landig_current.xml` | BLOQ 403 (confirmado) — [Source](https://www.thelancet.com/rssfeed/landig_current.xml) | **[rss.sciencedirect.com/publication/science/25897500](https://rss.sciencedirect.com/publication/science/25897500) OK(n=58; itens sem pubDate — deduplicar por link)**; Crossref 2589-7500 (390 DOIs) — [Source](https://api.crossref.org/journals/2589-7500/works?sort=published&order=desc&rows=5&mailto=probe@example.com); PubMed `"Lancet Digit Health"[jour]` OK; Europe PMC `JOURNAL:"Lancet Digit Health"` 1051 hits — [Source](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=JOURNAL%3A%22Lancet%20Digit%20Health%22&format=json&pageSize=3&sort=P_PDATE_D%20desc) | mensal | sim |
| eClinicalMedicine / eBioMedicine (Lancet) | ScienceDirect | [25895370](https://rss.sciencedirect.com/publication/science/25895370) OK(n=100); [23523964](https://rss.sciencedirect.com/publication/science/23523964) OK(n=40) | — | contínuo | sim |
| JAMIA / JAMIA Open | OUP | BLOQ 403 (Cloudflare) nas páginas; `rss/site_5306/3182.xml` 404 — [Source](https://academic.oup.com/jamia) | Crossref 1527-974X (738 DOIs) — [Source](https://api.crossref.org/journals/1527-974X/works?sort=published&order=desc&rows=5&mailto=probe@example.com); PubMed `"J Am Med Inform Assoc"[jour]` / `"JAMIA Open"[jour]` | mensal | híbrido |
| JAMA Network Open | [jamanetwork.com/rss/site_214/187.xml](https://jamanetwork.com/rss/site_214/187.xml) ("New Online") | OK(n=55, 2026-11-06) — páginas HTML do site dão 403, mas os RSS funcionam | diretório de feeds — [Source](https://jamanetwork.com/pages/rss); Crossref 2574-3805 (7167 DOIs) | diária | sim |
| JAMA Network — coleção "Artificial Intelligence" | [jamanetwork.com/rss/site_9/0_44024.xml](https://jamanetwork.com/rss/site_9/0_44024.xml) | OK(n=4, 2026-11-06: "AI Scribes and Note Closure…", "Updated AI/Machine Learning-Based Medical Devices Cleared Through FDA 510(k)") | outras coleções: Mobile Health & Telemedicine `0_44025.xml`, EHR `0_5620.xml`, Clinical Decision Support `0_5589.xml`, Medical Devices `0_5738.xml` — [Source](https://jamanetwork.com/pages/collections) | contínua (todas as revistas JAMA) | misto |
| Radiology: Artificial Intelligence | `pubs.rsna.org/action/showFeed?…jc=ai` | BLOQ 403 (confirmado) — [Source](https://pubs.rsna.org/action/showFeed?type=etoc&feed=rss&jc=ai) | PubMed `"Radiol Artif Intell"[jour]` → 625 — [Source](https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=%22Radiol+Artif+Intell%22%5Bjour%5D&sort=date&retmax=3&retmode=json); Crossref 2638-6100 (305 DOIs) — [Source](https://api.crossref.org/journals/2638-6100/works?sort=published&order=desc&rows=5&mailto=probe@example.com); Europe PMC `JOURNAL:"Radiol Artif Intell"` OK; podcast RSNA Radiology AI (3e) | bimestral | não |
| JMIR | [jmir.org/feed/atom](https://www.jmir.org/feed/atom) | OK(n=10, 2026-11-06; ex.: "LLMs for Generating Patient Education Materials") | `feed/rss` também OK | diária | sim |
| npj Health Systems | [nature.com/npjhealthsyst.rss](https://www.nature.com/npjhealthsyst.rss) | OK(RSS1 n=8, 2026-11-04) na 1ª rodada; HTML de desafio depois | Crossref (ISSN NV) | contínuo | sim |
| Communications Medicine | [nature.com/commsmed.rss](https://www.nature.com/commsmed.rss) | OK(n=8, 2026-11-06) (mesma ressalva anti-bot) | — | contínuo | sim |
| Nature Biomedical Engineering | [nature.com/natbiomedeng.rss](https://www.nature.com/natbiomedeng.rss) | OK(n=8, 2026-11-03) (mesma ressalva) | Crossref 2157-846X (623 DOIs) | mensal | não |
| Cell Reports Medicine / Patterns | `cell.com/<journal>/current.rss` | BLOQ 403 — [Source](https://www.cell.com/cell-reports-medicine/current.rss) | Crossref 2666-3791 (1310 DOIs); PubMed `"Cell Rep Med"[jour]` | mensal | sim |
| IEEE JBHI | [ieeexplore.ieee.org/rss/TOC6221020.XML](https://ieeexplore.ieee.org/rss/TOC6221020.XML) | OK(n=50, 2026-10-05) | Crossref 2168-2194 (3005 DOIs) | mensal (TOC) | não |
| IEEE Trans. Medical Imaging | [ieeexplore.ieee.org/rss/TOC42.XML](https://ieeexplore.ieee.org/rss/TOC42.XML) | OK(n=21, 2026-10-06) | — | mensal | não |
| J. Biomedical Informatics | [rss.sciencedirect.com/publication/science/15320464](https://rss.sciencedirect.com/publication/science/15320464) | OK(n=19) | Crossref 1532-0464 | contínuo | não |
| Artificial Intelligence in Medicine | [09333657](https://rss.sciencedirect.com/publication/science/09333657) | OK(n=33) | Crossref 0933-3657 | contínuo | não |
| Int. J. Medical Informatics | [13865056](https://rss.sciencedirect.com/publication/science/13865056) | OK(n=47) | — | contínuo | não |
| Medical Image Analysis | [13618415](https://rss.sciencedirect.com/publication/science/13618415) | OK(n=94) | — | contínuo | não |
| Computers in Biology and Medicine | [00104825](https://rss.sciencedirect.com/publication/science/00104825) | OK(n=49) | — | contínuo | híbrido |
| PLOS Digital Health | [journals.plos.org/digitalhealth/feed/atom](https://journals.plos.org/digitalhealth/feed/atom) | OK(n=30, 2026-11-06) | — | semanal | sim |
| Frontiers in Digital Health | [frontiersin.org/journals/digital-health/rss](https://www.frontiersin.org/journals/digital-health/rss) | OK(n=20; sem datas) | — | contínuo | sim |
| BMJ Health & Care Informatics | [informatics.bmj.com/rss/current.xml](https://informatics.bmj.com/rss/current.xml) | OK(n=101) | — | contínuo | sim |
| Science Translational Medicine | Atypon showFeed | BLOQ 403 | Crossref/PubMed | semanal | não |
| Health Affairs (Forefront) | `healthaffairs.org/action/showFeed…`, `/forefront` | BLOQ 403 — [Source](https://www.healthaffairs.org/forefront) | podcast "Health Affairs This Week" `https://feeds.transistor.fm/health-affairs-this-week` (subagente) | — | misto |

Observação sobre Nature: feeds `*.rss` alternaram RSS 1.0 (1ª rodada) e página HTML de desafio (rodadas seguintes) para o mesmo IP/UA — [Source](https://www.nature.com/npjhealthsyst.rss)

**3b. Preprints e APIs bibliográficas**

| Fonte | Mecanismo verificado | Status | Notas |
|---|---|---|---|
| medRxiv API (com categoria) | [api.biorxiv.org/details/medrxiv/2026-11-01/2026-11-07/0/json?category=health_informatics](https://api.biorxiv.org/details/medrxiv/2026-11-01/2026-11-07/0/json?category=health_informatics) | OK: `messages[0].category = "health informatics"`, 27 itens | o parâmetro `category` (slug com `_`) só funciona em `api.biorxiv.org`; em `api.medrxiv.org` é ignorado; forma `/json/<categoria>` → 404. Campos: title, authors, author_corresponding, author_corresponding_institution, doi, date, version, type, license, category, jatsxml, abstract, published, server. Paginação por cursor; `count_new_papers`/`total` nas messages. Categorias vistas: health informatics, radiology and imaging, health systems and quality improvement, emergency medicine, intensive care and critical care medicine |
| medRxiv/bioRxiv RSS por assunto | `connect.medrxiv.org/medrxiv_xml/subject/<slug>` | 404 (health_informatics, radiology_and_imaging, health_systems…; bioRxiv bioinformatics idem) — [Source](https://connect.medrxiv.org/medrxiv_xml/subject/health_informatics) | usar a API |
| arXiv eess.IV | API `cat:eess.IV` OK(n=5, 2026-11-05); [rss.arxiv.org/rss/eess.IV](https://rss.arxiv.org/rss/eess.IV) 200 com 0 itens em fim de semana | OK | adicionar `eess.IV` à lista de categorias da API já mapeada |
| Europe PMC REST | [busca IA∩hospital 1–7 nov](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%22artificial%20intelligence%22%20AND%20(hospital%20OR%20clinical)%20AND%20FIRST_PDATE:%5B2026-11-01%20TO%202026-11-07%5D&format=json&pageSize=25&sort=P_PDATE_D%20desc) OK(n=18) | OK (503 transitório observado numa chamada) | `JOURNAL:"…"` cobre periódicos bloqueados; `sort=P_PDATE_D desc`; `FIRST_PDATE:[a TO b]` |
| OpenAlex topics | [topics?search=artificial intelligence healthcare](https://api.openalex.org/topics?search=artificial%20intelligence%20healthcare&mailto=probe@example.com) → T11396 "Artificial Intelligence in Healthcare" (106.651 works), T11636 "Artificial Intelligence in Healthcare and Education" (112.628), T12422 "Radiomics and Machine Learning in Medical Imaging" (43.960), T10052 "Medical Image Segmentation Techniques" (168.042), T10350 "Electronic Health Records Systems" (179.554) | OK | works por tópico: [filter=primary_topic.id:T11396,type:article,primary_location.source.type:journal,from_publication_date:…](https://api.openalex.org/works?filter=primary_topic.id:T11396,type:article,primary_location.source.type:journal,from_publication_date:2026-10-31,to_publication_date:2026-11-07&sort=publication_date:desc&per-page=3&mailto=probe@example.com) → 77 em 1 semana (sem o filtro de tipo: 141, com ruído de Zenodo/Mendeley Data e datas futuras). Polite pool com `mailto` funcionou sem chave |
| Crossref journals/works | [journals/2836-9386/works?sort=published&order=desc](https://api.crossref.org/journals/2836-9386/works?sort=published&order=desc&rows=5&mailto=probe@example.com) | OK p/ todos os ISSNs testados | ISSNs confirmados: NEJM AI 2836-9386; JAMA Netw Open 2574-3805; Lancet Digit Health 2589-7500; Radiol AI 2638-6100; JAMIA 1527-974X; npj Digit Med 2398-6352; Nat BME 2157-846X; Cell Rep Med 2666-3791; IEEE JBHI 2168-2194; JBI 1532-0464; AI in Medicine 0933-3657; Nat Med 1546-170X — [Source](https://api.crossref.org/journals/2836-9386?mailto=probe@example.com) |
| PubMed E-utilities (já mapeado) | `"NEJM AI"[jour]`, `"Radiol Artif Intell"[jour]`, `"Lancet Digit Health"[jour]` | OK | rota preferencial para os periódicos bloqueados |

**3c. Notícias de IA em saúde** (gratuito salvo indicação)

| Fonte | Feed | Status | Sinal / ruído | Notas |
|---|---|---|---|---|
| STAT — tópico IA | [statnews.com/topic/artificial-intelligence/feed/](https://www.statnews.com/topic/artificial-intelligence/feed/) (o `/tag/…` redireciona) | OK(n=20, 2026-11-06; canal "Artificial Intelligence in Health and Medicine") | alto / baixo | itens pagos prefixados "STAT+:"; [category/health-tech/feed](https://www.statnews.com/category/health-tech/feed/) OK; site-wide OK |
| Healthcare Dive — Health IT | [healthcaredive.com/feeds/topic/health-it/](https://www.healthcaredive.com/feeds/topic/health-it/) | OK(n=20, 2026-11-05 "Mayo Clinic Platform launches AI tool…") | alto / baixo | site-wide [feeds/news/](https://www.healthcaredive.com/feeds/news/) OK |
| MedTech Dive | [medtechdive.com/feeds/news/](https://www.medtechdive.com/feeds/news/) | OK(n=10, 2026-11-06) | médio / médio | regulação FDA de dispositivos |
| MedCity News — IA | [medcitynews.com/category/artificial-intelligence/feed/](https://medcitynews.com/category/artificial-intelligence/feed/) | OK(n=30, 2026-11-06) | médio / médio (op-eds) | tag feed e site-wide OK |
| Fierce Healthcare — AI & ML | [fiercehealthcare.com/rss/AI%20and%20Machine%20Learning/xml](https://www.fiercehealthcare.com/rss/AI%20and%20Machine%20Learning/xml) | OK(n=25, 2026-11-02) | alto / baixo | o slug `/rss/ai-and-machine-learning/xml` devolve canal VAZIO; `Health%20Tech` OK(n=25); pubDate não-RFC822 ("Nov 6, 2026 4:12pm") — [Source](https://www.fiercehealthcare.com/rss/ai-and-machine-learning/xml) |
| Becker's Hospital Review | [beckershospitalreview.com/feed/](https://www.beckershospitalreview.com/feed/) | OK(n=10, 2026-11-07) | médio / alto | feeds de seção (`/healthcare-information-technology/feed/`, `/artificial-intelligence/feed/`, `/rss/`) → 403 "Your browser was…"; fallback [Google News site:](https://news.google.com/rss/search?q=site:beckershospitalreview.com+%22artificial+intelligence%22+when:7d&hl=en-US&gl=US&ceid=US:en) OK(n=100) |
| Healthcare IT News (HIMSS Media) | `/feed`, `/rss`, `/rss.xml`, `/news/feed` | BLOQ 403 — [Source](https://www.healthcareitnews.com/feed) | alto / médio | fallback [Google News site:healthcareitnews.com](https://news.google.com/rss/search?q=site:healthcareitnews.com+when:7d&hl=en-US&gl=US&ceid=US:en) OK(n=25, 2026-11-04) |
| HIMSS | `himss.org/rss.xml`, `/news/feed` | BLOQ 403 | — | podcast HIMSSCast `https://rss.buzzsprout.com/728309.rss` (subagente) |
| AuntMinnie | [auntminnie.com/feed](https://www.auntminnie.com/feed) (`/rss` redireciona) | OK(n=10, 2026-11-06 "Deep-learning model predicts mortality from CTA scans") | alto p/ imagem / médio | página da seção IA → 403; registro gratuito |
| Radiology Business | [radiologybusiness.com/rss.xml](https://radiologybusiness.com/rss.xml) | OK(n=100, 2026-11-06) | médio / médio | `/rss` → 404 |
| Health Imaging / Healthcare Innovation / MobiHealthNews / Digital Health (UK) | `/rss`, `/feed` | BLOQ 403 — [Source](https://healthimaging.com/rss) | — | usar Google News `site:` |
| HealthTech Magazine (CDW) | [healthtechmagazine.net/rss.xml](https://healthtechmagazine.net/rss.xml) | OK(n=10, 2026-11-04) | médio / médio (patrocinado) | |
| HIStalk | [histalk2.com/feed/](https://histalk2.com/feed/) | OK(n=5, "Morning Headlines 11/6/26") | alto p/ Epic/Oracle/fornecedores / médio | subagente |
| Healthcare IT Today | [healthcareittoday.com/feed/](https://www.healthcareittoday.com/feed/) | OK(n=10, 2026-11-07) | médio / médio | subagente |
| Medical Xpress — busca IA | [medicalxpress.com/rss-feed/search/?search=artificial+intelligence](https://medicalxpress.com/rss-feed/search/?search=artificial+intelligence) | OK(n=30, 2026-11-06) | médio / alto (press releases) | |
| Politico Healthcare | [rss.politico.com/healthcare.xml](https://rss.politico.com/healthcare.xml) | OK(n=30, 2026-11-05) | baixo p/ IA / alto | "Future Pulse" só por e-mail (NV) |
| MIT Tech Review AI / Ars Technica AI / The Verge AI | [technologyreview.com/topic/artificial-intelligence/feed](https://www.technologyreview.com/topic/artificial-intelligence/feed) OK; [arstechnica.com/ai/feed/](https://arstechnica.com/ai/feed/) OK; [theverge.com/rss/ai-artificial-intelligence/index.xml](https://www.theverge.com/rss/ai-artificial-intelligence/index.xml) OK | OK (2026-11-06/07) | baixo p/ hospital / alto | |
| Google News RSS (meta-agregador) | EN: [("machine learning" OR "artificial intelligence" OR LLM) (hospital OR clinical OR FDA) when:1d](https://news.google.com/rss/search?q=(%22machine+learning%22+OR+%22artificial+intelligence%22+OR+LLM)+(hospital+OR+clinical+OR+FDA)+when:1d&hl=en-US&gl=US&ceid=US:en) OK(n=29); PT-BR refinada: ["inteligência artificial" (hospital OR Anvisa OR SUS OR "saúde digital") -site:sapo.pt when:2d](https://news.google.com/rss/search?q=%22intelig%C3%AAncia+artificial%22+(hospital+OR+Anvisa+OR+SUS+OR+%22sa%C3%BAde+digital%22)+-site:sapo.pt+when:2d&hl=pt-BR&gl=BR&ceid=BR:pt-419) OK(n=100, 2026-11-06 "Brasil aprova sua política nacional de informação e saúde digital – JOTA") | OK | alto como rede de segurança / médio-alto | sem `-site:sapo.pt` a consulta PT trouxe Portugal/Enem; links são redirects `news.google.com/rss/articles/…`; máx. ~100 itens; operadores `site:`, `when:`, `-` funcionam |

**3d. Newsletters/Substacks de IA em saúde ativas (2025-26)**

| Fonte | Feed | Status / último post | Plataforma | Cadência | Sinal / ruído | Grátis? |
|---|---|---|---|---|---|---|
| Ground Truths (Eric Topol) | [erictopol.substack.com/feed](https://erictopol.substack.com/feed) | OK(n=20, 2026-10-27) | Substack | ~semanal | alto / baixo | sim (+pago) |
| AI Health Uncut (Sergei Polevikov) | [fixhealth.ai/feed](https://www.fixhealth.ai/feed) (`sergeiai.substack.com` → 301) | OK(n=20, 2026-10-29 "Walmart Has Failed at Healthcare 8 Times…"; "Inside OpenEvidence…") | Substack (domínio próprio; publisher "AI Health LLC", subagente) | ~semanal | alto p/ mercado de IA em saúde / baixo-médio | parcial (posts pagos truncados) |
| Doctor Penguin Weekly | [doctorpenguin.substack.com/feed](https://doctorpenguin.substack.com/feed) | OK(n=20, "Week 268" 2026-07-22; depois nada → possivelmente pausado); site antigo [doctorpenguin.com/feed](https://doctorpenguin.com/feed) parado em 2023-07-23 | Substack | mensal em 2026 | alto (papers curados; assinam Emma Chen, Pranav Rajpurkar, Eric Topol — subagente) / baixo | sim |
| The Medical Futurist (B. Meskó) | [medicalfuturist.com/feed](https://medicalfuturist.com/feed) | OK(n=10, 2026-11-04) | WordPress | semanal | médio / médio | sim |
| Healthcare AI Guy | sem RSS (`/feed`, `/rss` 404) — arquivo [healthcareaiguy.com/archive](https://www.healthcareaiguy.com/archive), posts `/p/<slug>` (ex. `/p/healthcare-ai-guy-weekly-11-3`) | HTML OK; "Join 60,000+ readers"; "Healthcare AI Guy Weekly" às terças (2026-09-22 → 2026-11-03) | beehiiv ("Powered by beehiiv") — [Source](https://www.healthcareaiguy.com/) | semanal | alto p/ hospital-vendor / baixo-médio | sim |
| Sensible Medicine | [sensible-med.com/feed](https://www.sensible-med.com/feed) | OK(n=20, 2026-11-07) | Substack | diária | médio / alto p/ IA (sem tag feed) | sim (+pago) |
| Out-Of-Pocket (Nikhil Krishnan) | [outofpocket.health/p/rss.xml](https://www.outofpocket.health/p/rss.xml) | OK(n=100, 2026-11-07) | Webflow (subagente) | semanal | médio / médio | sim |
| Second Opinion (Christina Farr) | [secondopinion.media/rss/](https://www.secondopinion.media/rss/) | OK(n=15, 2026-11-07 "CMS wants to pay for AI-enabled primary care") | Ghost (subagente) | quase diária | alto / médio | sim (+pago) |
| Hospitalogy (Blake Madden) | [hospitalogy.com/feed](https://hospitalogy.com/feed) | OK(n=24, 2026-11-05) | beehiiv | 2-3/sem | médio / alto p/ IA | sim |
| Health Tech Nerds / Healthcare Huddle | sem RSS (subagente) | HTML | beehiiv | diária / semanal | médio | sim |
| DR GPT (Harvey Castro MD) | [harveycastromd.substack.com/feed](https://harveycastromd.substack.com/feed) | OK(n=20, 2026-11-03) | Substack | várias/sem | médio / alto | sim |
| CHAI (Coalition for Health AI) | sem feed (`chai.org/feed/` 404); notícias HTML (subagente: 2026-10-01 AI Intake Playbook; 2026-09-21 OVERT) | HTML | — | 1-2/mês | alto p/ governança / baixo | sim |
| Mayo Clinic Platform blog | `/blog/feed/` | BLOQ 403 (Akamai) | — | — | — | — |
| Rock Health (Rock Weekly) | `rockhealth.com/feed/` → 403; `rockhealthcapital.com/feed/` → 403 — [Source](https://rockhealthcapital.com/feed/) | BLOQ | WordPress | relatórios trimestrais (Q3 2026, subagente) | alto / baixo | sim |
| Mortas/paradas (subagente) | aihandoff.substack.com (2025-05), "DoctorAI Digest" (2026-01), "AI Rx" (2025-12), healthcareainews.beehiiv.com (2024-01); AIMed `ai-med.io/feed/` 404 | — | — | — | — | — |

**3e. Podcasts (feed via iTunes Search API `feedUrl`, verificados)**

| Podcast | Feed | Status | Cadência / sinal |
|---|---|---|---|
| NEJM AI Grand Rounds (Raj Manrai & Andy Beam) | [ai-podcast.nejm.org/feed.xml](https://ai-podcast.nejm.org/feed.xml) (espelho [feed.podbean.com/nejm-ai/feed.xml](https://feed.podbean.com/nejm-ai/feed.xml)) | OK(48 eps, 2026-10-21 "Abridge's Dr. Michal Nedoszytko…") | mensal; sinal máximo |
| RSNA Radiology AI Podcast | [rss.libsyn.com/shows/260105/destinations/1973264.xml](https://rss.libsyn.com/shows/260105/destinations/1973264.xml) | OK(64 eps, 2026-10-30 "The Promise and Pitfalls of Medical AI") | irregular; alto p/ imagem |
| Ground Truths (podcast) | [api.substack.com/feed/podcast/587835/s/119690.rss](https://api.substack.com/feed/podcast/587835/s/119690.rss) | OK(98 eps, 2026-10-27) | 2-3/mês |
| AI in Healthcare — Stanford Medicine | [audioboom.com/channels/5167325.rss](https://audioboom.com/channels/5167325.rss) | OK(16 eps, 2026-09-28) | mensal; alto |
| Faces of Digital Health (Tjasa Zajc) | [feeds.megaphone.fm/faces-of-digital-health](https://feeds.megaphone.fm/faces-of-digital-health) | OK(408 eps, 2026-11-06) | semanal; médio |
| Fixing Healthcare (Pearl & Corr) | `https://www.fixinghealthcarepodcast.com/feed/podcast/` | OK(299 eps, 2026-11-02; subagente) | semanal; médio |
| Sensible Medicine (podcast) | `https://api.substack.com/feed/podcast/1000397.rss` | OK(149 eps, 2026-11-04; iTunes) | semanal; ruído alto p/ IA |
| The AI Health Podcast (Rajpurkar et al.) | `https://anchor.fm/s/353b22e0/podcast/rss` | 41 eps, último 2022-07-26 (parado) — [Source](https://itunes.apple.com/search?media=podcast&limit=3&term=The%20AI%20Health%20Podcast) | arquivo |
| Latent Space / Last Week in AI | `https://podcast.latent.space/feed.xml` (294 eps); `https://rss.art19.com/last-week-in-ai` (299 eps, 2026-10-19) | OK (iTunes) | genéricos |
| AI in Medicine — curated summaries (Mike Rawson) | [ai-in-medicine-podcast.vercel.app/feed.xml](https://ai-in-medicine-podcast.vercel.app/feed.xml) | OK(157 eps, 2026-11-07) | diário; provavelmente gerado por IA (qualidade NV) |
| Outros verificados pelo subagente | Claims Denied (Hospitalogy) `feeds.megaphone.fm/OWEWK5446771877`; The Signal Room `rss.buzzsprout.com/2550733.rss`; AI-ready Healthcare `anchor.fm/s/54a80ee0/podcast/rss`; Raising Health (a16z) `feeds.simplecast.com/BXDamaKF`; Lifers (Second Opinion) `feeds.megaphone.fm/secondopinion`; Becker's Health IT `feeds.blubrry.com/feeds/1461261.xml`; HTN Radio `feeds.transistor.fm/health-tech-nerds-radio`; Emerj AI in Healthcare `rss.libsyn.com/shows/511038/destinations/4384188.xml` | OK (subagente) | médios |
| Brasil: IA med — Inteligência Artificial na Medicina (Fabiano Novaes Barcellos Filho) | [anchor.fm/s/1044f94d0/podcast/rss](https://anchor.fm/s/1044f94d0/podcast/rss) | OK(81 eps, 2026-11-07 "IA.med da semana #4 – IA analisa mamografias…") | semanal; alto p/ PT-BR |
| Brasil: Podcast Saúde Digital (Dr. Lorenzo Tomé) | [rss.libsyn.com/shows/125156/destinations/744258.xml](https://rss.libsyn.com/shows/125156/destinations/744258.xml) → `feeds.transistor.fm/podcast-saude-digital` | OK(405 eps, 2026-10-27) | semanal; médio |

**3f. YouTube (feed `https://www.youtube.com/feeds/videos.xml?channel_id=<ID>`)**
- Stanford AIMI `UCiHlZ1osvJ_1C8K5MCnJp7w` OK(n=15, 2026-10-03 "AIMI Symposium + 2026 Summit Highlights") — [Source](https://www.youtube.com/feeds/videos.xml?channel_id=UCiHlZ1osvJ_1C8K5MCnJp7w); Stanford MedAI `UCOkkljs06NPPkjNysCdQV4w` OK(2026-10-10 "MedAI #166") — [Source](https://www.youtube.com/feeds/videos.xml?channel_id=UCOkkljs06NPPkjNysCdQV4w); NEJM Group `UCqO3GxVYutcugyknCWdAcUA` OK(2026-11-06; ruído alto) — [Source](https://www.youtube.com/feeds/videos.xml?channel_id=UCqO3GxVYutcugyknCWdAcUA)
- Subagente (verificados por curl): Stanford HAI `UC-EnprmCZ3OXyAoG7vjVNCA`; DeepLearning.AI `UCcIXc5mJsHVYTZR1maL5l9w`; Andrej Karpathy `UCXUPKJO5MZQN11PqgIvyuvQ` (último 2025-02-27); Yannic Kilcher `UCZHmQk67mSJgfCCTn7xBfew`; Two Minute Papers `UCbfYPyITQ-7l4upoX8nvctg`; AI Explained `UCNJ1Ymd5yFuUPtn21xtRbbw`; Microsoft Research `UCCb9_Kn8F_Opb3UCGm-lILQ`; Google DeepMind `UCP7jMXSY2xbc3KCAE0MHQ-A`; Google Research `UCT-VzthVAM_4ohDdKa-BbXA`; Google Health `UCzqcfJjCO5C1zUmnxFRGvzg`; Harvard DBMI `UCn6jbvnRUST3nyD06HAGO-g`; Eric Topol não tem canal. Cuidado: o primeiro `"channelId"` do HTML pode ser de canal relacionado — usar `"externalId"`.

**3g. Indústria / VC / relatórios**

| Fonte | Mecanismo | Status | Cadência | Grátis? |
|---|---|---|---|---|
| Rock Health | scrape `rockhealthcapital.com/insights/` (feeds 403) | BLOQ | trimestral (funding) + anual | sim |
| a16z (todas as verticais, filtrar Bio+Health) | [a16z.substack.com/feed](https://a16z.substack.com/feed) → `a16z.news/feed` | OK(n=20, 2026-11-07) | diária | sim |
| Bessemer Atlas | HTML sem RSS — [Source](https://www.bvp.com/atlas) | HTML | irregular; "State of Health AI" NV | sim |
| CB Insights Research | [cbinsights.com/research/feed/](https://www.cbinsights.com/research/feed/) | OK(n=25, 2026-11-06) | diária (multi-setor) | teasers; relatórios pagos |
| Signify Research (IA em imagem) | [signifyresearch.net/feed/](https://www.signifyresearch.net/feed/) | OK(n=10, 2026-09-22; baixo volume) | mensal | insights grátis; relatórios pagos |
| State of AI Report (Benaich) | HTML [stateof.ai](https://www.stateof.ai/) (2026 = 9ª edição, subagente); newsletter Air Street [press.airstreet.com/feed](https://press.airstreet.com/feed) OK(2026-10-30 "State of AI 2026: My conversation with Matt Turck") | OK | anual (out) + mensal | sim |
| Stanford AI Index | HTML [hai.stanford.edu/ai-index/2026-ai-index-report](https://hai.stanford.edu/ai-index/2026-ai-index-report) (abril/2026, subagente); HAI sem RSS | HTML | anual | sim |
| Epoch AI | [epoch.ai/atom.xml](https://epoch.ai/atom.xml) | OK(n=50, 2026-11-06) (`/feed`, `/rss.xml` 404) | semanal | sim |
| PHTI (Peterson) | [phti.org/feed/](https://www.phti.org/feed/) | OK(n=10, 2026-10-14 "Achieving AI's Promise for Health Outcomes…") | mensal | sim |
| HealthAI (agência global) | [healthai.agency/feed/](https://healthai.agency/feed/) | OK(n=10, 2026-10-21) | mensal | sim |
| Galen Growth | [galengrowth.com/rss.xml](https://www.galengrowth.com/rss.xml) | OK(n=50, 2026-10-26) | semanal | sim |
| KLAS / ECRI / McKinsey / Deloitte / BCG | sem RSS temático (subagente); McKinsey site-wide `mckinsey.com/insights/rss` | NV | — | KLAS pago |

**3h. Regulatório / catálogos**

| Fonte | URL / mecanismo | Verificação | Cadência | Download máquina |
|---|---|---|---|---|
| FDA — List of AI-Enabled Medical Devices | nova URL [fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/list-artificial-intelligence-enabled-medical-devices](https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/list-artificial-intelligence-enabled-medical-devices) (a URL antiga `/software-medical-device-samd/…` dá 301) | página: "This list will continue to be updated periodically"; método "identified primarily based on the use of AI-related terms in the summary descriptions"; FDA "will explore methods to identify and tag medical devices that incorporate foundation models" (LLMs/multimodais); contato digitalhealth@fda.hhs.gov; sem RSS/GovDelivery — [Source](https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/list-artificial-intelligence-enabled-medical-devices) | "periodicamente" (sem datas na página) | CSV [fda.gov/media/178541/download?attachment](https://www.fda.gov/media/178541/download?attachment) → 1.614 dispositivos; colunas Date of Final Decision, Submission Number, Device, Company, Panel (Lead), Primary Product Code; decisão mais recente 06/29/2026; por ano: 2023=226, 2024=235, 2025=335, 2026=181 (até jun); Excel [media/178540](https://www.fda.gov/media/178540/download?attachment); XML [media/178565](https://www.fda.gov/media/178565/download?attachment) |
| openFDA 510(k) | [api.fda.gov/device/510k.json?search=decision_date:[20261001+TO+20261107]](https://api.fda.gov/device/510k.json?search=decision_date:[20261001+TO+20261107]&limit=5) OK; [product_code:QAS](https://api.fda.gov/device/510k.json?search=product_code:QAS&sort=decision_date:desc&limit=3) OK(n=3) | OK | diária | JSON; cruzar `Primary Product Code` da lista (ex. QIH) |
| FDA RSS | diretório [fda.gov/about-fda/contact-fda/subscribe-podcasts-and-news-feeds](https://www.fda.gov/about-fda/contact-fda/subscribe-podcasts-and-news-feeds) (a URL antiga `rss-feeds-fda` → 404); Press Releases [rss-feeds/press-releases/rss.xml](https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml) OK(n=20, 2026-11-05); MedWatch [rss-feeds/medwatch/rss.xml](https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medwatch/rss.xml) OK(n=20, 2026-11-03) | OK | diária | sem feed específico de CDRH/dispositivos/guidance/comitês |
| FDA Digital Health Advisory Committee | [fda.gov/advisory-committees/committees-and-meeting-materials/digital-health-advisory-committee](https://www.fda.gov/advisory-committees/committees-and-meeting-materials/digital-health-advisory-committee) ("advises the Commissioner… on issues related to digital health technologies", incl. AI/ML, cibersegurança, PGHD); materiais passados `/advisory-committees/digital-health-advisory-committee/past-meeting-materials-digital-health-advisory-committee`; calendário [advisory-committee-calendar](https://www.fda.gov/advisory-committees/advisory-committee-calendar) | OK (página não lista datas 2025-26) | ad hoc | HTML |
| Federal Register API | [documents.rss?conditions[term]="artificial intelligence" "medical device"&order=newest](https://www.federalregister.gov/api/v1/documents.rss?conditions%5Bterm%5D=%22artificial%20intelligence%22%20%22medical%20device%22&order=newest) OK(n=4: 2026-11-05 "Classification of the Digital Cervical Cytology…", 2026-10-28 "ONC Deregulatory Actions…"); versão JSON OK | OK | diária | RSS/JSON |
| EU AI Act (site) | [artificialintelligenceact.eu/feed/](https://artificialintelligenceact.eu/feed/) OK(n=27, 2026-08-07 "AI Therapy under the EU AI Act"); cronograma: entrada em vigor 1 ago 2024; proibições 2 fev 2025; GPAI 2 ago 2025; **alto risco Anexo III: 2 dez 2027; alto risco Anexo I (componentes de segurança de produtos, p.ex. dispositivos sob MDR/IVDR): 2 ago 2028** — a página não menciona "Digital Omnibus" — [Source](https://artificialintelligenceact.eu/implementation-timeline/) | OK | mensal | RSS |
| MDCG (MDR/IVDR) | MDCG 2025-6 "FAQ on Interplay between the MDR & IVDR and the Artificial Intelligence Act (AIA)", jun/2025, [PDF](https://health.ec.europa.eu/document/download/b78a17d7-e3cd-4943-851d-e02a2f22bbb4_en?filename=mdcg_2025-6_en.pdf); MDCG 2025-4 (MDSW apps em plataformas online, jun/2025); MDCG 2019-11 rev.1 (qualificação/classificação de software, jun/2025); MDCG 2020-1 (avaliação clínica de MDSW); MDCG 2019-16 rev.1 (cibersegurança) — página sem RSS — [Source](https://health.ec.europa.eu/medical-devices-sector/new-regulations/guidance-mdcg-endorsed-documents-and-other-guidance_en) | OK | irregular | HTML (scrape da lista) |
| EMA | `ema.europa.eu/en/news/rss.xml` → 404 | NV | — | — |
| ANVISA — notícias | `gov.br/anvisa/pt-br/assuntos/noticias-anvisa/RSS` (e variantes `/rss`, `/2025/RSS`, `/2026/RSS`, raiz `/RSS`) → 404 — [Source](https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/RSS) | sem RSS | — | scrape HTML de [noticias-anvisa](https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa) |
| ANVISA — Consultas (produtos registrados) | API do SPA `consultas.anvisa.gov.br/api/consulta/produtos` → 403 `{"codigo":"turnstile_invalido","mensagem":"Token do Cloudflare Turnstile não informado."}` mesmo com `Authorization: Guest` — [Source](https://consultas.anvisa.gov.br/api/consulta/produtos?count=5&page=1&filter%5BnomeProduto%5D=software) | BLOQ (Turnstile) | — | inviável sem browser |
| ANVISA — Dados Abertos (produtos para saúde) | diretório [dados.anvisa.gov.br/dados/](https://dados.anvisa.gov.br/dados/): `TA_PRODUTO_SAUDE_SITE.csv` (27,7 MB, 2026-10-13), `TA_PRODUTO_SAUDE_MODELO.csv` (1,2 GB, 2026-10-13), `CICLO_ANALISE_PETICOES_PRODUTO_SAUDE(CORRELATOS).CSV` (338 MB, 2026-11-06), `CICLO_ANALISE_PETICOES_ANDAMENTO_PRODUTO_SAUDE(CORRELATOS).CSV` (2026-11-06), `FILA_ANALISE_DISPOSITIVOS MÉDICOS.csv` (2026-10-13), `DADOS_ABERTOS_TECNOVIGILANCIA.csv` (2026-10-13), dicionários `Documentacao_e_Dicionario_de_Dados_PRODUTO_SAUDE.pdf` | OK (listagem lida) | ~mensal (TA_*), diária/semanal (CICLO_*) pelas datas | CSV (sem coluna "SaMD/IA" conhecida: filtrar por nome técnico/classe) |
| ANVISA — página Dispositivos Médicos | [gov.br/anvisa/pt-br/assuntos/produtosparasaude](https://www.gov.br/anvisa/pt-br/assuntos/produtosparasaude) ("Modificado em 20/08/2026"; sem links a SaMD/IA; links "Dados Abertos" e "Notícias") | OK | — | HTML |
| Ministério da Saúde — notícias RSS | [gov.br/saude/pt-br/assuntos/noticias/RSS](https://www.gov.br/saude/pt-br/assuntos/noticias/RSS) responde RSS 1.0 mas último item 2022-05-04 (obsoleto) | parado | — | — |
| ANPD | `/assuntos/noticias/RSS` → 404 | sem RSS | — | — |
| PL 2338/2023 (marco da IA) | Futuro da Saúde 2026-11-05: "Marco de IA pode avançar ainda em 2026, enquanto dúvidas regulatórias persistem" — [Source](https://futurodasaude.com.br/feed/) | indireto | — | — |
| NHS England | [england.nhs.uk/feed/](https://www.england.nhs.uk/feed/) OK(n=10, 2026-11-05); `transform.england.nhs.uk/ai-lab/` → falha de DNS/conexão — [Source](https://transform.england.nhs.uk/ai-lab/); AI & Digital Regulations Service [digitalregulations.innovation.nhs.uk](https://www.digitalregulations.innovation.nhs.uk/) HTML sem feed | parcial | — | — |
| NICE | `/rss`, `/news/feed`, `/feeds`, `/guidance/published?…type=hte` → 403 — [Source](https://www.nice.org.uk/rss) | BLOQ | — | — |
| MHRA | [gov.uk/government/organisations/medicines-and-healthcare-products-regulatory-agency.atom](https://www.gov.uk/government/organisations/medicines-and-healthcare-products-regulatory-agency.atom) OK(n=20, 2026-11-06); busca Atom por palavra-chave [search/all.atom?keywords=artificial+intelligence+medical+device](https://www.gov.uk/search/all.atom?keywords=artificial+intelligence+medical+device&order=updated-newest) responde mas com ruído (itens não relacionados) | OK | diária | Atom |
| WHO | [who.int/rss-feeds/news-english.xml](https://www.who.int/rss-feeds/news-english.xml) OK(n=83, 2026-10-10; ordem/mistura de itens de 2020) | OK | baixo volume | RSS |
| IMDRF | `imdrf.org` timeout | NV | — | — |

**3i. Brasil**

| Fonte | Feed | Status / último item | Tipo | Relevância IA∩saúde | Ruído |
|---|---|---|---|---|---|
| Futuro da Saúde | [futurodasaude.com.br/feed/](https://futurodasaude.com.br/feed/) | OK(n=10, 2026-11-05; "Marco de IA pode avançar…") | notícias/política | média-alta | médio |
| Saúde Digital News | [saudedigitalnews.com.br/feed/](https://saudedigitalnews.com.br/feed/) | OK(n=20, 2026-11-06) | notícias saúde digital | média | alto (press releases) |
| Medicina S/A | [medicinasa.com.br/feed/](https://medicinasa.com.br/feed/) | OK(n=10, 2026-11-06) | gestão hospitalar | baixa-média | alto |
| Saúde Business | [saudebusiness.com/feed/](https://www.saudebusiness.com/feed/) | OK(n=10, 2026-11-06) | executivo de saúde | baixa-média | alto |
| Setor Saúde | [setorsaude.com.br/feed/](https://setorsaude.com.br/feed/) | OK(n=10, 2026-11-06) | notícias | baixa | alto |
| Portal Hospitais Brasil | [portalhospitaisbrasil.com.br/feed/](https://portalhospitaisbrasil.com.br/feed/) | OK(n=10, 2026-11-06) | hospitalar | baixa | alto |
| Healthcare Management | [healthcaremanagement.com.br/feed/](https://healthcaremanagement.com.br/feed/) → `healthcare.grupomidia.com/feed/` | OK(n=3, 2026-10-30) | gestão | baixa | alto |
| SBIS | [sbis.org.br/feed/](https://sbis.org.br/feed/) | OK(n=10, 2026-10-06 "Quando a IA deixa de responder e começa a agir…") | sociedade científica | alta | baixo (baixo volume) |
| JHI — Journal of Health Informatics (SBIS) | [OJS rss2](https://jhi.sbis.org.br/index.php/jhi-sbis/gateway/plugin/WebFeedGatewayPlugin/rss2) | OK(n=19; "Brazilian Dataset for Retinal Lesion Analysis: A Deep Learning Diagnostic Pipeline", 2026-01-18) | periódico OA | alta | baixo |
| Saúde Digital Brasil (associação) | [saudedigitalbrasil.com.br/feed/](https://saudedigitalbrasil.com.br/feed/) | OK(n=10, último 2025-12-16 — parado há 11 meses) | associação | média | baixo |
| InovaHC (HC-FMUSP) | [inovahc.com.br/feed/](https://inovahc.com.br/feed/) | OK(n=10, último 2026-01-09 — parado) | hub de inovação | média | baixo |
| Abstartups | [abstartups.com.br/feed/](https://abstartups.com.br/feed/) | OK(n=10, 2026-10-06; avisos institucionais) | associação | baixa | alto |
| Anahp | [anahp.com.br/feed/](https://www.anahp.com.br/feed/) | OK(n=10, 2026-10-06; conteúdo p/ pacientes) | associação | baixa | alto |
| IDOR | `idor.org/feed/`, `/noticias/feed/` → 404; site HTML sem feed — [Source](https://www.idor.org/feed/) | sem feed | pesquisa | alta (potencial) | — |
| Einstein / Agência Einstein | `einstein.br` → 403; `agencia.einstein.br` → falha de conexão — [Source](https://agencia.einstein.br/feed/) | BLOQ/indisponível | — | alta (ex.: parceria Einstein–Mayo p/ startups de IA, via Google News PT 2026-11-07) | — |
| Sírio-Libanês / Dasa / Rede D'Or São Luiz | HTML sem `<link>` de feed — [Source](https://dasa.com.br/) | sem feed | — | — | — |
| Hospitalar (feira) | `/feed/`, `/pt/feed/` → 404 | sem feed | evento | — | — |
| Distrito | `/feed/`, `/blog/feed/` → 404 | sem feed (relatórios gated, NV) | relatórios | média | — |
| PEBMED/Afya | `/feed/` → 404 | sem feed | — | — | — |
| CFM | [portal.cfm.org.br/feed/](https://portal.cfm.org.br/feed/) 1 item de 2024-01-25 (morto) | parado | regulador | alta (resoluções) | — |
| Agência FAPESP | [agencia.fapesp.br/rss/](https://agencia.fapesp.br/rss/) responde RSS com 0 itens | VAZIO | ciência | média | — |
| Jornal da USP / Startupi / Mobile Time | [jornal.usp.br/feed/](https://jornal.usp.br/feed/) OK; [startupi.com.br/feed/](https://startupi.com.br/feed/) OK; [mobiletime.com.br/feed/](https://www.mobiletime.com.br/feed/) OK (2026-11-06/07) | OK | genéricos | baixa | alto |
| Google News PT-BR (consulta refinada) | ver 3c | OK(n=100) | meta | alta (rede de segurança BR) | médio-alto |
| Podcasts BR | IA med (semanal, 2026-11-07); Podcast Saúde Digital (2026-10-27) — ver 3e | OK | podcast | alta / média | baixo |

### Inferences
- A rota "PubMed `[jour]` + Crossref `journals/<ISSN>/works` + ScienceDirect RSS" elimina a dependência de RSS de Atypon/OUP/Cell/Lancet; o ScienceDirect RSS é a solução direta para o Lancet Digital Health bloqueado.
- A coleção "Artificial Intelligence" da JAMA Network é o feed de maior densidade IA∩clínica entre os que funcionam sem bloqueio (poucos itens/dia, todos relevantes).
- Para Nature (nm.rss, natmachintell.rss, npjdigitalmed.rss), reduzir a frequência (1 fetch/feed/dia, com intervalo e ETag) e manter fallback Crossref/PubMed; o pipeline atual pode estar sendo servido com HTML de desafio sem perceber.
- No Brasil não há feed nativo de IA∩saúde com volume: o melhor sinal vem de SBIS/JHI (baixo volume), Futuro da Saúde (política/regulação) e da consulta Google News PT-BR; IDOR/Einstein/Sírio/Dasa exigem scrape ou monitoramento via Google News.
- A cronologia do site do AI Act (2 dez 2027 / 2 ago 2028) difere das datas originais do regulamento (2 ago 2026 / 2 ago 2027), o que sugere que um adiamento foi incorporado; como a página não cita o "Digital Omnibus", tratar como NV até confirmar no Jornal Oficial.

### Gaps
- Datas/temas das reuniões do FDA DHAC em 2025-26 (página do comitê não lista; só "Past Meeting Materials").
- ANVISA: guias/consultas sobre IA em SaMD (2025-26), ISSN do npj Health Systems, status oficial do PL 2338/2023, resoluções CFM sobre IA — não verificáveis sem busca; ANVISA Consultas exige token Turnstile (sem API pública).
- Newsletters brasileiras de IA∩saúde (Substack/LinkedIn) não localizadas sem busca; só dois podcasts foram confirmados via iTunes.
- "Health AI Tracker", "The Health AI Report", "AI Health Index", "Medical AI Weekly", "Healthcare AI Digest": existência não confirmada (subagente).
- Nature: causa exata do desafio (F5/Shape vs. rate limit) e se o `httpx` do pipeline o contorna.

## Q4 — Feeds de releases de modelos, datasets e ferramentas; blogs de saúde das big techs

### Takeaway
A Hugging Face Hub API com `filter=medical` (ou `radiology`) e `sort=lastModified|createdAt|trendingScore` funciona sem chave e é a melhor fonte de modelos/datasets médicos; MONAI/nnU-Net/TorchIO/pydicom têm Atom no GitHub e RSS no PyPI; PhysioNet tem RSS de notícias (não de datasets); ClinicalTrials.gov v2 tem API e RSS (parâmetros `term`/`intr` + `dateField`); Kaggle exige credencial. Entre big techs, só Google Health (Keyword), AWS (categorias healthcare), NVIDIA (site-wide), Microsoft Research (site-wide) e OpenAI (news RSS) têm feed; Anthropic, Epic, Oracle Health e Dragon Copilot não.

### Cited Findings

| Fonte | URL/API verificada | Status | Cadência | Notas |
|---|---|---|---|---|
| HF Hub — modelos médicos | [api/models?filter=medical&sort=lastModified&direction=-1&limit=20](https://huggingface.co/api/models?filter=medical&sort=lastModified&direction=-1&limit=20) OK; [sort=trendingScore](https://huggingface.co/api/models?filter=medical&sort=trendingScore&direction=-1&limit=20) OK (top: google/medgemma-1.5-4b-it, Prior-Labs/tabpfn_3_5, google/medgemma-27b-it, google/medsiglip-448); [filter=radiology](https://huggingface.co/api/models?filter=radiology&sort=lastModified&direction=-1&limit=20) OK; `search=medical` OK; `sort=trending` → 400 | OK | contínuo | campos: id, pipeline_tag, tags, likes, downloads, lastModified, createdAt, trendingScore |
| HF Hub — datasets médicos | [api/datasets?filter=medical&sort=lastModified&direction=-1&limit=20](https://huggingface.co/api/datasets?filter=medical&sort=lastModified&direction=-1&limit=20) OK (ex.: KeremTT/cmmd-mammography 2026-11-07); [sort=trendingScore](https://huggingface.co/api/datasets?filter=medical&sort=trendingScore&direction=-1&limit=20) OK; filtros `task_categories:image-segmentation` funcionam | OK | contínuo | |
| HF trending (geral) | [api/trending?type=model](https://huggingface.co/api/trending?type=model&limit=3) OK (`recentlyTrending[]`) | OK | — | |
| Open Medical-LLM Leaderboard | [spaces/openlifescienceai/open_medical_llm_leaderboard](https://huggingface.co/spaces/openlifescienceai/open_medical_llm_leaderboard) HTML (Space) | HTML | — | status de atualização NV |
| MONAI | [github.com/Project-MONAI/MONAI/releases.atom](https://github.com/Project-MONAI/MONAI/releases.atom) OK(2026-09-27); [PyPI monai releases](https://pypi.org/rss/project/monai/releases.xml) OK(2026-09-27); [MONAILabel releases.atom](https://github.com/Project-MONAI/MONAILabel/releases.atom) último 2024-11-25; [monai-deploy-app-sdk](https://github.com/Project-MONAI/monai-deploy-app-sdk/releases.atom) 2026-06-13 | OK | trimestral | |
| nnU-Net / TorchIO / pydicom | [nnUNet releases.atom](https://github.com/MIC-DKFZ/nnUNet/releases.atom) OK(2026-07-01); [PyPI nnunetv2](https://pypi.org/rss/project/nnunetv2/releases.xml) OK; [PyPI torchio](https://pypi.org/rss/project/torchio/releases.xml) OK(2026-07-20); [PyPI pydicom](https://pypi.org/rss/project/pydicom/releases.xml) OK(2026-03-20) | OK | irregular | padrão `https://pypi.org/rss/project/<pkg>/releases.xml` confirmado |
| PhysioNet | [physionet.org/feed.xml](https://physionet.org/feed.xml) "PhysioNet News" OK(n=100, 2026-10-28 "New citation lists on PhysioNet"); `/rss/` 404; [/content/](https://physionet.org/content/) HTML sem feed | OK (notícias) | mensal | lista de novos datasets exige scrape de `/content/` (NV) |
| Kaggle | [api/v1/competitions/list?search=medical](https://www.kaggle.com/api/v1/competitions/list?search=medical) → 401 | precisa de credencial (`KAGGLE_USERNAME/KEY`) | — | |
| ClinicalTrials.gov v2 — API | [api/v2/studies?query.term="artificial intelligence"&sort=LastUpdatePostDate:desc&pageSize=5&format=json&fields=NCTId,BriefTitle,LastUpdatePostDate](https://clinicaltrials.gov/api/v2/studies?query.term=%22artificial%20intelligence%22&sort=LastUpdatePostDate:desc&pageSize=3&format=json&fields=NCTId,BriefTitle,LastUpdatePostDate) OK (ex.: NCT05890716 "AI-powered ECG Analysis…", 2026-11-06) | OK | diária | |
| ClinicalTrials.gov — RSS | [api/rss?term="artificial intelligence"&dateField=LastUpdatePostDate](https://clinicaltrials.gov/api/rss?term=%22artificial+intelligence%22&dateField=LastUpdatePostDate) OK; [intr=…&dateField=StudyFirstPostDate](https://clinicaltrials.gov/api/rss?intr=%22artificial+intelligence%22&dateField=StudyFirstPostDate) OK; `query.term` no RSS → 400 "Invalid prefix in parameter name" | OK | diária | |
| TCIA | [cancerimagingarchive.net/feed/](https://www.cancerimagingarchive.net/feed/) OK(n=10, 2026-10-01 "…MAMA-MIA Challenge") | OK | mensal | |
| Grand Challenge | [grand-challenge.org/api/v1/challenges/](https://grand-challenge.org/api/v1/challenges/) OK(JSON n=100) | OK | contínuo | lista de desafios (MICCAI etc.) |
| Stanford AIMI datasets | [aimi.stanford.edu/data](https://aimi.stanford.edu/shared-datasets) HTML sem feed | HTML | — | |
| NVIDIA healthcare | site-wide [blogs.nvidia.com/feed/](https://blogs.nvidia.com/feed/) OK; [developer.nvidia.com/blog/feed](https://developer.nvidia.com/blog/feed) OK(Atom n=100); [category/healthcare/feed/](https://developer.nvidia.com/blog/category/healthcare/feed/) Atom VAZIO (3 testes) | parcial | semanal | filtrar por "Clara|Holoscan|BioNeMo|healthcare" |
| Microsoft Health Futures / Dragon Copilot | lab page [research/lab/microsoft-health-futures/](https://www.microsoft.com/en-us/research/lab/microsoft-health-futures/) HTML (só expõe o feed site-wide); feed `group/health-futures/feed/` entrega MSR Asia (errado); `industry/blog/healthcare/feed/` 404; `microsoft-cloud/blog/industry-healthcare/feed/` VAZIO (subagente) | parcial | — | Dragon Copilot: sem feed → Google News `"Dragon Copilot" when:7d` |
| Google Health / Google Research | [blog.google/innovation-and-ai/technology/health/rss/](https://blog.google/innovation-and-ai/technology/health/rss/) OK(n=20, 2026-11-04; 2026-10-29 "Equipping healthcare professionals with practical AI skills"); Google Research RSS já mapeado (2026-11-05 "Detecting signs of hypertension using wearable sensors") | OK | semanal | alto sinal |
| Amazon / AWS | [AWS for Industries — Healthcare](https://aws.amazon.com/blogs/industries/category/industries/healthcare/feed/) OK(n=10, 2026-10-27; "Agentic AI on Connect Health"); [AWS ML — Healthcare](https://aws.amazon.com/blogs/machine-learning/category/industries/healthcare/feed/) OK(n=20, 2026-09-16; "Amazon Nova Act is now HIPAA eligible"); Amazon Science OK | OK | mensal | HealthScribe aparece aqui |
| Epic / Oracle Health | sem feed (ver Q2) | — | — | HIStalk + Google News |
| Anthropic — saúde | sem RSS; páginas: "Advancing Claude in healthcare and the life sciences" [anthropic.com/news/healthcare-life-sciences](https://www.anthropic.com/news/healthcare-life-sciences) (2026-01-11, subagente), "Claude for Life Sciences" (2025-10-20, subagente); release notes RSS (Q2) | HTML | — | `/healthcare`, `/solutions/healthcare`, `/solutions/life-sciences` → 404 |
| OpenAI — saúde | RSS site-wide (Q2); páginas (datas pelo byline, subagente via curl): "Introducing ChatGPT Health" 2026-01-07, "OpenAI for Healthcare" [openai.com/index/openai-for-healthcare/](https://openai.com/index/openai-for-healthcare/) 2026-01-08, HealthBench [openai.com/index/healthbench/](https://openai.com/index/healthbench/) 2025-05-12 | OK (HTML) | — | páginas dão 403 ao WebFetch, 200 ao curl/urllib com UA |
| Fornecedores clínicos | [hippocraticai.com/feed/](https://hippocraticai.com/feed/) OK(2026-10-31 "Polaris 6"); [aidoc.com/feed/](https://www.aidoc.com/feed/) OK(2026-11-02); [viz.ai/feed](https://www.viz.ai/feed) OK(2026-11-04; posts de engenharia misturados); Tempus 429; Abridge/Nabla/Ambience sem RSS (subagente) | parcial | mensal | marketing (ruído médio) |

### Inferences
- `filter=medical` + `sort=createdAt` (novos repositórios) e `sort=trendingScore` (relevância) cobrem "novos modelos médicos" e "o que está em alta"; combinar com `daily_papers` já mapeado.
- O feed de categoria healthcare do NVIDIA Technical Blog é instável (vazio em 3/3 testes aqui, com itens no subagente): ingerir o Atom site-wide e filtrar por palavras-chave.
- ClinicalTrials RSS é a forma mais barata de detectar novos ensaios com IA (sem paginação/cursor).

### Gaps
- Lista de novos datasets do PhysioNet e da Stanford AIMI: sem feed (scrape NV).
- Kaggle: necessidade de credencial impede verificação de competições médicas ativas.
- Cadência real de atualização da lista FDA (datas de releases 2025-26) não está na página.

## Q5 — Sobreposição, priorização (Tiers) e as 10–15 fontes a manter

### Takeaway
Para "só o que é aplicável em hospital + IA de fronteira", bastam ~14 fontes: 5 trilhos de literatura (NEJM AI + Lancet Digital Health + Nature Medicine/npj Digital Medicine + JAMA AI collection + JAMIA via PubMed/Crossref/ScienceDirect; medRxiv API filtrada), 3 de notícias (STAT IA, Healthcare Dive Health-IT, MedCity IA ou Fierce AI&ML), 2 regulatórias (CSV FDA + openFDA; Federal Register/MDCG por scrape), 2 de laboratórios (Google Health RSS + OpenAI/Claude release notes, além dos já mapeados), 1 de ferramentas (HF `filter=medical` + MONAI) e 1 rede de segurança (Google News EN/PT-BR); newsletters de IA genérica e portais brasileiros de gestão ficam em Tier 3 com filtro por palavra-chave.

### Cited Findings

**Sobreposição (quem duplica quem)**
- Digests diários de IA: TLDR AI ≈ The Rundown ≈ The Neuron ≈ Ben's Bites ≈ AlphaSignal cobrem os mesmos lançamentos dos feeds primários (OpenAI news, Google Keyword AI, DeepMind, Mistral, HF) — ex.: os três primeiros itens de TLDR AI e The Neuron em 2026-11-06 citam "GPT-6 Cyber" — [Source](https://tldr.tech/api/rss/ai), [Source](https://www.theneuron.ai/feed/)
- Resumos semanais: The Batch ≈ Last Week in AI ≈ Import AI (este com mais pesquisa/política) — [Source](https://lastweekin.ai/feed), [Source](https://importai.substack.com/feed)
- Literatura médica: STAT IA, MedCity IA, Medical Xpress e Google News re-reportam os mesmos artigos de NEJM AI/Nature Medicine/JAMA; Doctor Penguin (pausado) e Ground Truths comentam o mesmo conjunto — [Source](https://www.statnews.com/topic/artificial-intelligence/feed/), [Source](https://medicalxpress.com/rss-feed/search/?search=artificial+intelligence)
- Dispositivos aprovados: CSV da FDA (fonte primária) ≈ item "Updated AI/Machine Learning-Based Medical Devices Cleared Through FDA 510(k)" na coleção JAMA AI ≈ notícias de AuntMinnie/Radiology Business — [Source](https://jamanetwork.com/rss/site_9/0_44024.xml)
- Negócios hospitalares EUA: Becker's ≈ Healthcare Dive ≈ Fierce ≈ MedCity ≈ HIStalk ≈ Healthcare IT News (bloqueado) — todos cobrem os mesmos anúncios (ex.: Mayo Clinic Platform em Healthcare Dive 2026-11-05) — [Source](https://www.healthcaredive.com/feeds/topic/health-it/)
- Imagem: AuntMinnie ≈ Radiology Business ≈ Health Imaging (bloqueado) ≈ Signify — [Source](https://www.auntminnie.com/feed), [Source](https://radiologybusiness.com/rss.xml)
- Brasil: Futuro da Saúde ≈ Medicina S/A ≈ Saúde Business ≈ Setor Saúde ≈ Portal Hospitais Brasil ≈ Saúde Digital News (mesmas pautas de gestão; IA é minoria) — [Source](https://medicinasa.com.br/feed/), [Source](https://setorsaude.com.br/feed/)
- Google News (EN e PT) sobrepõe tudo acima (meta-agregador) — usar com deduplicação por URL canônica — [Source](https://news.google.com/rss/search?q=site:healthcareitnews.com+when:7d&hl=en-US&gl=US&ceid=US:en)

**Tier 1 — manter (alto sinal, aplicável a hospital, ingestão verificada)**
1. NEJM AI via PubMed `"NEJM AI"[jour]` + Crossref 2836-9386 — [Source](https://api.crossref.org/journals/2836-9386/works?sort=published&order=desc&rows=5&mailto=probe@example.com)
2. The Lancet Digital Health via ScienceDirect RSS 25897500 (+ eClinicalMedicine 25895370) — [Source](https://rss.sciencedirect.com/publication/science/25897500)
3. Nature Medicine + npj Digital Medicine (já mapeado) + npj Health Systems via Crossref/PubMed com fallback (Nature serve desafio anti-bot) — [Source](https://api.crossref.org/journals/1546-170X/works?sort=published&order=desc&rows=5&mailto=probe@example.com)
4. JAMA Network coleção "Artificial Intelligence" RSS + JAMA Network Open "New Online" — [Source](https://jamanetwork.com/rss/site_9/0_44024.xml)
5. JAMIA + Radiology: AI via PubMed `[jour]`/Crossref (bloqueados em RSS) — [Source](https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=%22Radiol+Artif+Intell%22%5Bjour%5D&sort=date&retmax=3&retmode=json)
6. medRxiv API `category=health_informatics` e `radiology_and_imaging` (+ arXiv eess.IV na API já mapeada) — [Source](https://api.biorxiv.org/details/medrxiv/2026-11-01/2026-11-07/0/json?category=health_informatics)
7. STAT — tópico IA (filtrar "STAT+:") — [Source](https://www.statnews.com/topic/artificial-intelligence/feed/)
8. Healthcare Dive — Health IT (+ MedTech Dive para regulação) — [Source](https://www.healthcaredive.com/feeds/topic/health-it/)
9. FDA: CSV da lista de dispositivos com IA (diff diário) + openFDA 510(k) + MedWatch RSS — [Source](https://www.fda.gov/media/178541/download?attachment)
10. Google Health (Keyword) RSS + OpenAI news RSS + Claude release notes RSS (filtro "health|clinical|medical") — [Source](https://blog.google/innovation-and-ai/technology/health/rss/)
11. Hugging Face Hub API `filter=medical` (modelos e datasets; `createdAt` + `trendingScore`) + MONAI releases.atom — [Source](https://huggingface.co/api/models?filter=medical&sort=trendingScore&direction=-1&limit=20)
12. Google News RSS: consulta EN (hospital/clinical/FDA) + consulta PT-BR refinada — [Source](https://news.google.com/rss/search?q=%22intelig%C3%AAncia+artificial%22+(hospital+OR+Anvisa+OR+SUS+OR+%22sa%C3%BAde+digital%22)+-site:sapo.pt+when:2d&hl=pt-BR&gl=BR&ceid=BR:pt-419)

**Tier 2 — vale manter com filtro/baixa frequência**
- MedCity IA e Fierce "AI and Machine Learning" (se quiser 2º/3º feed de mercado) — [Source](https://www.fiercehealthcare.com/rss/AI%20and%20Machine%20Learning/xml)
- AuntMinnie (imagem) — [Source](https://www.auntminnie.com/feed)
- AI Health Uncut, Ground Truths, Healthcare AI Guy (scrape), Second Opinion — [Source](https://www.fixhealth.ai/feed)
- NEJM AI Grand Rounds + RSNA Radiology AI Podcast + Stanford AIMI/MedAI (YouTube) — [Source](https://ai-podcast.nejm.org/feed.xml)
- ClinicalTrials.gov RSS (ensaios com IA) — [Source](https://clinicaltrials.gov/api/rss?term=%22artificial+intelligence%22&dateField=LastUpdatePostDate)
- JMIR, PLOS Digital Health, JBI/AI in Medicine (ScienceDirect), IEEE JBHI — volume alto, filtrar por LLM/hospital — [Source](https://www.jmir.org/feed/atom)
- Regulação: Federal Register RSS, EU AI Act feed + scrape MDCG, MHRA Atom, PHTI, HealthAI — [Source](https://www.federalregister.gov/api/v1/documents.rss?conditions%5Bterm%5D=%22artificial%20intelligence%22%20%22medical%20device%22&order=newest)
- Brasil: Futuro da Saúde + Saúde Digital News (filtro "IA|inteligência artificial"), SBIS + JHI, podcast IA med; ANVISA Dados Abertos (diff mensal de TA_PRODUTO_SAUDE_SITE.csv) — [Source](https://sbis.org.br/feed/)
- AWS healthcare (duas categorias), Microsoft Research (site-wide), NVIDIA (site-wide + filtro) — [Source](https://aws.amazon.com/blogs/industries/category/industries/healthcare/feed/)
- Import AI e TLDR AI (um único digest geral) — [Source](https://tldr.tech/api/rss/ai)

**Tier 3 — baixa prioridade ou substituível**
- AlphaSignal, The Batch, Rundown, Neuron, Ben's Bites, The Sequence, Latent Space, Zvi, Exponential View, One Useful Thing (IA genérica; já coberta pelos feeds primários) — [Source](https://www.therundown.ai/feed)
- Runway (news/research/changelog; vídeo generativo) — [Source](https://runway.com/news)
- MIT TR / Ars / Verge / HN / lobste.rs / Reddit (ruído alto; Reddit com rate-limit) — [Source](https://lobste.rs/t/ai.rss)
- Medical Futurist, Sensible Medicine, Hospitalogy, Out-Of-Pocket, DR GPT, Fixing Healthcare, Faces of Digital Health — [Source](https://www.sensible-med.com/feed)
- CB Insights, Signify, Galen Growth, Epoch, Air Street (relatórios/mercado) — [Source](https://www.cbinsights.com/research/feed/)
- Portais brasileiros de gestão (Medicina S/A, Saúde Business, Setor Saúde, Portal Hospitais Brasil, Healthcare Management), Abstartups, Anahp, Jornal da USP, Startupi, Mobile Time — [Source](https://www.saudebusiness.com/feed/)
- Parados/mortos: The Gradient (2026-02), AI Tidbits (2026-04), Doctor Penguin (2026-07), Saúde Digital Brasil (2025-12), InovaHC (2026-01), CFM feed (2024), The AI Health Podcast (2022), Papers with Code (redirect) — [Source](https://thegradient.pub/rss/)
- Bloqueados (usar Google News `site:` se necessário): Healthcare IT News, HIMSS, Health Affairs, MobiHealthNews, Health Imaging, Healthcare Innovation, Digital Health UK, Becker's (seções), Mayo Clinic Platform, Rock Health, NICE, ANVISA Consultas — [Source](https://www.healthcareitnews.com/feed)

### Inferences
- Com os 12 trilhos Tier 1 o pipeline cobre literatura (primária), regulação (primária), produto de laboratório (primário) e mercado (2 feeds) com ruído baixo; cada fonte adicional de Tier 2/3 traz principalmente duplicatas, então vale deduplicar por DOI/URL canônica e por similaridade de título.
- Para o contexto Rede D'Or/Brasil, o maior ganho marginal é a consulta Google News PT-BR + SBIS/JHI + diff do CSV da ANVISA, já que nenhuma instituição brasileira (IDOR, Einstein, Sírio, Dasa, D'Or) publica feed.
- Detalhes de implementação que importam: UA de browser; 1 req/feed/dia com intervalo para Nature e Reddit; parse tolerante de datas (Fierce usa "Nov 6, 2026 4:12pm"; ScienceDirect não envia pubDate); resolver redirects de Google News; `mailto=` em OpenAlex/Crossref; tratar 503 transitório do Europe PMC.

### Gaps
- A priorização usa sinal/ruído observado em 1 dia de feeds; a taxa real de itens IA∩hospital por fonte deve ser medida após 2-4 semanas de ingestão.
- Fontes brasileiras de alto sinal (newsletters/Substacks de IA em saúde, hubs de inovação hospitalar) permanecem sub-cobertas por falta de busca web nesta sessão.
