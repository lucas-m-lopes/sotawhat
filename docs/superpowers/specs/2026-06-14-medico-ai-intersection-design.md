# Design — Focus the `medico` profile on the AI∩medicine intersection

Date: 2026-06-14
Status: approved (pending spec review)

## Problem

The `medico` digest profile returns many broad medical articles with no AI/ML
content. None of its sources require that a result actually sits at the
intersection of AI and medicine:

- PubMed queries pass plain medical terms (`radiology`, `diagnosis`,
  `medical imaging`, `electronic health record`), matching any clinical paper.
- arXiv `q-bio.QM` and the medical RSS feeds are not constrained to AI either.

Investigation also found that the RSS adapter (`feedparser.parse(url)`) silently
fails on several publisher feeds (Nature returns garbage / 0 entries without a
browser User-Agent). This is why the last medico run produced **0** notes from
`nature-machine-intelligence` and `radiology-ai` — they were broken, not empty.

## Goal

Restrict the `medico` profile to papers that are clearly about AI/ML applied to
medicine, via three reinforcing mechanisms, plus an RSS robustness fix that
revives publisher feeds.

Decisions taken during brainstorming:
- Use **both** a PubMed AI clause (force intersection at the source) **and** a
  cross-source AI-relevance filter (catch arXiv q-bio and RSS noise).
- **Expand** the medical RSS feeds with validated intersection journals.
- Keep the medical keywords as clean topic labels (so concept links stay clean).
- Do not touch the `geral` profile's behavior (it only inherits the more robust
  RSS fetch).

## Architecture

### 1. PubMed AI clause — `sotawhat/sources/pubmed.py`

`PubMedSource.__init__` gains an optional `and_clause=None`. When set, the search
term becomes `({keyword}) AND ({and_clause})`; when `None`, behavior is unchanged.

The medico clause (defined in `profiles.py`):

```
("Artificial Intelligence"[Mesh] OR "machine learning"[tiab] OR "deep learning"[tiab] OR "neural network*"[tiab] OR "large language model*"[tiab] OR "foundation model*"[tiab])
```

The MeSH term "Artificial Intelligence" auto-explodes to Machine Learning, Deep
Learning, NLP, etc.; the `[tiab]` phrases catch recent papers not yet MeSH-indexed.
The clean keyword is still what `collect()` records as the concept, so concept
links remain `[[radiology]]` etc.

### 2. Cross-source AI-relevance filter — `sotawhat/textmatch.py` (new) + `sotawhat/digest.py`

New module `sotawhat/textmatch.py`:

```python
import re

def contains_term(text, term):
    return re.search(r"\b" + re.escape(term.lower()) + r"\b", text.lower()) is not None

def contains_any(text, terms):
    return any(contains_term(text, t) for t in terms)
```

`sotawhat/backfill.py` `_matches` is refactored to delegate to `contains_term`
(DRY; the regex is identical).

`PROFILES["medico"]` gains `require_any: AI_TERMS`. In `run_digest`, after
`collect()` and before `write_notes()`:

- If the profile defines `require_any`, keep only results whose
  `f"{title} {abstract}"` contains at least one term (`contains_any`).
- Report how many were dropped (stderr), then proceed.

`geral` has no `require_any` → unfiltered.

`AI_TERMS` (in `profiles.py`):

```
["artificial intelligence", "machine learning", "deep learning",
 "neural network", "large language model", "foundation model", "transformer",
 "computer vision", "natural language processing", "radiomics", "generative",
 "diffusion model", "reinforcement learning", "convolutional",
 "predictive model", "AI", "LLM", "NLP"]
```

Bare `"ML"` is deliberately excluded — word-boundary matching would match `"mL"`
(milliliters) in clinical abstracts. `"AI"`, `"LLM"`, `"NLP"` are safe under
word-boundary matching.

### 3. Robust RSS fetch — `sotawhat/sources/rss.py`

Split fetching from parsing so fixture-based tests keep working:

- `parse_feed(content, source)` stays **parse-only** — it calls
  `feedparser.parse(content)`, where `content` may be bytes, a string, or a local
  path (so tests can pass a fixture). Its body is otherwise unchanged.
- New `fetch_feed(url)` does the network fetch:
  `httpx.get(url, headers=_UA, timeout=30, follow_redirects=True)`,
  `raise_for_status()`, returns `response.content`. `_UA` is a browser-like
  User-Agent (e.g. `Mozilla/5.0 (sotawhat/2.0)`), verified to make Nature feeds
  return entries.
- `RSSSource.search` wraps each feed: `try: content = fetch_feed(url)` then
  `parse_feed(content, ...)`; `except Exception: continue` (skip that feed).

This applies to both profiles' RSS usage; `geral` only benefits (more feeds
parse). A failing feed is skipped, matching the existing "unreachable feeds are
skipped" contract.

### 4. Medical feeds — `sotawhat/profiles.py`

`MEDICAL_FEEDS` becomes (only feeds verified to return entries via httpx+UA):

```python
MEDICAL_FEEDS = [
    ("nature-machine-intelligence", "https://www.nature.com/natmachintell.rss"),
    ("npj-digital-medicine", "https://www.nature.com/npjdigitalmed.rss"),
    ("jmir-ai", "https://ai.jmir.org/feed/atom"),
    ("jmir-medinform", "https://medinform.jmir.org/feed/atom"),
]
```

`radiology-ai` (RSNA) is removed — it returns 403 even with a User-Agent and never
produced results; the `radiology` topic is still covered by the PubMed query.

`build_sources("medico")` passes `and_clause=MEDICAL_AI_CLAUSE` to `PubMedSource`.
Medical keywords are unchanged: `["clinical LLM", "medical imaging", "diagnosis",
"radiology", "electronic health record"]`.

## Testing (TDD)

- `textmatch.contains_term`: word-boundary (`agent` not in `reagent`); `"ML"` not
  in `"5 mL"`; multi-word terms match.
- `backfill._matches` still passes after delegating to `contains_term` (existing
  tests stay green).
- `PubMedSource` with `and_clause` builds the term `({keyword}) AND ({clause})`
  (assert via a fake/captured request, no network); with `and_clause=None` the
  term is just the keyword.
- `run_digest` relevance filter: a medico result lacking any AI term is dropped;
  one containing an AI term is kept; `geral` is unaffected.
- `rss.parse_feed`: parses a local fixture (unchanged behavior).
- `RSSSource.search`: with `fetch_feed` monkeypatched to raise for one feed and
  return fixture bytes for another, the failing feed is skipped and the other's
  entries are returned.

## Out of scope (YAGNI)

- Changing the medical keyword list (kept as clean topic labels).
- Any change to `geral`'s sources/keywords (only inherits robust RSS fetch).
- Adding feeds that block bots (Lancet Digital Health, RSNA Radiology: AI).

## Files touched

- `sotawhat/sources/pubmed.py` — optional `and_clause`.
- `sotawhat/sources/rss.py` — httpx fetch + per-feed error isolation.
- `sotawhat/textmatch.py` — NEW shared word-boundary matcher.
- `sotawhat/digest.py` — relevance filter in `run_digest`.
- `sotawhat/backfill.py` — `_matches` delegates to `textmatch`.
- `sotawhat/profiles.py` — `MEDICAL_AI_CLAUSE`, `AI_TERMS`, `require_any`,
  expanded `MEDICAL_FEEDS`, `build_sources` wires the clause.
- `tests/` — new/updated tests per the list above.
