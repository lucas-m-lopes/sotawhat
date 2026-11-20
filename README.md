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
- The votes go both ways between Telegram and the interface (2026-11-20). A vote in the interface (an item, an idea
  or a tool of the radar) moves the ✅ on the Telegram buttons of every message that carries it. A vote in Telegram
  lights the same button in the open page within 15 s, or at once when the page comes back to the front. The store
  is the one record; each side only redraws (`pipeline/feedback.py`: `mirror_vote`, `vote_changes`, `/api/votes`).
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
- `sotawhat serve` opens the interface at http://127.0.0.1:8765: the graph (in 3D since 2026-11-20, with a 3D | 2D
  switch that flattens the same scene onto a plane: three.js + graphology, shipped in the package), filters by period, type and mentions, search (accents optional; an exact
  name or alias such as "EHR" comes first, the triage categories after the entities), entity and item
  panels, and 👍 👎 🧪 votes that count like the Telegram ones. It reads SQLite, so it works with Docker
  closed. `scripts\schedule_daily.ps1 -Web` starts it at every logon; the task keeps the Python code it
  started with, so after an update restart it (`Stop-ScheduledTask sotawhat-web; Start-ScheduledTask
  sotawhat-web`).
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
  (`APIFY_TOKEN`; the Free plan gives US$ 5/month and a post costs US$ 0.0027). `INSTAGRAM_MAX_USD_RUN` caps the
  whole day: the "ia" and "saude" scans share it by their enabled accounts (at least US$ 0.02 each), and the
  account order turns every day, so a scan cut by the cap does not always leave out the same accounts. Each scan
  starts where the last one stopped. "ia" accounts feed the general profile, "saude" accounts the medical one.
- To build the list, export "Seguidores e seguindo" as JSON in the Accounts Center and run
  `sotawhat instagram import following.json [--max 50] [--limit N] --yes`. Without `--yes` it only shows the
  plan and the Apify cost. It fetches the profiles, sorts them into IA, saúde or fora with a cheap model, and
  writes the YAML for you to review; importing again keeps your choices.
- The images of every post go to the vision model (`vision` task, ≤ 3 per carousel, 800 px) and the
  description joins the caption. Reels are transcribed on the CPU if you install `uv pip install -e ".[audio]"`.
- The triage prompt is v3 (it knows `instagram_post`), and `sotawhat doctor` shows the Apify usage of the
  month and the accounts in the scan.
- **Your saved posts instead of the accounts (2026-11-20, `sotawhat/sources/instagram_saved.py`).** The scan of 51
  accounts brought 212 posts in nine days and 1 was approved, so it can be turned off (`INSTAGRAM_ACCOUNT_SCAN=false`)
  in favour of what you save. There is no API for the saved posts and no login is used: you ask for the export in
  the Accounts Center (Download your information → only "Saved items", all time, JSON) and drop the zip in
  `data/instagram/salvos/`.
  - `sotawhat instagram salvos [ZIP]` shows the inventory: posts, accounts, years, collections, what is already
    stored and what reading the rest costs on Apify. Nothing is spent.
  - With `--yes [--max-usd 1.0] [--limit N] [--colecao NAME]` it reads the posts by URL, newest saves first, 40 per
    Apify run, up to the cap (`INSTAGRAM_SAVED_MAX_USD`). Before any image is paid for, a cheap model drops by the
    caption what is neither AI nor medicine (task `saved`, 25 posts a call; in doubt it keeps). The rest is
    described (images; reels too with the audio extra) and imported as `instagram:salvos` items.
  - These items are triaged in the command's own run: the backlog enters the graph and the questions, never a
    digest (the daily triage leaves them alone). A sweep that stops resumes where it stopped, and nothing is paid
    twice (`data/state/instagram_saved.json`).
  - Afterwards, save what matters in a collection (`INSTAGRAM_SAVED_COLLECTION`, "IA/Med" by default) and drop a new
    export in the folder every week or so: the daily run reads that collection's new posts as `manual:instagram`
    items, like the links sent to the bot. They skip the filters and come first in the digest.

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
- `sotawhat repair names [--dry-run]` fixes technique and problem names that the singular rule before 2026-11-10
  cut ("AI bias" → "AI bia", "CAMS" → "CAM", "mixture of experts" → "mixture of expert"). It reads the raw names
  kept in the extractions, moves names and keys to the current rule (only the head noun goes singular; acronyms,
  symbols and words such as "bias" keep their s) and reports a key that already belongs to another entity instead
  of merging it.
- `sotawhat repair entities [--dry-run]` applies `config/entity_fixes.yaml`, with merges ("regulation: Model
  Context Protocol" into the technique, "model: GPT4" into "GPT-4"), renames and drops. A merge works across
  types: mentions, relations and aliases move, so the next extraction of that name lands on the entity that
  stays. It also takes the acronym out of the middle of names ("large language model (LLM) agent"). It makes a
  backup first and rebuilds the Neo4j mirror, now or at the next sync. Running it again changes nothing.
  The extraction follows the same rules:
  - "GPT4" meets "GPT-4" and "nnUnet" meets "nnU-Net" without the judge;
  - dropped names are skipped;
  - "compared with" may join a technique, a model and a product;
  - "uses" a problem is stored as "addresses".
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

Animated lessons (aulas; research in `docs/research/reports/Aulas didáticas animadas em 3D.md`; plans in
`docs/superpowers/plans/2026-11-09-aulas-3d-f0-f1.md`, `docs/superpowers/plans/2026-11-10-aulas-motor-hyperframes.md` and
`docs/superpowers/plans/2026-11-11-aulas-3d-hibrido.md`):

- `sotawhat lessons make --tema "Atenção no Transformer" [--entidade 105 …]` (or `--auto`, the strongest weekly
  trend without a lesson) makes a 3–6 minute lesson in the HyperFrames engine (since 2026-11-10):
  1. The source pack is built from the graph.
  2. An LLM writes the plan (`lesson_plan_v4`). Each scene names the kit template that shows it, and one worked
     example with its numbers travels through the lesson. The plan goes through the G2 lint and the G1 fact gate,
     with one revision round.
  3. An LLM writes the storyboard (`sotawhat/lessons/storyboard.py`). It fills the template of each scene with data
     and lists the actions of each sentence, each with the word that triggers it. It runs before the voice, so a
     failure here spends no credits.
  4. ElevenLabs narrates each scene (`eleven_v4`, voice Klaus), with the time of every word. Those times drive
     the captions and the cue words. Every scene is cached, so a rerun spends no credits.
  5. The `mechanism3d` scenes get their three.js from an LLM (`sotawhat/lessons/three3d.py`, prompt
     `lesson_three_v2`). The LLM writes only geometry and motion. The kit owns the camera, the labels, the timing
     and the look. Each scene is checked by a headless probe (`probe3d.py`: errors, parts off the frame) and the
     visual critic, with repairs. A scene that never passes is drawn as the graph of its parts. The module is
     cached in `data/lessons/<id>/3d/`.
  6. The kit (`sotawhat/lessons/motion_kit`: HTML, CSS, GSAP; three.js for the 3D) owns layout, links, motion, type
     and colour, and HyperFrames renders the video: headless Chrome plus FFmpeg, deterministic. The MP4 fits in
     48 MB. A resume with nothing changed keeps the video.
  7. `interativo.html` (`sotawhat/lessons/interactive.py`) puts every 3D scene of the lesson in one self-contained
     file: the same code as the video, bundled with three.js by HyperFrames' esbuild, plus the narration of each
     scene. You hear the scene, drag the timeline, drag to turn and pinch or scroll to zoom. It goes to Telegram
     after the video and is linked on the Aulas tab.
- The kit templates:
  - `graph`: parts and arrows routed border to border.
  - `bars`: scores, softmax and weights.
  - `chart`: curves on axes. A ROC curve is drawn from its AUC, so the number said, the curve and the area agree.
  - `timeline`: events in time.
  - `compare`: alternatives side by side.
  - `vectors3d`: dot products as angles.
  - `patches`: an image cut into tokens.
  - `volume3d`: synthetic CT/MRI slices that stack into a volume, a cut with its 2D image, an organ segmented into a
    marching-cubes surface, and a finding.
  - `mechanism3d`: a physical mechanism in 3D, written for the scene (the CT gantry turning with tube, beam and
    detector; a probe sweeping; a voxel grid being segmented). The plan uses 2–4 scenes in 3D when the topic has
    spatial steps.
- The video goes to Telegram with:
  - the interactive 3D file, when the lesson has 3D scenes;
  - the cost of the lesson, LLM plus voice, in US$ and in R$ at the PTAX of the Banco Central;
  - the quiz;
  - your review buttons (✅ / ⚠️);
  - the comparison with the NotebookLM Video Overview generated from `fontes.md`.

  The daily run sends the re-quiz two days later.
- Cost:
  - The voice is priced as credits × your plan's price per credit (`SOTAWHAT_ELEVENLABS_PLAN_USD`,
    `SOTAWHAT_ELEVENLABS_PLAN_CREDITS`: Starter is US$ 5 for 30k credits; a 3.5-minute lesson uses about 2.7k).
  - The R$ comes from the PTAX of the Banco Central (open-data API, `sotawhat/fx.py`).
  - The LLM cap per lesson (`SOTAWHAT_LLM_BUDGET_USD_LESSON`) counts only the LLM.
- Other commands:
  - `lessons resume N [--refazer plano,storyboard,voz,3d,video]` continues a lesson or redoes some steps (`voz`
    spends credits again); `--so-roteiro` (with `make` too) stops after the plan, for the review on the Aulas tab;
  - `lessons hf N` remakes an older lesson (its plan and sources) in the HyperFrames engine;
  - `lessons send N`, `lessons pack N` and `lessons list` deliver a lesson, export its pack and list the lessons.
- The Aulas tab makes lessons too (since 2026-11-20; design in
  `docs/superpowers/specs/2026-11-20-aulas-pela-interface-design.md`):
  1. **Nova aula.** Write a topic, or click a suggestion of the week (the trends without a lesson). Optionally link
     up to 3 graph entities, and choose the models (econômico or equilibrado). "Planejar roteiro" makes only the plan:
     2 to 4 minutes and US$ 0.01 to 0.02, no voice.
  2. **Review.** The card shows the plan (scenes with their narration, quiz, fact gate) and the estimate of its
     production: length, 3D scenes, voice credits, cost and time, beside the ElevenLabs credits left. Then
     "Produzir aula" (with "enviar ao Telegram ao terminar"), "Refazer roteiro" or "Descartar".
  3. **Production.** It runs in the background. The card shows the steps (done, running, still to come with their
     estimate), the time and the end of the log, with "Cancelar". The page can be closed, and the interface can
     restart: the lesson goes on.
  4. **After.** A ready lesson that was not sent has "Enviar ao Telegram". A lesson that stopped says where and why,
     with "Retomar": what was paid stays in its cache.

  Each action runs the same command as the terminal (`sotawhat lessons resume N --so-roteiro`, `resume N`,
  `send N`) in a process of its own, out of the job object of the scheduled task. One lesson is made at a time,
  from the interface or the terminal: a `lessons make/resume/hf/send` started while another is running refuses and
  says which one is. The state of the jobs is the `lesson_jobs` table (schema 8), and each lesson keeps its log in
  `data/lessons/<id>/job.log`. "Cancelar", "Refazer roteiro" and "Descartar" ask for a second click instead of a
  dialog. A discarded lesson leaves the list, keeps its files and gives its entities back to the suggestions.
- The Aulas tab also shows, for every lesson:
  - the videos;
  - the interactive 3D page;
  - the plan with the template of each scene;
  - the gates and the HyperFrames check;
  - what the lesson cost;
  - the review checklist.
- HyperFrames (HeyGen, Apache-2.0) is pinned in `data/tools/hyperframes` with versions at least two weeks old, and
  its telemetry is off:
  `npm install --before=2026-10-26T20:00:00Z --ignore-scripts --save-exact hyperframes@0.8.206 gsap@3.15.0
  three@0.186.1 katex@0.19.1 @fontsource/fraunces@5.3.0 @fontsource/manrope@5.3.0 lucide-static@1.61.0
  @ffprobe-installer/win32-x64@5.1.0`.
  FFmpeg comes from `sotawhat lessons setup` (`data/tools/lessons`).
- Lessons 1–5 were made with the first engine:
  - Manim and three.js scenes written by an LLM, a layout check and a visual review (G4);
  - Piper or Google Chirp voices.

  It is kept so they can still be resumed (`resume` follows the engine of each lesson), re-narrated
  (`lessons rerender N --voz …`) and voice-tested (`lessons voices`). The user rejected its look and voice on
  2026-11-10.

Tools radar (radar de ferramentas, 2026-11-10; plan in `docs/superpowers/plans/2026-11-10-radar-ferramentas.md`): skills,
plugins, MCP servers and other tools on the rise on GitHub, for building AI systems rather than medicine. It stays
outside the triage, the digest and the graph.

- `config/tools_radar.yaml` lists the fronts and their GitHub searches:
  - skills, plugins and MCPs;
  - agent architecture and evals;
  - tokens and context;
  - lessons: video, animation and voice.
- `sotawhat radar scan` runs at the end of `run daily`:
  - two searches per query, the active repositories already in use and the new ones that climb;
  - the GitHub repositories in the Hacker News stories of the week (Algolia's public API);
  - a daily count of every tracked repository's stars.

  Star growth comes from these counts. The scan also fills the 14 days before a repository's first count, up to 300
  repositories a day, from GitHub's star history endpoint:
  - `/stargazers/history` (September 2026) gives the stars given each day and never who gave them. Since July 2026
    GitHub lists who starred only to a repository's admins and collaborators.
  - The count of day d is the latest count minus the stars given after d, so the week is the sum of those days.
  - A repository without that history is scaled from what there is and marked as an estimate.
  - `sotawhat radar backfill [--dias 14]` fills all of them at once.
- `sotawhat radar report [--no-notify]`, which `run weekly` runs every Sunday:
  - measures the stars gained in the week and the week before;
  - adds the npm and PyPI downloads of the last two weeks (packages read from `package.json`/`pyproject.toml`) and
    the Hacker News points;
  - scores each repository by the mean percentile of its signals;
  - sends the leading 30 to a cheap judge (task `radar`, ZDR), which gives the front, the relevance 0–5 for your stack,
    what the tool does, why it helps and its risks;
  - reports the top 10 with relevance ≥ 3, at most 4 per front, with "testar a partir de" (the latest release plus
    14 days, the dependency rule).
- The section goes into the weekly report, to Telegram (🧪 testar · 👍 · 👎 · 🗄️ depois per tool) and to the Ferramentas
  tab of the interface.
- The official MCP registry is not crawled (more than 6,000 servers change every two weeks). OSS Insight's trend
  ranking has been unavailable since 2026-03-01.

The digests explain themselves, since 2026-11-20 (SDD §6.14, `config/digest.yaml`):

- `didactic: true` writes the summaries for a physician who is not an ML specialist (prompt `triage_v4`: up to 75 words,
  a plain first sentence, a short gloss in parentheses after a term beyond the basics). On the golden set its decisions
  differ from the old prompt's as much as two runs of the same prompt differ (`sotawhat eval models --prompt triage_v3`).
- `glossary: true` ends each digest (e-mail, Telegram, the day's file) with "Glossário do dia": the ML/AI terms of its
  texts, one sentence each, without medical terms or product names. A term is defined once by the LLM (task `glossary`,
  one call a digest) and found again with no LLM. A digest prints up to 8 terms, the new ones first; a term leaves the
  digests after 3 of them or when you mark it "já sei" in the Glossário tab of the interface, which lists them all.
- `sotawhat glossary list` prints the glossary; `sotawhat glossary backfill [--dias 14]` defines the terms of the digests
  already sent. The MCP server has a `glossary` tool.

Questions to the graph, answered by a small model on your own machine (SDD §6.15):

- `sotawhat ask "o que saiu esta semana sobre agentes clínicos?"` (also the Perguntar tab of the interface and the
  `retrieve` tool of the MCP server). Options: `--dias N`, `--k N`, `--so-fontes` (no model), `--sem-rerank`,
  `--detalhes`, `--json`.
- The retrieval needs no LLM and reads only the SQLite store: a time window and words such as "quantos" or "mais
  citados" read from the question, the entities it names or means, six rankings of the approved items (dense, BM25,
  personalized PageRank over the entity graph, mentions, typed relations, triage categories) fused by reciprocal rank,
  and a multilingual cross-encoder on the best ten. The model gets the facts computed from the graph plus up to 8
  numbered sources.
- The answer comes from an OpenAI-compatible endpoint (`SLM_BASE_URL`, `SLM_MODEL`). `sotawhat rag up` starts Ollama in
  Docker (service `ollama` of `compose.yaml`, GPU, port on 127.0.0.1 only) and pulls the model; the default,
  `qwen3.5:9b-q4_K_M`, fits a GPU of 8 GB. What the model writes is checked without another model: a citation of a
  source that is not there, an answer with no citation and a number that is not in the sources become warnings next
  to the answer. With no model running, the sources and the graph facts are the answer.
- A second engine answers without writing: `sotawhat ask "..." --motor jev` (the "Jev · extrai" switch of the Perguntar
  tab, or `RAG_ENGINE=jev`). Jev, TypeSafe's typed-decision model, reached through OpenRouter with the same ZDR setting,
  judges each of the ten best candidates in parallel (does this passage help to answer the question?) and picks the
  sentence of each one that does. The answer is those sentences, quoted with their source numbers. It takes about 2
  seconds instead of about 12, costs about US$ 0.0004 a question, and on the 40 evaluation questions it put the right
  item first in 97 to 100% (the local cross-encoder: 95%). What it gives up is the written synthesis.
- `sotawhat rag index` refreshes the passages and their vectors (the daily run does it after the graph stage; the first
  build embeds everything and takes minutes), `sotawhat rag status` shows what is indexed and whether the model answers,
  and `sotawhat rag eval [--gerar] [--n 40] [--jev]` measures how often the retrieval finds the item a question is
  about, as a whole and per ranking (`--jev` adds the Jev judge; it costs cents).
- On a VPS: clone the repository there, run `docker compose -f compose.vps.yaml up -d --build` and
  `docker compose -f compose.vps.yaml exec ollama ollama pull qwen3.5:4b-q4_K_M`, then send the store from your PC with
  `scripts\vps_sync.ps1 -Vps user@host`. The interface opens on the VPS's 127.0.0.1 only (use
  `ssh -L 8765:127.0.0.1:8765 user@host`), no API key goes there, and the VPS only reads: a vote given on its copy is
  lost at the next sync.

Semantic Scholar now reads `SEMANTIC_SCHOLAR_API_KEY` (free, optional) and asks for the most cited papers of the last
60 days in bulk, retrying a 429; before 2026-11-20 it asked the relevance search without a key and failed every day.

The Instagram import (`sotawhat instagram import following.json --yes`) fetches the profiles in batches of 40 (about
10 s each on Apify) and keeps them in `data/state/instagram_profiles.json`. An import that stops resumes without paying
twice, and `--recuperar RUN_ID` adds what an aborted Apify run had fetched. `config/instagram_accounts.yaml` lists the
accounts you follow, so it stays out of git.

To set it up, copy `.env.example` to `.env` and fill in at least `OPENROUTER_API_KEY`,
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Then schedule the runs with
`powershell -ExecutionPolicy Bypass -File scripts\schedule_daily.ps1 [-Listener] [-Web] [-Weekly]`.
The daily task also fires at logon with `run daily --catch-up 07:00`. When a restart has logged you off at 07:00
(Windows Update, for example), the missed run happens at your next logon. On any other logon it only logs that
today's run already happened.

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
