# sotawhat 2.0

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An insight engine for AI/ML ∩ medicine: multi-source collection, LLM triage and a
daily digest (Telegram, e-mail, Markdown/HTML), growing into a knowledge graph
with its own local interface. Interactive paper search still works.

Original SOTAWHAT background: [blog post](https://huyenchip.com/2018/10/04/sotawhat.html).

## What's new in 2.0

- **Multiple sources** behind a single interface: arXiv (official API),
  Semantic Scholar, Hugging Face Daily Papers, PubMed, and generic RSS/Atom feeds.
- **No more `nltk`/`six`/`pyspellchecker`/`win-unicode-console`** — the
  summarizer is now pure Python. The only runtime deps are `httpx` and
  `feedparser`. No `punkt` download, no SSL/encoding workarounds.

## 3.0: insight engine

sotawhat is becoming an insight engine for AI/ML ∩ medicine. The design is in
`docs/sdd/2026-11-07-insight-engine-sdd.md` and the phase plans are in `docs/superpowers/plans/`.
Phase P0 adds:

- `sotawhat run daily [--no-notify] [--limit N]` collects every
  profile, normalizes and de-duplicates items into `data/insight.db` (SQLite),
  tracks the health of every source and feed, and sends a run summary to
  Telegram. A feed that returns an HTML anti-bot page now counts as an error
  instead of silently yielding 0 items.
- `sotawhat doctor [--llm]` checks `.env`, the OpenRouter key and its spend
  limit, and every configured model: still in the catalog, Zero-Data-Retention
  endpoints available, reasoning level accepted, not about to expire. It also
  checks the Telegram bot, the last run and this month's LLM spend. `--llm`
  makes one tiny structured call per primary model, for well under one cent.
- The LLMs are Chinese open-weight models (DeepSeek, Xiaomi MiMo, Z.ai GLM,
  Moonshot Kimi) reached through OpenRouter, ZDR endpoints only. See
  `sotawhat/llm/` and SDD §6.6.

Phase P1 adds the triage and the real digest:

- Every new item goes through stage A without LLM: mute filters (`config/mute.yaml`), same-story
  dedup on near-identical titles, local embeddings (EmbeddingGemma-300m via `fastembed`, CPU,
  downloaded once to `data/models/`) and a novelty score. Then the LLM rubric
  (`config/rubric.yaml`, prompt `sotawhat/llm/prompts/triage_v1.md`) scores frontier AI,
  medical applicability and actionability with strict JSON, inside the daily budget.
- The digest has two ranked sections, "IA ∩ Saúde" (up to 10) and "Fronteira de IA" (up to 5:
  strong frontier AI even without a health link), each item with 👍 👎 🧪 buttons, plus a one-line
  radar. It goes to Telegram and to `data/digests/YYYY-MM-DD.md` and `.html`.
  Nothing relevant and nothing broken means nothing is sent.
- With `DIGEST_EMAIL_TO` set, the same digest also goes by e-mail (SMTP; with Gmail it reuses
  `GMAIL_ADDRESS` and the app password in `GMAIL_APP_PASSWORD`, never the account password).
- `sotawhat feedback pull|listen` records the votes; after 100 votes a profile gets its own
  classifier (logistic regression over the embeddings), which then decides what reaches the LLM.
- `sotawhat eval golden draft|import` builds a golden set that you label by editing a Markdown
  file, and `sotawhat eval models [--apply]` runs the bake-off of triage models against it
  and can put the winner first in `config/llm.yaml`.

Phase P3 adds the knowledge graph and its own interface (no Obsidian):

- After the digest, `run daily` extracts entities (techniques, models, datasets, organizations,
  products, problems, regulations), relations and figures from every approved item with strict JSON
  (`sotawhat/llm/prompts/extract_v1.md`). It resolves them into one entity graph in SQLite: aliases in
  `config/aliases.yaml`, a cheap LLM judge for look-alike names (never across version numbers) and an
  audit trail of merges. The triage categories become graph nodes too. `sotawhat graph extract
  [--limit N]` does the same on demand, e.g. for the items approved before P3.
- `sotawhat serve` opens the interface at http://127.0.0.1:8765: the graph (sigma.js + graphology,
  shipped in the package), filters by period, type and mentions, search, entity and item panels, and
  👍 👎 🧪 votes that count like the Telegram ones. It reads SQLite, so it works with Docker closed.
  `scripts\schedule_daily.ps1 -Web` starts it at every logon.
- Neo4j mirror (optional): set `NEO4J_PASSWORD`, run `sotawhat graph up` (opens Docker Desktop and
  starts `compose.yaml`, ports only on 127.0.0.1) and `sotawhat graph sync [--rebuild]`. The daily run
  keeps it in sync. Neo4j Browser: http://127.0.0.1:7474 (user `neo4j`).
- MCP: `.mcp.json` registers `sotawhat-graph` (`sotawhat serve-mcp`) for Claude Code, with `search`,
  `entity`, `neighbors`, `recent_items`, `graph_stats` and read-only `cypher`.
- `sotawhat graph status` prints the counts; `sotawhat graph export` writes JSON + CSV to `data/exports/`.

Phase P2 adds the new sources (each one a channel fetched once a day with its own cap; the triage decides):

- Health: JAMA AI, STAT AI, MONAI releases, The Lancet Digital Health, Healthcare Dive Health IT, Google News
  (EN and PT-BR), medRxiv (API, health informatics, radiology, ICU, ED…), JAMIA, Radiology: AI and npj Health
  Systems via Crossref, and the FDA list of AI-enabled devices (a baseline first, then every new submission).
- Frontier AI: AlphaSignal and OpenAI News (RSS), The Batch (sitemap, one item per story), new GitHub
  repositories by topic (with the start of the README), trending and medical Hugging Face models and datasets,
  and the official MCP registry.
- Newsletters from Gmail (`GMAIL_QUERY`, read only over IMAP with the app password): each e-mail is split into
  stories by the LLM, and their links are resolved and cleaned of tracking. Create a Gmail filter that labels
  the newsletters without RSS as `newsletters/ai`.
- The triage prompt (v2) knows the new item kinds: repo, model, dataset, mcp_server, newsletter_item and
  regulation. `sotawhat doctor` checks the GitHub and Hugging Face tokens and the Gmail query.

Phase P4 adds the weekly intelligence and the idea engine (SDD §6.9, §8):

- `sotawhat run weekly` (Sundays at 20:00 with `scripts\schedule_daily.ps1 -Weekly`) syncs the Neo4j mirror
  when it answers, then computes what rose this week (7 days against the 28 before), the communities of the
  graph (Louvain over co-mentions and relations, labeled by the LLM) and its gaps: recent techniques never
  linked to frequent problems, bridges between communities that barely touch, and distant pairs. A
  meta-review turns your idea decisions, with their reasons, into at most 10 rules for the generators.
  Then it runs the idea engine and sends the report.
- The idea engine, economic mode: 12 technique × problem candidates from the gaps (10% with no graph
  context, as a control), 3 lenses each (tech-push, JTBD, SCAMPER, TRIZ, cross-sector analogy, 2029
  scenario) plus the contrarian lens on a quarter of them, with generators of rotating model families. Then
  dedup (a cheap judge per technique × problem pair decides which drafts are the same product and which
  repeat an earlier or rejected idea; pairs used in the last 4 weeks yield to new ones), a six-role critique
  by a model of another family, prior
  art by layers (the graph, OpenAlex, Semantic Scholar, GitHub and, with `EXA_API_KEY`, Exa; patents stay
  "not verified"), a novelty matrix per facet and the rubric of SDD §8.4 by two judges, hard gates (only
  when both judges agree; a gate raised by one judge is shown as disputed), a
  portfolio with at most 2 ideas per niche and at least one contrarian bet, and a dossier (90-day pilot,
  evidence plan, SaMD class, LGPD basis) for every finalist. `--modo completo` widens every step. The run
  stops gracefully at `SOTAWHAT_LLM_BUDGET_USD_RUN_WEEKLY`.
- `sotawhat ideate [--tema "UTI"] [--n 4] [--modo economico|completo] [--no-notify]` runs the engine alone,
  on demand: `--n` finalists out of `--n` candidates.
- The report goes to `data/weekly/` (Markdown and HTML), to Telegram (one message per idea, with
  👍 explorar · 👎 · 🧪 testar · 🗄️ engavetar) and by e-mail. Every idea, kept or discarded, stays in the
  ledger with its reason.
- The interface gains two tabs. Ideias shows the cards with the rubric, novelty, prior art, critiques,
  dossier, the graph facts the generator saw and the votes (👎 asks for a reason; 🛠️ construí marks what
  you built). Tendências shows what rose, the labeled map, the gaps and the meta-review rules. The MCP
  server adds `trends`, `gaps`, `list_ideas` and `idea`.

Phase P5 adds Instagram and the manual capture (SDD §7.2, §7.7), with no Meta app and no Instagram login:

- Send any link to the Telegram bot (in the Instagram app: Share → Telegram → the bot). The bot confirms it,
  and the next daily run turns it into an item: Instagram posts and reels through Apify, any other link with
  the page title and description. What you send skips the mute filter and the classifier and is never
  rejected (the radar at worst); a post the scan had already stored becomes yours and is triaged again.
- Daily scan of the public accounts in `config/instagram_accounts.yaml` through the Apify Instagram scraper
  (`APIFY_TOKEN`; the Free plan gives US$ 5/month and a post costs US$ 0.0027). Each run has a charge cap
  (`INSTAGRAM_MAX_USD_RUN`) and starts where the last one stopped. "ia" accounts feed the general profile,
  "saude" accounts the medical one.
- To build the list, export "Seguidores e seguindo" as JSON in the Accounts Center and run
  `sotawhat instagram import following.json [--max 50] [--limit N] --yes`. Without `--yes` it only shows the
  plan and the Apify cost. It fetches the profiles, sorts them into IA, saúde or fora with a cheap model, and
  writes the YAML for you to review; importing again keeps your choices.
- The images of every post go to the vision model (`vision` task, ≤ 3 per carousel, 800 px) and the
  description joins the caption. Reels are transcribed on the CPU if you install `uv pip install -e ".[audio]"`.
- The triage prompt is v3 (it knows `instagram_post`), and `sotawhat doctor` shows the Apify usage of the
  month and the accounts in the scan.

Phase P6 hardens it and measures the SDD goals:

- `sotawhat backup` copies `data/insight.db` to `data/backups/` (one consistent file, integrity checked, the
  newest 8 kept); `run weekly` makes one every Sunday. `sotawhat backup --restore FILE --yes` restores a copy
  and keeps the current database next to it. The Neo4j mirror needs no dump: `sotawhat graph sync --rebuild`.
- `sotawhat eval report [--send]` writes `data/reports/AAAA-MM-DD-metas.md` with the goals G1–G4 (daily
  runs, digest sizes and precision by your votes, extraction precision and query latency, ideas per week
  and the share you want to explore), each rate with its count. `run weekly` writes it every week and sends
  the table to Telegram on the first Sunday of the month. `sotawhat eval triage` and `sotawhat eval ideas`
  show the parts.
- `sotawhat eval extract draft` writes a sample of 40 extracted items to `tests/evals/extract/`; uncheck the
  wrong entities and relations and run `sotawhat eval extract import` to get the precision.
- `sotawhat calibrate [--apply]` proposes the triage cut-offs (from 100 votes; they can only go up, since
  only delivered items have votes) and the idea rubric weights (from 30 decided finalists). Nothing changes
  without `--apply`.
- `sotawhat repair cjk` rewrites old triage texts that still had Chinese characters (from the model used
  before the P1 bake-off), keeping every decision.
- The interface gains the Hoje tab: the latest digest with its votes and the recent runs.

After P6, newsletters by RSS (2026-11-09):

- `config/newsletters.yaml` lists the newsletters read every day: frontier AI (Import AI, Interconnects,
  Latent Space, Understanding AI, One Useful Thing, Normal Technology, Epoch AI, DAIR.AI papers, Guide to AI,
  Lilian Weng) and AI ∩ health (Ground Truths, AI Health Uncut, Second Opinion, Doctor Penguin, The Medical
  Futurist, Health API Guy, Hospitalogy, Out-Of-Pocket, Palpate Health AI, MedCity AI, AuntMinnie, Futuro da
  Saúde, Saúde Business, Medicina S/A). Repetitive daily digests are listed but disabled.
- `kind: post` makes every post one item; `kind: digest` splits each issue into its stories with the LLM
  (the same `segment` task as the Gmail newsletters), each story keeping its source link. A run takes at most
  2 entries per newsletter from the last 4 days and never reads an entry twice. The health newsletters are
  filtered by AI terms in English and Portuguese before the triage.
- Full text: when a feed carries only an excerpt (less than 1,500 characters: MedCity, Out-Of-Pocket, Lilian
  Weng), the article page is read and its main text (trafilatura) replaces the excerpt, before the health
  filter. A post keeps up to 8,000 characters, what the triage reads. Pages that block robots keep the excerpt.
- `sotawhat newsletters add <address> --profile ia|saude [--kind digest]` finds the feed (a Substack name
  such as `importai`, a site, a topic page or a feed URL) and appends it to the file. `sotawhat doctor`
  checks every enabled feed.
- The Gmail source skips e-mails from senders that have their own source (The Batch, AlphaSignal), so a
  filter that also labels them never doubles the stories. The scheduled daily and weekly runs use
  `pythonw.exe`: with no console window, closing a window can no longer kill a run.

Animated lessons (aulas 3D, F0/F1, 2026-11-09; plan in `docs/superpowers/plans/2026-11-09-aulas-3d-f0-f1.md`,
research in `docs/research/reports/Aulas didáticas animadas em 3D.md`):

- `sotawhat lessons setup` installs the tools in `data/tools/lessons`:
  - a uv venv with packages at least two weeks old: Manim 0.22.0, Playwright 1.64.1, matplotlib, Piper and FFmpeg;
  - Chromium;
  - the Brazilian Portuguese Piper voices (faber, cadu, jeff; CC0 data).
- `sotawhat lessons make --tema "Atenção no Transformer" [--entidade 105 …]` (or `--auto`, the strongest weekly
  trend without a lesson) makes a 3–6 minute lesson:
  1. The source pack is built from the graph.
  2. An LLM writes the storyboard, which goes through the G2 lint and the G1 fact gate (one revision round).
  3. Each sentence is narrated, and its length times its animation.
  4. An LLM writes each scene as code: Manim for the abstract, three.js only for the spatial.
  5. The code passes a policy (no files, network, processes or DOM) and is rendered on the PC. A failure goes back
     for repair, escalates to Kimi K3.1 Pro after two tries and, as a last resort, becomes a slide.
  6. The MP4 is assembled under 48 MB, with subtitles drawn in the picture.
- The video goes to Telegram with:
  - the quiz;
  - your review buttons (✅ / ⚠️);
  - the comparison with the NotebookLM Video Overview generated from `fontes.md`.

  The daily run sends the re-quiz two days later.
- The Aulas tab of the interface shows the videos, the 3D scenes as interactive pages (timeline, narration, free
  orbit), the storyboard, the gates and the review checklist.
- Other commands:
  - `lessons resume N` continues a lesson where it stopped;
  - `lessons rerender N --voz …` re-narrates without the LLM;
  - `lessons voices` sends a blind voice test to Telegram (your vote picks the voice);
  - `lessons send N`, `lessons pack N` and `lessons list` deliver a lesson, export its pack and list the lessons.
- Voice: Piper by default (local). Google Chirp 3 HD (`google:pt-BR-Chirp3-HD-Charon`) needs `GOOGLE_TTS_API_KEY`.
  A lesson made from a ledger idea should keep a local voice.
- After the pilot feedback (arrows out of place, overlaps, artificial pauses):
  - Scenes draw arrows with `connect(a, b)`, which follows its ends and disappears with them.
  - The layout check rejects:
    - arrows left behind after their object left;
    - arrows that arrive before their target;
    - loose arrows and arrows that cross objects;
    - partial overlaps between objects;
    - LaTeX typed into a Text;
    - more than 16 things on stage.
  - A vision model reviews the frame at the end of every sentence (gate G4). A serious defect goes back with the
    frames to a model that sees images.
  - The narration is written for the ear: short sentences, at most one comma, no colons or parentheses.
  - Before synthesis the text is rewritten for speech: acronyms spelled out, symbols written as words.
  - Pauses are shaped: 0.24 s at commas, 0.32 s between sentences and 0.75 s at the end of a scene.
  - Lesson calls never pay more than US$ 1/2.5 per million tokens.
- HyperFrames prototype (2026-11-10, after the second feedback: arrows blinking and misaligned, a bland look, a
  robotic voice): `sotawhat lessons hf 4 [--aula N] [--sem-envio] [--refazer storyboard,voz]` remakes lesson 4's
  plan with another engine.
  - The LLM no longer draws. It writes a storyboard (`sotawhat/lessons/storyboard.py`): for each scene it picks a
    kit template (`graph`, `bars`, `vectors3d`, `patches`), fills it with data and lists the actions of each
    sentence, each with the word that triggers it.
  - The kit (`sotawhat/lessons/motion_kit`: HTML, CSS, GSAP; three.js for the 3D template) owns layout, links,
    motion, type and colour. A link is routed from border to border and fades with its ends.
  - HyperFrames (HeyGen, Apache-2.0) renders it: headless Chrome plus FFmpeg, deterministic. It is pinned in
    `data/tools/hyperframes` with versions at least two weeks old, and its telemetry is off:
    `npm install --before=2026-10-26T20:00:00Z --ignore-scripts --save-exact hyperframes@0.8.206 gsap@3.15.0
    three@0.186.1 katex@0.19.1 @fontsource/fraunces@5.3.0 @fontsource/manrope@5.3.0 lucide-static@1.61.0
    @ffprobe-installer/win32-x64@5.1.0`.
  - The narration is ElevenLabs (`ELEVENLABS_API_KEY`, model `eleven_v4`, voice Klaus): one request per scene,
    with the time of every word. Those times drive the captions and the cue words. Every scene is cached, so a
    rerun spends no credits.

To set it up, copy `.env.example` to `.env` and fill in at least `OPENROUTER_API_KEY`,
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Then schedule the runs with
`powershell -ExecutionPolicy Bypass -File scripts\schedule_daily.ps1 [-Listener] [-Web] [-Weekly]`.

Obsidian is no longer used (SDD §9): nothing reads or writes a vault, and the 2.0 `digest` and
`backfill-links` commands are gone.

## Install

Requires Python 3.11+.

```bash
git clone [HTTPS or SSH link to this repo]
cd sotawhat
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"   # Windows
# source .venv/bin/activate && pip install -e ".[dev]"   # macOS/Linux
```

This installs the `sotawhat` console command.

## Usage

### Search (interactive)

Classic form — keyword(s) followed by an optional result count (default 5):

```bash
sotawhat perplexity 10
sotawhat language model 10
```

Equivalent explicit subcommand:

```bash
sotawhat search "language model" 10
```

Results are grouped by source. Each entry shows the title (author + date), a
summarized extract of the abstract (preferring sentences with metrics or
state-of-the-art claims), and a link.

Works best with keywords that are a model, dataset, task, or metric
(e.g. `transformer`, `imagenet`, `machine translation`, `BLEU`).

### Profiles

- `geral` — general ML/AI (arXiv, Semantic Scholar, HF Daily Papers, lab/blog RSS).
- `medico` — AI∩medicine only. PubMed queries are AND-ed with an AI clause
  (MeSH "Artificial Intelligence" + recent ML/LLM phrases), and every result
  (PubMed, arXiv q-bio/CV/LG, medical-journal RSS and Crossref) must mention an AI/ML term to
  be kept. A single source failing (rate limit, network) is isolated — the run continues with
  the other sources.

## Development

```bash
.\.venv\Scripts\python -m pytest -q
```

Source adapters are tested against recorded fixtures in `tests/fixtures/`, so
the suite runs without network access.
