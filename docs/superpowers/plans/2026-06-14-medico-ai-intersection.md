# Medico AI∩Medicine Focus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restrict the `medico` digest profile to papers at the AI∩medicine intersection via a PubMed AI clause, a cross-source AI-relevance filter, more reliable RSS fetching, and a curated feed list.

**Architecture:** A shared word-boundary matcher (`textmatch.py`) powers both the new relevance filter (in `digest.run_digest`) and the existing backfill matcher. `PubMedSource` gains an optional AND clause; `RSSSource` fetches via httpx with a browser User-Agent and isolates per-feed failures; `profiles.py` wires it all together for `medico` only.

**Tech Stack:** Python 3.9+, `httpx`, `feedparser`, stdlib `re`, pytest.

---

## File Structure

- `sotawhat/textmatch.py` — NEW. `contains_term` / `contains_any` word-boundary matchers (single responsibility: text matching).
- `sotawhat/backfill.py` — `_matches` delegates to `textmatch.contains_term` (DRY); drop now-unused `import re`.
- `sotawhat/sources/pubmed.py` — `PubMedSource(and_clause=None)` + `_term()` helper.
- `sotawhat/sources/rss.py` — `fetch_feed(url)` via httpx; `RSSSource.search` isolates per-feed failures.
- `sotawhat/digest.py` — `filter_relevant()` + `run_digest` applies `profile["require_any"]`.
- `sotawhat/profiles.py` — `MEDICAL_AI_CLAUSE`, `AI_TERMS`, `require_any`, expanded `MEDICAL_FEEDS`, wired `build_sources`.
- `tests/` — `test_textmatch.py` (new) + additions to `test_pubmed.py`, `test_rss.py`, `test_digest.py`, `test_profiles.py`.

---

## Task 1: Shared word-boundary matcher + backfill refactor

**Files:**
- Create: `sotawhat/textmatch.py`
- Modify: `sotawhat/backfill.py`
- Test: `tests/test_textmatch.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_textmatch.py`:

```python
# tests/test_textmatch.py
from sotawhat.textmatch import contains_term, contains_any

def test_contains_term_word_boundary():
    assert contains_term("we built an agent system", "agent")
    assert not contains_term("we used a reagent here", "agent")

def test_contains_term_ml_not_milliliters():
    assert not contains_term("we injected 5 mL of saline", "ML")
    assert contains_term("a machine learning model", "machine learning")

def test_contains_any():
    assert contains_any("deep learning in radiology", ["machine learning", "deep learning"])
    assert not contains_any("a clinical trial of aspirin", ["machine learning", "deep learning"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests/test_textmatch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sotawhat.textmatch'`.

- [ ] **Step 3: Create the module**

Create `sotawhat/textmatch.py`:

```python
# sotawhat/textmatch.py
import re

def contains_term(text, term):
    return re.search(r"\b" + re.escape(term.lower()) + r"\b", text.lower()) is not None

def contains_any(text, terms):
    return any(contains_term(text, t) for t in terms)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_textmatch.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Refactor backfill to delegate (DRY)**

In `sotawhat/backfill.py`, change the imports at the top from:

```python
import re
from pathlib import Path

from sotawhat.obsidian import ensure_concept_notes
```

to:

```python
from pathlib import Path

from sotawhat.obsidian import ensure_concept_notes
from sotawhat.textmatch import contains_term
```

Then replace the `_matches` function:

```python
def _matches(text, keyword):
    pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
    return re.search(pattern, text.lower()) is not None
```

with:

```python
def _matches(text, keyword):
    return contains_term(text, keyword)
```

- [ ] **Step 6: Run backfill + textmatch tests to verify no regression**

Run: `.\.venv\Scripts\python -m pytest tests/test_backfill.py tests/test_textmatch.py -v`
Expected: PASS (existing 4 backfill tests + 3 textmatch tests).

- [ ] **Step 7: Commit**

```bash
git add sotawhat/textmatch.py sotawhat/backfill.py tests/test_textmatch.py
git commit -m "feat: shared word-boundary matcher; backfill reuses it"
```

---

## Task 2: PubMed optional AND clause

**Files:**
- Modify: `sotawhat/sources/pubmed.py` (`PubMedSource`)
- Test: `tests/test_pubmed.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_pubmed.py`:

```python
from sotawhat.sources.pubmed import PubMedSource

def test_term_plain_without_clause():
    src = PubMedSource()
    assert src._term("radiology") == "radiology"

def test_term_with_and_clause():
    src = PubMedSource(and_clause='"Artificial Intelligence"[Mesh]')
    assert src._term("radiology") == '(radiology) AND ("Artificial Intelligence"[Mesh])'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests/test_pubmed.py -k term -v`
Expected: FAIL — `PubMedSource` has no `__init__`/`_term` accepting a clause (`AttributeError`).

- [ ] **Step 3: Implement**

In `sotawhat/sources/pubmed.py`, change the `PubMedSource` class. Replace:

```python
class PubMedSource(Source):
    name = "pubmed"

    def search(self, keyword, limit):
        s = httpx.get(_ESEARCH, params={
            "db": "pubmed", "term": keyword, "retmax": limit,
            "retmode": "json", "sort": "date", "tool": _TOOL, "email": _EMAIL},
            timeout=30, follow_redirects=True)
```

with:

```python
class PubMedSource(Source):
    name = "pubmed"

    def __init__(self, and_clause=None):
        self.and_clause = and_clause

    def _term(self, keyword):
        if self.and_clause:
            return f"({keyword}) AND ({self.and_clause})"
        return keyword

    def search(self, keyword, limit):
        s = httpx.get(_ESEARCH, params={
            "db": "pubmed", "term": self._term(keyword), "retmax": limit,
            "retmode": "json", "sort": "date", "tool": _TOOL, "email": _EMAIL},
            timeout=30, follow_redirects=True)
```

(The rest of `search` is unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_pubmed.py -v`
Expected: PASS (new `_term` tests + existing `test_parse_efetch`).

- [ ] **Step 5: Commit**

```bash
git add sotawhat/sources/pubmed.py tests/test_pubmed.py
git commit -m "feat: optional AND clause for PubMed queries"
```

---

## Task 3: Robust RSS fetch with per-feed isolation

**Files:**
- Modify: `sotawhat/sources/rss.py`
- Test: `tests/test_rss.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_rss.py` (note the new import line at top too):

```python
import sotawhat.sources.rss as rssmod

def test_search_skips_failing_feed(monkeypatch):
    fixture = open("tests/fixtures/sample_feed.xml", "rb").read()
    def fake_fetch(url):
        if "bad" in url:
            raise RuntimeError("403 Forbidden")
        return fixture
    monkeypatch.setattr(rssmod, "fetch_feed", fake_fetch)
    src = RSSSource("labs", [("bad", "http://bad/feed"), ("good", "http://good/feed")])
    results = src.search("transformer", 10)
    assert len(results) == 1
    assert results[0].source == "rss:good"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_rss.py -k skips_failing -v`
Expected: FAIL — `fetch_feed` does not exist (`AttributeError` on monkeypatch).

- [ ] **Step 3: Implement**

In `sotawhat/sources/rss.py`, change the top imports from:

```python
import feedparser
from sotawhat.models import Result
from sotawhat.sources.base import Source
```

to:

```python
import feedparser
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_UA = {"User-Agent": "Mozilla/5.0 (sotawhat/2.0)"}

def fetch_feed(url):
    r = httpx.get(url, headers=_UA, timeout=30, follow_redirects=True)
    r.raise_for_status()
    return r.content
```

Then replace `RSSSource.search`:

```python
    def search(self, keyword, limit):
        collected = []
        for label, url in self.feeds:
            collected.extend(parse_feed(url, source=f"rss:{label}"))
        return self._filter(collected, keyword, limit)
```

with:

```python
    def search(self, keyword, limit):
        collected = []
        for label, url in self.feeds:
            try:
                content = fetch_feed(url)
            except Exception:  # noqa: BLE001 - a failing feed must not abort the others
                continue
            collected.extend(parse_feed(content, source=f"rss:{label}"))
        return self._filter(collected, keyword, limit)
```

(`parse_feed` is unchanged — `feedparser.parse` accepts bytes, a path, or a URL, so the existing `test_parse_feed_maps_and_filters` fixture test still passes.)

- [ ] **Step 4: Run the rss test file to verify all pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_rss.py -v`
Expected: PASS (new skip test + existing `test_parse_feed_maps_and_filters`).

- [ ] **Step 5: Commit**

```bash
git add sotawhat/sources/rss.py tests/test_rss.py
git commit -m "feat: fetch RSS via httpx with UA and per-feed isolation"
```

---

## Task 4: Cross-source AI-relevance filter

**Files:**
- Modify: `sotawhat/digest.py`
- Test: `tests/test_digest.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_digest.py` (it already imports `from sotawhat.models import Result`):

```python
def test_filter_relevant_keeps_ai_drops_others():
    from sotawhat.digest import filter_relevant
    keep = Result(id="1", title="Deep learning for sepsis", authors=[],
                  date="", url="", abstract="x", source="pubmed")
    drop = Result(id="2", title="Aspirin trial", authors=[],
                  date="", url="", abstract="no method here", source="pubmed")
    out = filter_relevant([keep, drop], ["deep learning", "machine learning"])
    assert [r.id for r in out] == ["1"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_digest.py -k filter_relevant -v`
Expected: FAIL — `cannot import name 'filter_relevant'`.

- [ ] **Step 3: Implement**

In `sotawhat/digest.py`, add the import near the top (after the existing imports):

```python
from sotawhat.textmatch import contains_any
```

Add this function (e.g. after `collect`):

```python
def filter_relevant(results, terms):
    return [r for r in results
            if contains_any(f"{r.title} {r.abstract}", terms)]
```

In `run_digest`, after the `results = collect(...)` line and before the
`for w in warnings:` loop, insert:

```python
    require = profile.get("require_any")
    if require:
        before = len(results)
        results = filter_relevant(results, require)
        dropped = before - len(results)
        if dropped:
            print(f"[{ns.profile}] filtered out {dropped} non-AI result(s)",
                  file=sys.stderr)
```

- [ ] **Step 4: Run the digest test file to verify all pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_digest.py -v`
Expected: PASS (new filter test + existing collect tests).

- [ ] **Step 5: Commit**

```bash
git add sotawhat/digest.py tests/test_digest.py
git commit -m "feat: AI-relevance filter for profiles with require_any"
```

---

## Task 5: Wire up the `medico` profile

**Files:**
- Modify: `sotawhat/profiles.py`
- Test: `tests/test_profiles.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_profiles.py`:

```python
def test_medico_has_require_any():
    assert PROFILES["medico"]["require_any"]

def test_medico_pubmed_has_ai_clause():
    from sotawhat.profiles import MEDICAL_AI_CLAUSE
    sources = build_sources("medico")
    pub = [s for s in sources if s.name == "pubmed"][0]
    assert pub.and_clause == MEDICAL_AI_CLAUSE

def test_medical_feeds_curated():
    from sotawhat.profiles import MEDICAL_FEEDS
    labels = [name for name, _ in MEDICAL_FEEDS]
    assert "npj-digital-medicine" in labels
    assert "jmir-medinform" in labels
    assert "radiology-ai" not in labels
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests/test_profiles.py -k "require_any or ai_clause or curated" -v`
Expected: FAIL — `require_any` key missing / `MEDICAL_AI_CLAUSE` not defined / feeds not updated.

- [ ] **Step 3: Implement**

In `sotawhat/profiles.py`, replace the `MEDICAL_FEEDS` block:

```python
# Medical journal feeds.
MEDICAL_FEEDS = [
    ("nature-machine-intelligence", "https://www.nature.com/natmachintell.rss"),
    ("jmir-ai", "https://ai.jmir.org/feed/atom"),
    ("radiology-ai", "https://pubs.rsna.org/action/showFeed?type=etoc&feed=rss&jc=ai"),
]
```

with:

```python
# Medical journal feeds (verified to return entries via httpx + User-Agent).
MEDICAL_FEEDS = [
    ("nature-machine-intelligence", "https://www.nature.com/natmachintell.rss"),
    ("npj-digital-medicine", "https://www.nature.com/npjdigitalmed.rss"),
    ("jmir-ai", "https://ai.jmir.org/feed/atom"),
    ("jmir-medinform", "https://medinform.jmir.org/feed/atom"),
]

# AND-ed into every medico PubMed query to force the AI/medicine intersection.
MEDICAL_AI_CLAUSE = (
    '"Artificial Intelligence"[Mesh] OR "machine learning"[tiab] '
    'OR "deep learning"[tiab] OR "neural network*"[tiab] '
    'OR "large language model*"[tiab] OR "foundation model*"[tiab]'
)

# A medico result is kept only if its title/abstract contains one of these
# (word-boundary match). "ML" is intentionally absent — it matches "mL".
AI_TERMS = [
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "large language model", "foundation model", "transformer",
    "computer vision", "natural language processing", "radiomics", "generative",
    "diffusion model", "reinforcement learning", "convolutional",
    "predictive model", "AI", "LLM", "NLP",
]
```

Then change the `medico` entry in `PROFILES` from:

```python
    "medico": {
        "keywords": ["clinical LLM", "medical imaging", "diagnosis",
                     "radiology", "electronic health record"],
        "tags": ["medical-ai"],
    },
```

to:

```python
    "medico": {
        "keywords": ["clinical LLM", "medical imaging", "diagnosis",
                     "radiology", "electronic health record"],
        "tags": ["medical-ai"],
        "require_any": AI_TERMS,
    },
```

Then change the `medico` branch of `build_sources` from:

```python
    if profile == "medico":
        return [PubMedSource(),
                ArxivSource(("q-bio.QM", "cs.LG", "cs.CV")),
                RSSSource("medical", MEDICAL_FEEDS)]
```

to:

```python
    if profile == "medico":
        return [PubMedSource(and_clause=MEDICAL_AI_CLAUSE),
                ArxivSource(("q-bio.QM", "cs.LG", "cs.CV")),
                RSSSource("medical", MEDICAL_FEEDS)]
```

- [ ] **Step 4: Run the profiles test file to verify all pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_profiles.py -v`
Expected: PASS (new tests + existing `test_profiles_exist`, `test_build_sources_returns_source_objects`).

- [ ] **Step 5: Commit**

```bash
git add sotawhat/profiles.py tests/test_profiles.py
git commit -m "feat: focus medico profile on AI-medicine intersection"
```

---

## Task 6: Full suite, README note, end-to-end verification

**Files:**
- Modify: `README.md`
- Test: full suite + live run

- [ ] **Step 1: Run the full test suite**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: all tests PASS (prior suite + the new tests from Tasks 1–5).

- [ ] **Step 2: Add a README note about the medico focus**

In `README.md`, find the `medico` bullet:

```markdown
- `medico` — medical AI (PubMed, arXiv q-bio/CV/LG, medical-journal RSS).
```

Replace it with:

```markdown
- `medico` — AI∩medicine only. PubMed queries are AND-ed with an AI clause
  (MeSH "Artificial Intelligence" + recent ML/LLM phrases), and every result
  (PubMed, arXiv q-bio/CV/LG, medical-journal RSS) must mention an AI/ML term to
  be kept. Feeds: Nature Machine Intelligence, npj Digital Medicine, JMIR AI,
  JMIR Medical Informatics.
```

- [ ] **Step 3: Commit the docs**

```bash
git add README.md
git commit -m "docs: describe medico AI-medicine focus"
```

- [ ] **Step 4: End-to-end live run on a throwaway vault**

Run:
```bash
.\.venv\Scripts\sotawhat digest --profile medico --vault _tmp_vault --limit 5
```
Expected: prints a `[medico] filtered out N non-AI result(s)` line (N may be 0 if
all sources already returned AI papers) and `Digest 'medico': X found, Y new
note(s) written.` Confirm with:
```bash
.\.venv\Scripts\python -c "import pathlib,collections; c=collections.Counter(p.parent.name for p in pathlib.Path('_tmp_vault/medico').rglob('*.md')); print(dict(c))"
```
Expected: a dict showing notes by source. `nature-machine-intelligence` and/or
`npj-digital-medicine` should now be able to appear (the httpx fix), confirming
revived feeds. Spot-check 2–3 note titles look AI-related.

- [ ] **Step 5: Clean up**

```bash
rm -rf _tmp_vault
```

---

## Self-Review Notes

- **Spec coverage:** PubMed clause (Task 2 + 5), relevance filter (Tasks 1, 4, 5),
  robust RSS (Task 3), curated feeds (Task 5), shared matcher + backfill DRY
  (Task 1). All spec sections covered.
- **Type/name consistency:** `contains_term`/`contains_any` (textmatch) used by
  backfill `_matches` and digest `filter_relevant`; `and_clause` attribute on
  `PubMedSource` referenced by `profiles.test`; `require_any` key read by
  `run_digest`. Names consistent across tasks.
- **No network in unit tests:** PubMed (`_term`), RSS (monkeypatched `fetch_feed`),
  digest (`filter_relevant`), profiles (object inspection) are all offline. Only
  Task 6 Step 4 hits the network, as an explicit live verification.
