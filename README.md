# sotawhat 2.0

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A multi-source AI/ML research aggregator. Search the latest papers on demand,
or run an unattended daily **digest** that writes curated Markdown notes into a
local [Obsidian](https://obsidian.md) vault.

Original SOTAWHAT background: [blog post](https://huyenchip.com/2018/10/04/sotawhat.html).

## What's new in 2.0

- **Multiple sources** behind a single interface: arXiv (official API),
  Semantic Scholar, Hugging Face Daily Papers, PubMed, and generic RSS/Atom feeds.
- **Daily digest → Obsidian** with cross-run dedup, one note per item, YAML
  frontmatter and tags.
- **No more `nltk`/`six`/`pyspellchecker`/`win-unicode-console`** — the
  summarizer is now pure Python. The only runtime deps are `httpx` and
  `feedparser`. No `punkt` download, no SSL/encoding workarounds.

## 3.0 (in progress): insight engine

sotawhat is becoming an insight engine for AI/ML ∩ medicine. The design is in
`docs/sdd/2026-11-07-insight-engine-sdd.md` and the phase plans are in `docs/superpowers/plans/`.
Phase P0 adds:

- `sotawhat run daily [--vault PATH] [--no-notify] [--limit N]` collects every
  profile, normalizes and de-duplicates items into `data/insight.db` (SQLite),
  tracks the health of every source and feed, and sends a run summary to
  Telegram. A feed that returns an HTML anti-bot page now counts as an error
  instead of silently yielding 0 items. `--vault` keeps writing Obsidian notes
  during the transition.
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
- The digest goes to Telegram (up to 15 main items with 👍 👎 🧪 buttons, plus a radar of
  frontier AI without a medical bridge) and to `data/digests/YYYY-MM-DD.md` and `.html`.
  Nothing relevant and nothing broken means nothing is sent.
- With `DIGEST_EMAIL_TO` set, the same digest also goes by e-mail (SMTP; with Gmail it reuses
  `GMAIL_ADDRESS` and the app password in `GMAIL_APP_PASSWORD`, never the account password).
- `sotawhat feedback pull|listen` records the votes; after 100 votes a profile gets its own
  classifier (logistic regression over the embeddings), which then decides what reaches the LLM.
- `sotawhat eval golden draft|import` builds a golden set that you label by editing a Markdown
  file, and `sotawhat eval models [--apply]` runs the bake-off of triage models against it
  and can put the winner first in `config/llm.yaml`.

To set it up, copy `.env.example` to `.env` and fill in at least `OPENROUTER_API_KEY`,
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Then schedule the daily run with
`powershell -ExecutionPolicy Bypass -File scripts\schedule_daily.ps1 [-Vault PATH] [-Listener]`.

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

### Digest → Obsidian vault

Run a predefined profile and write notes into a vault:

```bash
sotawhat digest --profile geral  --vault "D:\path\to\ObsidianVault" --limit 10
sotawhat digest --profile medico --vault "D:\path\to\ObsidianVault" --limit 10
```

- `geral` — general ML/AI (arXiv, Semantic Scholar, HF Daily Papers, lab/blog RSS).
- `medico` — AI∩medicine only. PubMed queries are AND-ed with an AI clause
  (MeSH "Artificial Intelligence" + recent ML/LLM phrases), and every result
  (PubMed, arXiv q-bio/CV/LG, medical-journal RSS) must mention an AI/ML term to
  be kept. Feeds: Nature Machine Intelligence, npj Digital Medicine, JMIR AI,
  JMIR Medical Informatics.

Notes are written to `<vault>/<profile>/<source>/<date>-<title>.md`. A
`.sotawhat_seen.json` index in the vault root prevents the same item from being
written twice across runs. A single source failing (rate limit, network) is
isolated — the run continues with the other sources.

### Concept links (graph edges)

Each note links to **concept notes** (one per profile keyword) via a
`**Conceitos:** [[...]]` line, so the Obsidian graph clusters papers by topic.
Concept stubs are created under `<vault>/concepts/`.

To retro-link notes written before this feature:

```bash
sotawhat backfill-links --vault "D:\path\to\ObsidianVault"            # all profiles
sotawhat backfill-links --vault "D:\path\to\ObsidianVault" --profile medico
```

Backfill scans existing notes for profile keywords (word-boundary match) and
inserts the concept line. It is idempotent — notes already linked are skipped.

## Scheduled daily digest (Windows)

> 2.0 path. For 3.0 use `scripts\schedule_daily.ps1` (see "3.0 (in progress)" above).

`scripts/schedule_digest.ps1` runs both profiles into one vault:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\schedule_digest.ps1 -Vault "D:\path\to\ObsidianVault" -Limit 10
```

Register it to run daily at 08:00 with Task Scheduler:

```bat
schtasks /Create /SC DAILY /ST 08:00 /TN "sotawhat-digest" ^
  /TR "powershell -ExecutionPolicy Bypass -File \"D:\Lucas\code_projects\sotawhat\scripts\schedule_digest.ps1\""
```

Remove it with:

```bat
schtasks /Delete /TN "sotawhat-digest" /F
```

## Development

```bash
.\.venv\Scripts\python -m pytest -q
```

Source adapters are tested against recorded fixtures in `tests/fixtures/`, so
the suite runs without network access.
