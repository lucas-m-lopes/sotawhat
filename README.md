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

## Install

Requires Python 3.9+.

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
