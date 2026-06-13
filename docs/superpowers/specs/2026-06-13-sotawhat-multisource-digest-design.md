# sotawhat 2.0 — Multi-source digest → Obsidian

**Date:** 2026-06-13
**Status:** Approved design — pending implementation plan

## 1. Goal

Evolve `sotawhat` from a fragile, single-source (arXiv HTML scraping) CLI into a
robust **multi-source AI/ML research aggregator** that can run on demand *and*
unattended, delivering daily curated insights about ML/AI in general and AI/ML in
the medical field, written as Markdown notes into a local Obsidian vault.

## 2. Scope

In scope:
- Replace arXiv HTML scraping with the official arXiv API.
- Add source adapters: Semantic Scholar, Hugging Face Daily Papers, PubMed
  (E-utilities), and a generic RSS adapter for research-lab blogs and medical
  journals.
- Modernize dependencies (drop `six`, `nltk`, `pyspellchecker`,
  `win-unicode-console`; add `httpx`, `feedparser`, `pytest`).
- Keep and extend the original "metrics / state-of-the-art" summarization heuristic.
- `digest` command with predefined profiles (`geral`, `medico`).
- Obsidian output: one Markdown note per item, with YAML frontmatter, tags,
  and cross-run deduplication.
- A Windows Task Scheduler setup to run the digest daily at 08:00.

Out of scope (decided during brainstorming):
- X (Twitter) and Instagram — hostile to automation, low research signal, ToS risk.
- Papers with Code — discontinued by Meta in 2025; API unstable.
- Playwright is **not** in the default data path; kept only as a possible future
  fallback for a source that has no API/RSS.

## 3. Verified facts (as of 2026-06-13)

- arXiv advanced-search HTML still matches the current code's tag constants
  (verified live via Playwright: 50 results, all CSS targets present). The scraper
  *probably* still runs, but line-based string parsing is fragile — hence the move
  to the official API.
- Source research produced the curated list in §5.

## 4. Architecture

Source-adapter pattern. Each source is isolated, returns a normalized list of
`Result`, and is testable in isolation against recorded fixtures.

```
sotawhat/
  __init__.py          # __VERSION__
  cli.py               # argparse: `search` and `digest` subcommands
  models.py            # @dataclass Result
  summarize.py         # pure heuristic: has_number, contains_sota, extract_line
  render.py            # terminal output grouped by source
  profiles.py          # predefined digest profiles
  obsidian.py          # write one .md note per item + dedup index
  sources/
    base.py            # class Source: search(keyword, limit) -> list[Result]
    arxiv.py           # official API (export.arxiv.org/api, Atom XML)
    semantic_scholar.py# Graph API (JSON)
    hf_papers.py       # Hugging Face daily papers (JSON)
    pubmed.py          # NCBI E-utilities (esearch + efetch, MeSH terms)
    rss.py             # generic RSS adapter (feedparser), configured by feed list
```

### `Result` (models.py)

```
@dataclass
class Result:
    id: str            # stable dedup key: arXiv id / DOI / canonical URL
    title: str
    authors: list[str]
    date: str          # ISO 8601 where possible
    url: str
    abstract: str      # summary/abstract/feed content
    source: str        # "arxiv", "semantic_scholar", "pubmed", "rss:<name>", ...
    extra: dict        # source-specific fields (optional)
```

### Source base contract

```
class Source:
    name: str
    def search(self, keyword: str, limit: int) -> list[Result]: ...
```

- Each source enforces its own timeout and rate-limit handling.
- A source that raises is caught by the orchestrator: it logs a warning and the
  digest continues with the other sources.

## 5. Curated sources

### General ML/AI — labs & respected authors (RSS via `rss.py`)
Google Research, DeepMind, Anthropic, Hugging Face Blog, BAIR (Berkeley),
MIT News – AI, The Gradient, Ahead of AI (Sebastian Raschka), Simon Willison,
MarkTechPost.

### Paper aggregators (API)
- arXiv official API — categories `cs.LG`, `cs.CL`, `cs.AI`.
- Semantic Scholar Graph API.
- Hugging Face Daily Papers (JSON) — trending signal.

### Medical AI (API/RSS)
- PubMed E-utilities — official free API, MeSH terms
  (`artificial intelligence`, `machine learning`). Primary clinical source.
- arXiv filtered by `q-bio` + medical keywords.
- Nature Machine Intelligence (RSS), JMIR AI (RSS), Radiology: AI (RSS),
  JAMA AI (RSS).

Exact feed URLs are resolved and pinned during implementation; unreachable feeds
are logged and skipped, never fatal.

## 6. Summarization heuristic (kept & extended)

`summarize.py` keeps the original logic, now pure (no nltk/six):
- `has_number` — prioritize sentences with real numbers/metrics, ignoring citation
  years and list numerals. The nltk `word_tokenize` call is replaced by a
  lightweight regex tokenizer.
- `contains_sota` — sentences mentioning "state-of-the-art" / "SOTA".
- `extract_line` — selects the most informative sentences from an abstract.
- For RSS items without a paper-style abstract, the heuristic runs over the
  title + feed summary; if nothing scores, fall back to the raw feed summary.

## 7. Digest command & profiles

`sotawhat digest --profile <name> --vault <path> [--limit N]`

`profiles.py` defines predefined parameter sets. **Default keywords below are
placeholders for the user to edit during spec review.**

```
PROFILES = {
  "geral": {
    "sources": ["arxiv", "semantic_scholar", "hf_papers", "rss:labs"],
    "keywords": ["large language model", "reinforcement learning",
                 "diffusion model", "agent"],
    "tags": ["ml-ai"],
  },
  "medico": {
    "sources": ["pubmed", "arxiv:qbio", "rss:medical"],
    "keywords": ["clinical LLM", "medical imaging", "diagnosis",
                 "radiology", "electronic health record"],
    "tags": ["medical-ai"],
  },
}
```

Backward compatibility: `sotawhat <keyword> [N]` and `sotawhat search <keyword> [N]`
keep the classic behaviour (all sources, grouped terminal output).

## 8. Obsidian output (one note per item)

`obsidian.py`:
- Path: `<Vault>/<Profile>/<Source>/<YYYY-MM-DD>-<sanitized-title>.md`
- Vault default: `D:\Lucas\obsidian_vaults\ml_ai_med_vault` (created if missing).
- YAML frontmatter per note:

```
---
title: "<title>"
authors: [<authors>]
date: <item date>
source: <source>
url: <url>
keywords: [<matched keywords>]
tags: [ml-ai | medical-ai, source/<source>]
added: <run date>
---
```

- Body: the summarized extract + a link back to the source.
- Optional lightweight per-profile index note linking the day's items via wikilinks.

### Deduplication (mandatory)
- A `.sotawhat_seen.json` index lives at the vault root, mapping `Result.id`
  → note path.
- The daily job creates a note only for unseen ids; seen items are skipped.
- Title sanitization strips characters invalid on Windows filesystems.

## 9. Scheduling — Windows Task Scheduler

- `schedule_digest.ps1` runs both profiles in sequence and writes to the vault.
- A `schtasks` command (documented + provided) registers a daily task at **08:00**
  invoking the script.
- The scheduler is **not** created automatically: the user confirms creation.
- Cloud `/schedule` routines were rejected because they cannot write to the local
  vault.

## 10. Resilience

- Per-source timeouts; one source failing never aborts the digest.
- Respect rate limits (Semantic Scholar, PubMed); add a polite User-Agent and,
  where applicable, an API-key/email parameter (PubMed `tool`/`email`).
- Empty overall result prints/logs a clear message.

## 11. Testing

- `summarize.py`: pure unit tests (deterministic).
- `obsidian.py`: unit tests for dedup, path/title sanitization, frontmatter.
- Source adapters: parse recorded fixture responses (saved sample API/RSS payloads)
  — no network in tests.
- `pytest` as the dev dependency.

## 12. Dependency changes

| Removed | Reason |
|---|---|
| `six` | Python 3 only; `html.unescape` replaces it |
| `nltk` (+ punkt download) | Heavy; replaced by a regex tokenizer |
| `pyspellchecker` | CS-category heuristic replaced by API category filter |
| `win-unicode-console` | Unnecessary on Python 3.7+ |

| Added | Reason |
|---|---|
| `httpx` | Modern HTTP (timeouts, retries) |
| `feedparser` | Robust RSS parsing |
| `pytest` (dev) | Tests (none exist today) |

## 13. Implementation phases (for the plan)

1. Core refactor: `models`, `summarize` (pure), `sources/base`, arXiv API adapter,
   `render`, CLI `search` — at parity with today, on the new architecture.
2. Additional adapters: Semantic Scholar, HF Daily Papers, PubMed, generic RSS.
3. `digest` command + `profiles`.
4. `obsidian.py` output + dedup.
5. `schedule_digest.ps1` + `schtasks` setup (user-confirmed).
6. Tests + dependency/packaging cleanup (`setup.py`/`pyproject`).

## 14. Open items for user during spec review

- Confirm/adjust the default profile keywords (§7).
- Confirm the daily run time (08:00 assumed).
- Confirm whether the optional per-profile index note is wanted.
