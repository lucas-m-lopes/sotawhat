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

## 3.0 (in progress): insight engine

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

To set it up, copy `.env.example` to `.env` and fill in at least `OPENROUTER_API_KEY`,
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Then schedule the daily run with
`powershell -ExecutionPolicy Bypass -File scripts\schedule_daily.ps1 [-Listener] [-Web]`.

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
