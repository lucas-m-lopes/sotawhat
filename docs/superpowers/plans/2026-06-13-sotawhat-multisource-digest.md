# sotawhat 2.0 — Multi-source Digest → Obsidian — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `sotawhat` into a robust multi-source AI/ML research aggregator that runs on demand and unattended, writing daily curated Markdown notes into a local Obsidian vault.

**Architecture:** Source-adapter pattern. Each source (arXiv API, Semantic Scholar, Hugging Face Daily Papers, PubMed, generic RSS) returns a normalized `Result`. A pure summarization module extracts metric/SOTA sentences. A `digest` command runs predefined profiles and writes one Markdown note per item (with cross-run dedup) into an Obsidian vault, scheduled daily via Windows Task Scheduler.

**Tech Stack:** Python 3.9+, `httpx`, `feedparser`, stdlib `xml.etree.ElementTree` / `html` / `dataclasses`, `pytest`. Removes `six`, `nltk`, `pyspellchecker`, `win-unicode-console`.

**Spec:** `docs/superpowers/specs/2026-06-13-sotawhat-multisource-digest-design.md`

---

## File Structure

```
pyproject.toml              # replaces setup.py; deps + console_scripts entry
sotawhat/
  __init__.py               # __VERSION__ (keep)
  models.py                 # Result dataclass
  summarize.py              # pure heuristic (no nltk/six)
  render.py                 # terminal output grouped by source
  profiles.py               # digest profiles + feed registries
  obsidian.py               # write one .md note per item + dedup index
  cli.py                    # argparse: search / digest subcommands
  sources/
    __init__.py
    base.py                 # Source base class + registry helpers
    arxiv.py                # official Atom API adapter
    semantic_scholar.py     # Graph API adapter
    hf_papers.py            # Daily Papers adapter
    pubmed.py               # E-utilities adapter
    rss.py                  # generic feedparser adapter
scripts/
  schedule_digest.ps1       # runs both profiles
tests/
  fixtures/                 # recorded API/RSS payloads
  test_summarize.py
  test_obsidian.py
  test_arxiv.py
  test_semantic_scholar.py
  test_hf_papers.py
  test_pubmed.py
  test_rss.py
  test_cli.py
```

The legacy `sotawhat/sotawhat.py` is removed at the end of Phase 1 once `cli.py` reaches behavioural parity.

---

## Phase 0: Project scaffolding & dependency modernization

### Task 0.1: Replace packaging with `pyproject.toml`

**Files:**
- Create: `pyproject.toml`
- Delete (later, Task 1.9): `setup.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "sotawhat"
version = "2.0.0"
description = "Multi-source AI/ML research aggregator with Obsidian digest"
requires-python = ">=3.9"
dependencies = [
    "httpx>=0.27",
    "feedparser>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
sotawhat = "sotawhat.cli:main"

[tool.setuptools.packages.find]
include = ["sotawhat*"]
```

- [ ] **Step 2: Bump version in `sotawhat/__init__.py`**

Read `sotawhat/__init__.py`; set the version constant to `2.0.0`. If it uses `__VERSION__`, keep that name:

```python
__VERSION__ = "2.0.0"
```

- [ ] **Step 3: Create a virtualenv and install dev deps**

Run (PowerShell):
```
python -m venv .venv; .\.venv\Scripts\python -m pip install -e ".[dev]"
```
Expected: installs httpx, feedparser, pytest, and `sotawhat` in editable mode without error.

- [ ] **Step 4: Add `.gitignore` entries**

Append to `.gitignore` (create if missing):
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.playwright-mcp/
```

- [ ] **Step 5: Commit**

```
git add pyproject.toml sotawhat/__init__.py .gitignore
git commit -m "chore: modern packaging (pyproject), drop legacy deps"
```

---

## Phase 1: Core engine at parity (models, summarize, arXiv API, render, CLI search)

### Task 1.1: `Result` model

**Files:**
- Create: `sotawhat/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from sotawhat.models import Result

def test_result_defaults_and_fields():
    r = Result(id="2401.00001", title="T", authors=["A"], date="2026-06-01",
               url="http://x/abs/2401.00001", abstract="abc", source="arxiv")
    assert r.id == "2401.00001"
    assert r.authors == ["A"]
    assert r.extra == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_models.py -v`
Expected: FAIL (`ModuleNotFoundError: sotawhat.models`).

- [ ] **Step 3: Implement**

```python
# sotawhat/models.py
from dataclasses import dataclass, field

@dataclass
class Result:
    id: str
    title: str
    authors: list
    date: str
    url: str
    abstract: str
    source: str
    extra: dict = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add sotawhat/models.py tests/test_models.py
git commit -m "feat: add normalized Result model"
```

### Task 1.2: Pure tokenizer + `is_float`/`is_citation_year`/`is_list_numer`

**Files:**
- Create: `sotawhat/summarize.py`
- Test: `tests/test_summarize.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_summarize.py
from sotawhat.summarize import tokenize, is_float, is_citation_year, is_list_numer

def test_tokenize_splits_words_and_punct():
    assert tokenize("BLEU of 2.3 (Vaswani, 2017).") == \
        ["BLEU", "of", "2.3", "(", "Vaswani", ",", "2017", ")", "."]

def test_is_float():
    assert is_float("2.3") is True
    assert is_float("23") is False

def test_is_citation_year():
    toks = ["(", "Vaswani", ",", "2017", ")"]
    assert is_citation_year(toks, 3) is True
    assert is_citation_year(["in", "2017", "we"], 1) is False

def test_is_list_numer():
    toks = ["(", "2", ")", "we"]
    assert is_list_numer(toks, 1, 2) is True
    assert is_list_numer(["x", "9", ")"], 1, 9) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_summarize.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# sotawhat/summarize.py
import re

_TOKEN_RE = re.compile(r"\w+(?:\.\w+)?|[^\w\s]")

def tokenize(text):
    """Lightweight word tokenizer replacing nltk.word_tokenize for our needs."""
    return _TOKEN_RE.findall(text)

def is_float(token):
    return re.match(r"^\d+?\.\d+?$", token) is not None

def is_citation_year(tokens, i):
    if len(tokens[i]) != 4:
        return False
    if re.match(r"[12][0-9]{3}", tokens[i]) is None:
        return False
    if i == 0 or i == len(tokens) - 1:
        return False
    if (tokens[i - 1] == "," or tokens[i - 1] == "(") and tokens[i + 1] == ")":
        return True
    return False

def is_list_numer(tokens, i, value):
    if value < 1 or value > 4:
        return False
    if i == len(tokens) - 1:
        return False
    if (i == 0 or tokens[i - 1] in {"(", ".", ":"}) and tokens[i + 1] == ")":
        return True
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_summarize.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add sotawhat/summarize.py tests/test_summarize.py
git commit -m "feat: pure tokenizer + numeric heuristics (no nltk)"
```

### Task 1.3: `has_number`, `contains_sota`, `extract_line`

**Files:**
- Modify: `sotawhat/summarize.py`
- Test: `tests/test_summarize.py`

- [ ] **Step 1: Write the failing test (append)**

```python
# append to tests/test_summarize.py
from sotawhat.summarize import has_number, contains_sota, extract_line

def test_has_number_ignores_citation_years():
    assert has_number("Proposed by Vaswani (2017)") is False
    assert has_number("We improve BLEU by 2.3 points") is True

def test_contains_sota():
    assert contains_sota("achieves state-of-the-art results") is True
    assert contains_sota("a normal sentence") is False

def test_extract_line_prefers_numeric_sentences():
    abstract = ("We study transformers. Our transformer improves BLEU by 2.3. "
                "It is nice.")
    text, has_num = extract_line(abstract, "transformer", 280)
    assert has_num is True
    assert "2.3" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_summarize.py -v`
Expected: FAIL (`ImportError: cannot import name 'has_number'`).

- [ ] **Step 3: Implement (append to `summarize.py`)**

```python
def has_number(sent):
    tokens = tokenize(sent)
    for i, token in enumerate(tokens):
        if token.endswith("\\"):
            token = token[:-2]
        if token.endswith("x"):
            token = token[:-1]
        if token.startswith("x"):
            token = token[1:]
        if token.startswith("$") and token.endswith("$"):
            token = token[1:-1]
        if is_float(token):
            return True
        try:
            value = int(token)
        except ValueError:
            continue
        if not is_citation_year(tokens, i) and not is_list_numer(tokens, i, value):
            return True
    return False

def contains_sota(sent):
    return ("state-of-the-art" in sent or "state of the art" in sent
            or "SOTA" in sent)

def extract_line(abstract, keyword, limit):
    lines = []
    numbered_lines = []
    kw_mentioned = False
    abstract = abstract.replace("et. al", "et al.")
    sentences = abstract.split(". ")
    kw_sentences = []
    for sent in sentences:
        if keyword in sent.lower():
            kw_mentioned = True
            if has_number(sent):
                numbered_lines.append(sent)
            elif contains_sota(sent):
                numbered_lines.append(sent)
            else:
                kw_sentences.append(sent)
                lines.append(sent)
            continue
        if kw_mentioned and has_number(sent):
            if not numbered_lines and kw_sentences:
                numbered_lines.append(kw_sentences[-1])
            numbered_lines.append(sent)
        if kw_mentioned and contains_sota(sent):
            lines.append(sent)
    if numbered_lines:
        return ". ".join(numbered_lines), True
    return ". ".join(lines[-2:]), False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_summarize.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add sotawhat/summarize.py tests/test_summarize.py
git commit -m "feat: port SOTA/metric summarization heuristic (pure)"
```

### Task 1.4: Source base class

**Files:**
- Create: `sotawhat/sources/__init__.py` (empty)
- Create: `sotawhat/sources/base.py`
- Test: `tests/test_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_base.py
import pytest
from sotawhat.sources.base import Source

def test_source_requires_search():
    class Incomplete(Source):
        name = "x"
    with pytest.raises(NotImplementedError):
        Incomplete().search("k", 1)

def test_safe_search_swallows_errors():
    class Boom(Source):
        name = "boom"
        def search(self, keyword, limit):
            raise RuntimeError("down")
    warnings = []
    out = Boom().safe_search("k", 1, on_error=warnings.append)
    assert out == []
    assert "boom" in warnings[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_base.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# sotawhat/sources/base.py
class Source:
    name = "base"

    def search(self, keyword, limit):
        raise NotImplementedError

    def safe_search(self, keyword, limit, on_error=None):
        try:
            return self.search(keyword, limit)
        except Exception as exc:  # noqa: BLE001 - a failing source must not abort the run
            if on_error:
                on_error(f"[{self.name}] failed: {exc}")
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_base.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add sotawhat/sources/__init__.py sotawhat/sources/base.py tests/test_base.py
git commit -m "feat: Source base with fault-isolating safe_search"
```

### Task 1.5: arXiv API adapter — record a fixture

**Files:**
- Create: `tests/fixtures/arxiv_transformer.xml`

- [ ] **Step 1: Fetch a real Atom response and save it**

Run (PowerShell):
```
.\.venv\Scripts\python -c "import httpx; open('tests/fixtures/arxiv_transformer.xml','w',encoding='utf-8').write(httpx.get('http://export.arxiv.org/api/query', params={'search_query':'all:transformer AND cat:cs.LG','start':0,'max_results':5,'sortBy':'submittedDate','sortOrder':'descending'}, timeout=30).text)"
```
Expected: writes a non-empty Atom XML file containing `<entry>` elements.

- [ ] **Step 2: Sanity check the fixture**

Run: `.\.venv\Scripts\python -c "print(open('tests/fixtures/arxiv_transformer.xml',encoding='utf-8').read()[:200])"`
Expected: starts with `<?xml` and an Atom `<feed>`.

- [ ] **Step 3: Commit**

```
git add tests/fixtures/arxiv_transformer.xml
git commit -m "test: record arXiv API fixture"
```

### Task 1.6: arXiv API adapter — parser

**Files:**
- Create: `sotawhat/sources/arxiv.py`
- Test: `tests/test_arxiv.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_arxiv.py
from sotawhat.sources.arxiv import parse_atom

def test_parse_atom_extracts_results():
    xml = open("tests/fixtures/arxiv_transformer.xml", encoding="utf-8").read()
    results = parse_atom(xml, source="arxiv")
    assert len(results) >= 1
    r = results[0]
    assert r.title
    assert r.authors
    assert r.url.startswith("http")
    assert r.abstract
    assert r.id  # arXiv id like 2401.00001
    assert r.source == "arxiv"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_arxiv.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# sotawhat/sources/arxiv.py
import xml.etree.ElementTree as ET
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_NS = {"atom": "http://www.w3.org/2005/Atom"}
_API = "http://export.arxiv.org/api/query"

def _arxiv_id(entry_id):
    # entry id looks like http://arxiv.org/abs/2401.00001v1
    tail = entry_id.rstrip("/").split("/abs/")[-1]
    return tail.split("v")[0]

def parse_atom(xml_text, source="arxiv"):
    root = ET.fromstring(xml_text)
    results = []
    for entry in root.findall("atom:entry", _NS):
        title = (entry.findtext("atom:title", default="", namespaces=_NS) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=_NS) or "").strip()
        published = entry.findtext("atom:published", default="", namespaces=_NS) or ""
        entry_id = entry.findtext("atom:id", default="", namespaces=_NS) or ""
        authors = [a.findtext("atom:name", default="", namespaces=_NS).strip()
                   for a in entry.findall("atom:author", _NS)]
        url = ""
        for link in entry.findall("atom:link", _NS):
            if link.get("rel") == "alternate":
                url = link.get("href", "")
        url = url or entry_id
        results.append(Result(
            id=_arxiv_id(entry_id), title=" ".join(title.split()),
            authors=authors, date=published[:10], url=url,
            abstract=" ".join(summary.split()), source=source))
    return results

class ArxivSource(Source):
    name = "arxiv"

    def __init__(self, categories=("cs.LG", "cs.CL", "cs.AI")):
        self.categories = categories

    def _query(self, keyword):
        cats = " OR ".join(f"cat:{c}" for c in self.categories)
        return f"all:{keyword} AND ({cats})"

    def search(self, keyword, limit):
        params = {"search_query": self._query(keyword), "start": 0,
                  "max_results": limit, "sortBy": "submittedDate",
                  "sortOrder": "descending"}
        resp = httpx.get(_API, params=params, timeout=30,
                         headers={"User-Agent": "sotawhat/2.0"})
        resp.raise_for_status()
        return parse_atom(resp.text, source=self.name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_arxiv.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add sotawhat/sources/arxiv.py tests/test_arxiv.py
git commit -m "feat: arXiv official API adapter"
```

### Task 1.7: Terminal renderer (grouped by source)

**Files:**
- Create: `sotawhat/render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render.py
from sotawhat.models import Result
from sotawhat.summarize import extract_line
from sotawhat.render import render_grouped

def _r(source, title):
    return Result(id=title, title=title, authors=["A B"], date="2026-06-01",
                  url="http://x/" + title, abstract="We improve X by 2.3.",
                  source=source)

def test_render_groups_by_source_with_headers():
    out = render_grouped([_r("arxiv", "P1"), _r("pubmed", "P2")], keyword="x")
    assert "arxiv" in out.lower()
    assert "pubmed" in out.lower()
    assert "P1" in out and "P2" in out
    assert "http://x/P1" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_render.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# sotawhat/render.py
from collections import OrderedDict
from sotawhat.summarize import extract_line

_SEP = "=" * 52

def _format_one(result, keyword):
    author = result.authors[0] if result.authors else "Unknown"
    headline = f"{result.title} ({author} - {result.date})"
    extract, _ = extract_line(result.abstract, keyword.lower(), 280)
    body = extract or result.abstract[:280]
    return f"{headline}\n{body}\nLink: {result.url}"

def render_grouped(results, keyword):
    by_source = OrderedDict()
    for r in results:
        by_source.setdefault(r.source, []).append(r)
    blocks = []
    for source, items in by_source.items():
        blocks.append(f"\n### {source} ({len(items)})\n")
        for item in items:
            blocks.append(_format_one(item, keyword))
            blocks.append(_SEP)
    return "\n".join(blocks).strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_render.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add sotawhat/render.py tests/test_render.py
git commit -m "feat: terminal renderer grouped by source"
```

### Task 1.8: CLI with `search` subcommand + backward compatibility

**Files:**
- Create: `sotawhat/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
from sotawhat.cli import parse_args

def test_parse_classic_keyword_and_number():
    ns = parse_args(["language", "model", "10"])
    assert ns.command == "search"
    assert ns.keyword == "language model"
    assert ns.num == 10

def test_parse_default_number():
    ns = parse_args(["transformer"])
    assert ns.keyword == "transformer"
    assert ns.num == 5

def test_parse_explicit_search():
    ns = parse_args(["search", "perplexity", "3"])
    assert ns.command == "search"
    assert ns.keyword == "perplexity"
    assert ns.num == 3

def test_parse_digest():
    ns = parse_args(["digest", "--profile", "medico", "--vault", "V"])
    assert ns.command == "digest"
    assert ns.profile == "medico"
    assert ns.vault == "V"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_cli.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement (search path only for now; digest handler added in Phase 3)**

```python
# sotawhat/cli.py
import argparse
import sys

_SUBCOMMANDS = {"search", "digest"}

def parse_args(argv):
    # Backward compat: `sotawhat <keyword...> [N]` with no subcommand -> search.
    if not argv:
        raise SystemExit("You must specify a keyword")
    if argv[0] not in _SUBCOMMANDS:
        argv = ["search"] + argv

    parser = argparse.ArgumentParser(prog="sotawhat")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search")
    p_search.add_argument("words", nargs="+")

    p_digest = sub.add_parser("digest")
    p_digest.add_argument("--profile", required=True)
    p_digest.add_argument("--vault", required=True)
    p_digest.add_argument("--limit", type=int, default=10)

    ns = parser.parse_args(argv)
    if ns.command == "search":
        words = ns.words
        num = 5
        if len(words) > 1:
            try:
                num = int(words[-1])
                words = words[:-1]
            except ValueError:
                pass
        ns.keyword = " ".join(words)
        ns.num = num
    return ns

def _run_search(ns):
    from sotawhat.sources.arxiv import ArxivSource
    from sotawhat.render import render_grouped
    warnings = []
    results = ArxivSource().safe_search(ns.keyword, ns.num, on_error=warnings.append)
    for w in warnings:
        print(w, file=sys.stderr)
    if not results:
        print(f"Sorry, we were unable to find anything for '{ns.keyword}'")
        return
    print(render_grouped(results, ns.keyword))

def main(argv=None):
    ns = parse_args(argv if argv is not None else sys.argv[1:])
    if ns.command == "search":
        _run_search(ns)
    elif ns.command == "digest":
        from sotawhat.digest import run_digest  # added in Phase 3
        run_digest(ns)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_cli.py -v`
Expected: PASS (digest import is lazy, so it doesn't break here).

- [ ] **Step 5: Manual smoke test (network)**

Run: `.\.venv\Scripts\sotawhat transformer 3`
Expected: prints an `### arxiv (3)` section with 3 results and links.

- [ ] **Step 6: Commit**

```
git add sotawhat/cli.py tests/test_cli.py
git commit -m "feat: CLI search subcommand with backward-compat parsing"
```

### Task 1.9: Remove legacy module

**Files:**
- Delete: `sotawhat/sotawhat.py`
- Delete: `setup.py`

- [ ] **Step 1: Delete legacy files**

Run: `git rm sotawhat/sotawhat.py setup.py`

- [ ] **Step 2: Verify nothing imports them**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: all tests pass; no import errors.

- [ ] **Step 3: Reinstall to refresh entry point**

Run: `.\.venv\Scripts\python -m pip install -e ".[dev]"`
Expected: `sotawhat` console script now points at `sotawhat.cli:main`.

- [ ] **Step 4: Commit**

```
git add -A
git commit -m "refactor: remove legacy scraper and setup.py"
```

---

## Phase 2: Additional source adapters

### Task 2.1: Semantic Scholar — fixture + adapter

**Files:**
- Create: `tests/fixtures/semantic_scholar_transformer.json`
- Create: `sotawhat/sources/semantic_scholar.py`
- Test: `tests/test_semantic_scholar.py`

- [ ] **Step 1: Record fixture**

Run:
```
.\.venv\Scripts\python -c "import httpx,io; r=httpx.get('https://api.semanticscholar.org/graph/v1/paper/search', params={'query':'transformer','limit':5,'fields':'title,abstract,authors,year,url,externalIds,publicationDate'}, timeout=30, headers={'User-Agent':'sotawhat/2.0'}); open('tests/fixtures/semantic_scholar_transformer.json','w',encoding='utf-8').write(r.text)"
```
Expected: writes JSON with a `data` array. (If rate-limited, retry after a minute.)

- [ ] **Step 2: Write the failing test**

```python
# tests/test_semantic_scholar.py
import json
from sotawhat.sources.semantic_scholar import parse_response

def test_parse_semantic_scholar():
    payload = json.load(open("tests/fixtures/semantic_scholar_transformer.json", encoding="utf-8"))
    results = parse_response(payload)
    assert len(results) >= 1
    r = results[0]
    assert r.source == "semantic_scholar"
    assert r.title
    assert r.id  # paperId or DOI
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_semantic_scholar.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 4: Implement**

```python
# sotawhat/sources/semantic_scholar.py
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_API = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,abstract,authors,year,url,externalIds,publicationDate"

def parse_response(payload):
    results = []
    for p in payload.get("data", []):
        ext = p.get("externalIds") or {}
        pid = ext.get("DOI") or p.get("paperId") or p.get("url") or ""
        authors = [a.get("name", "") for a in (p.get("authors") or [])]
        date = p.get("publicationDate") or (str(p.get("year")) if p.get("year") else "")
        results.append(Result(
            id=str(pid), title=p.get("title") or "", authors=authors,
            date=date or "", url=p.get("url") or "",
            abstract=p.get("abstract") or "", source="semantic_scholar"))
    return results

class SemanticScholarSource(Source):
    name = "semantic_scholar"

    def search(self, keyword, limit):
        params = {"query": keyword, "limit": limit, "fields": _FIELDS}
        resp = httpx.get(_API, params=params, timeout=30,
                         headers={"User-Agent": "sotawhat/2.0"})
        resp.raise_for_status()
        return parse_response(resp.json())
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_semantic_scholar.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```
git add sotawhat/sources/semantic_scholar.py tests/test_semantic_scholar.py tests/fixtures/semantic_scholar_transformer.json
git commit -m "feat: Semantic Scholar adapter"
```

### Task 2.2: Hugging Face Daily Papers — fixture + adapter

**Files:**
- Create: `tests/fixtures/hf_daily_papers.json`
- Create: `sotawhat/sources/hf_papers.py`
- Test: `tests/test_hf_papers.py`

- [ ] **Step 1: Record fixture**

Run:
```
.\.venv\Scripts\python -c "import httpx; r=httpx.get('https://huggingface.co/api/daily_papers', params={'limit':30}, timeout=30, headers={'User-Agent':'sotawhat/2.0'}); open('tests/fixtures/hf_daily_papers.json','w',encoding='utf-8').write(r.text)"
```
Expected: writes a JSON array of daily-paper objects, each with a `paper` field.

- [ ] **Step 2: Inspect one record's shape**

Run: `.\.venv\Scripts\python -c "import json; d=json.load(open('tests/fixtures/hf_daily_papers.json',encoding='utf-8')); print(list(d[0].keys())); print(list(d[0]['paper'].keys()))"`
Expected: prints keys; confirm presence of `paper.id`, `paper.title`, `paper.summary`, `paper.authors`, `publishedAt`. Adjust field names in Step 4 if they differ.

- [ ] **Step 3: Write the failing test**

```python
# tests/test_hf_papers.py
import json
from sotawhat.sources.hf_papers import parse_response, HFPapersSource

def test_parse_and_filter():
    payload = json.load(open("tests/fixtures/hf_daily_papers.json", encoding="utf-8"))
    results = parse_response(payload)
    assert len(results) >= 1
    assert results[0].source == "hf_papers"
    # client-side keyword filter
    filtered = HFPapersSource._filter(results, "model", 50)
    assert all("model" in (r.title + r.abstract).lower() for r in filtered)
```

- [ ] **Step 4: Implement**

```python
# sotawhat/sources/hf_papers.py
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_API = "https://huggingface.co/api/daily_papers"

def parse_response(payload):
    results = []
    for item in payload:
        paper = item.get("paper") or {}
        pid = paper.get("id") or ""
        authors = [a.get("name", "") for a in (paper.get("authors") or [])]
        url = f"https://huggingface.co/papers/{pid}" if pid else ""
        results.append(Result(
            id=str(pid), title=paper.get("title") or "", authors=authors,
            date=(item.get("publishedAt") or "")[:10], url=url,
            abstract=paper.get("summary") or "", source="hf_papers"))
    return results

class HFPapersSource(Source):
    name = "hf_papers"

    @staticmethod
    def _filter(results, keyword, limit):
        kw = keyword.lower()
        hits = [r for r in results if kw in (r.title + " " + r.abstract).lower()]
        return hits[:limit]

    def search(self, keyword, limit):
        resp = httpx.get(_API, params={"limit": 100}, timeout=30,
                         headers={"User-Agent": "sotawhat/2.0"})
        resp.raise_for_status()
        results = parse_response(resp.json())
        return self._filter(results, keyword, limit)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_hf_papers.py -v`
Expected: PASS. If Step 2 showed different field names, fix `parse_response` and rerun.

- [ ] **Step 6: Commit**

```
git add sotawhat/sources/hf_papers.py tests/test_hf_papers.py tests/fixtures/hf_daily_papers.json
git commit -m "feat: Hugging Face Daily Papers adapter"
```

### Task 2.3: PubMed E-utilities — fixtures + adapter

**Files:**
- Create: `tests/fixtures/pubmed_esearch.json`, `tests/fixtures/pubmed_efetch.xml`
- Create: `sotawhat/sources/pubmed.py`
- Test: `tests/test_pubmed.py`

- [ ] **Step 1: Record fixtures**

Run:
```
.\.venv\Scripts\python -c "import httpx,json; s=httpx.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi', params={'db':'pubmed','term':'artificial intelligence AND radiology','retmax':5,'retmode':'json','sort':'date'}, timeout=30); open('tests/fixtures/pubmed_esearch.json','w',encoding='utf-8').write(s.text); ids=','.join(s.json()['esearchresult']['idlist']); f=httpx.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi', params={'db':'pubmed','id':ids,'retmode':'xml'}, timeout=30); open('tests/fixtures/pubmed_efetch.xml','w',encoding='utf-8').write(f.text)"
```
Expected: esearch JSON with an `idlist`; efetch XML with `<PubmedArticle>` elements.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_pubmed.py
from sotawhat.sources.pubmed import parse_efetch

def test_parse_efetch():
    xml = open("tests/fixtures/pubmed_efetch.xml", encoding="utf-8").read()
    results = parse_efetch(xml)
    assert len(results) >= 1
    r = results[0]
    assert r.source == "pubmed"
    assert r.title
    assert r.url.startswith("https://pubmed.ncbi.nlm.nih.gov/")
    assert r.id  # PMID
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_pubmed.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 4: Implement**

```python
# sotawhat/sources/pubmed.py
import xml.etree.ElementTree as ET
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_TOOL = "sotawhat"
_EMAIL = "sotawhat@example.com"  # NOTE: replace with the user's email at install time

def _text(node):
    return "".join(node.itertext()).strip() if node is not None else ""

def parse_efetch(xml_text):
    root = ET.fromstring(xml_text)
    results = []
    for art in root.findall(".//PubmedArticle"):
        pmid = _text(art.find(".//PMID"))
        title = _text(art.find(".//ArticleTitle"))
        abstract = " ".join(_text(a) for a in art.findall(".//Abstract/AbstractText")).strip()
        authors = []
        for a in art.findall(".//AuthorList/Author"):
            last = _text(a.find("LastName"))
            fore = _text(a.find("ForeName"))
            name = (f"{fore} {last}").strip()
            if name:
                authors.append(name)
        year = _text(art.find(".//PubDate/Year"))
        results.append(Result(
            id=pmid, title=title, authors=authors, date=year,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            abstract=abstract, source="pubmed"))
    return results

class PubMedSource(Source):
    name = "pubmed"

    def search(self, keyword, limit):
        s = httpx.get(_ESEARCH, params={
            "db": "pubmed", "term": keyword, "retmax": limit,
            "retmode": "json", "sort": "date", "tool": _TOOL, "email": _EMAIL},
            timeout=30)
        s.raise_for_status()
        ids = s.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        f = httpx.get(_EFETCH, params={
            "db": "pubmed", "id": ",".join(ids), "retmode": "xml",
            "tool": _TOOL, "email": _EMAIL}, timeout=30)
        f.raise_for_status()
        return parse_efetch(f.text)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_pubmed.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```
git add sotawhat/sources/pubmed.py tests/test_pubmed.py tests/fixtures/pubmed_esearch.json tests/fixtures/pubmed_efetch.xml
git commit -m "feat: PubMed E-utilities adapter"
```

### Task 2.4: Generic RSS adapter

**Files:**
- Create: `tests/fixtures/sample_feed.xml`
- Create: `sotawhat/sources/rss.py`
- Test: `tests/test_rss.py`

- [ ] **Step 1: Create a small static RSS fixture**

Create `tests/fixtures/sample_feed.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Lab Blog</title>
  <item>
    <title>A new transformer model</title>
    <link>https://lab.example/post1</link>
    <description>We present a transformer improving accuracy by 3.1 points.</description>
    <pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate>
    <author>alice@lab.example (Alice)</author>
  </item>
  <item>
    <title>Unrelated cooking post</title>
    <link>https://lab.example/post2</link>
    <description>How to bake bread.</description>
    <pubDate>Tue, 02 Jun 2026 10:00:00 GMT</pubDate>
  </item>
</channel></rss>
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_rss.py
from sotawhat.sources.rss import parse_feed, RSSSource

def test_parse_feed_maps_and_filters():
    results = parse_feed("tests/fixtures/sample_feed.xml", source="rss:lab")
    assert len(results) == 2
    filtered = RSSSource._filter(results, "transformer", 10)
    assert len(filtered) == 1
    assert filtered[0].url == "https://lab.example/post1"
    assert filtered[0].source == "rss:lab"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_rss.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 4: Implement**

```python
# sotawhat/sources/rss.py
import feedparser
from sotawhat.models import Result
from sotawhat.sources.base import Source

def parse_feed(url_or_path, source):
    feed = feedparser.parse(url_or_path)
    results = []
    for e in feed.entries:
        summary = getattr(e, "summary", "") or ""
        authors = []
        if getattr(e, "author", ""):
            authors = [e.author]
        link = getattr(e, "link", "")
        results.append(Result(
            id=link or getattr(e, "id", "") or getattr(e, "title", ""),
            title=getattr(e, "title", ""), authors=authors,
            date=getattr(e, "published", "")[:16], url=link,
            abstract=summary, source=source))
    return results

class RSSSource(Source):
    def __init__(self, name, feeds):
        # feeds: list of (label, url)
        self.name = name
        self.feeds = feeds

    @staticmethod
    def _filter(results, keyword, limit):
        kw = keyword.lower()
        hits = [r for r in results if kw in (r.title + " " + r.abstract).lower()]
        return hits[:limit]

    def search(self, keyword, limit):
        collected = []
        for label, url in self.feeds:
            collected.extend(parse_feed(url, source=f"rss:{label}"))
        return self._filter(collected, keyword, limit)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_rss.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```
git add sotawhat/sources/rss.py tests/test_rss.py tests/fixtures/sample_feed.xml
git commit -m "feat: generic RSS adapter"
```

---

## Phase 3: Digest command + profiles

### Task 3.1: Profiles & feed registry

**Files:**
- Create: `sotawhat/profiles.py`
- Test: `tests/test_profiles.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_profiles.py
from sotawhat.profiles import PROFILES, build_sources

def test_profiles_exist():
    assert set(PROFILES) == {"geral", "medico"}
    assert PROFILES["medico"]["keywords"]

def test_build_sources_returns_source_objects():
    sources = build_sources("geral")
    names = [s.name for s in sources]
    assert "arxiv" in names
    assert all(hasattr(s, "search") for s in sources)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_profiles.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# sotawhat/profiles.py
from sotawhat.sources.arxiv import ArxivSource
from sotawhat.sources.semantic_scholar import SemanticScholarSource
from sotawhat.sources.hf_papers import HFPapersSource
from sotawhat.sources.pubmed import PubMedSource
from sotawhat.sources.rss import RSSSource

# Lab/blog feeds (general). URLs pinned here; unreachable feeds are skipped at runtime.
LAB_FEEDS = [
    ("google-research", "https://research.google/blog/rss/"),
    ("deepmind", "https://deepmind.google/blog/rss.xml"),
    ("bair", "https://bair.berkeley.edu/blog/feed.xml"),
    ("huggingface", "https://huggingface.co/blog/feed.xml"),
    ("the-gradient", "https://thegradient.pub/rss/"),
    ("ahead-of-ai", "https://magazine.sebastianraschka.com/feed"),
    ("simon-willison", "https://simonwillison.net/atom/everything/"),
    ("marktechpost", "https://www.marktechpost.com/feed/"),
]

# Medical journal feeds.
MEDICAL_FEEDS = [
    ("nature-machine-intelligence", "https://www.nature.com/natmachintell.rss"),
    ("jmir-ai", "https://ai.jmir.org/feed/atom"),
    ("radiology-ai", "https://pubs.rsna.org/action/showFeed?type=etoc&feed=rss&jc=ai"),
]

PROFILES = {
    "geral": {
        "keywords": ["large language model", "reinforcement learning",
                     "diffusion model", "agent"],
        "tags": ["ml-ai"],
    },
    "medico": {
        "keywords": ["clinical LLM", "medical imaging", "diagnosis",
                     "radiology", "electronic health record"],
        "tags": ["medical-ai"],
    },
}

def build_sources(profile):
    if profile == "geral":
        return [ArxivSource(("cs.LG", "cs.CL", "cs.AI")),
                SemanticScholarSource(), HFPapersSource(),
                RSSSource("labs", LAB_FEEDS)]
    if profile == "medico":
        return [PubMedSource(),
                ArxivSource(("q-bio.QM", "cs.LG", "cs.CV")),
                RSSSource("medical", MEDICAL_FEEDS)]
    raise KeyError(f"Unknown profile: {profile}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_profiles.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add sotawhat/profiles.py tests/test_profiles.py
git commit -m "feat: digest profiles and feed registry"
```

### Task 3.2: Digest orchestration (collect → dedupe in-run → return)

**Files:**
- Create: `sotawhat/digest.py`
- Test: `tests/test_digest.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_digest.py
from sotawhat.models import Result
from sotawhat.digest import collect

class FakeSource:
    def __init__(self, name, items):
        self.name = name
        self._items = items
    def safe_search(self, keyword, limit, on_error=None):
        return self._items

def _r(rid, source):
    return Result(id=rid, title=rid, authors=[], date="2026-06-01",
                  url="u/" + rid, abstract="a", source=source)

def test_collect_dedupes_by_id_across_keywords():
    src = FakeSource("arxiv", [_r("1", "arxiv"), _r("1", "arxiv"), _r("2", "arxiv")])
    out = collect([src], keywords=["k1", "k2"], limit=10)
    ids = sorted(r.id for r in out)
    assert ids == ["1", "2"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_digest.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement (digest.run_digest references obsidian.write_notes added in Phase 4 — keep import lazy)**

```python
# sotawhat/digest.py
import sys

def collect(sources, keywords, limit, on_error=None):
    seen = set()
    out = []
    for source in sources:
        for kw in keywords:
            for r in source.safe_search(kw, limit, on_error=on_error):
                if r.id in seen:
                    continue
                seen.add(r.id)
                out.append(r)
    return out

def run_digest(ns):
    from sotawhat.profiles import PROFILES, build_sources
    from sotawhat.obsidian import write_notes  # Phase 4
    if ns.profile not in PROFILES:
        raise SystemExit(f"Unknown profile '{ns.profile}'. "
                         f"Choose from: {', '.join(PROFILES)}")
    profile = PROFILES[ns.profile]
    sources = build_sources(ns.profile)
    warnings = []
    results = collect(sources, profile["keywords"], ns.limit,
                      on_error=warnings.append)
    for w in warnings:
        print(w, file=sys.stderr)
    written = write_notes(results, vault=ns.vault, profile_name=ns.profile,
                          tags=profile["tags"], keywords=profile["keywords"])
    print(f"Digest '{ns.profile}': {len(results)} found, {written} new note(s) written.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_digest.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add sotawhat/digest.py tests/test_digest.py
git commit -m "feat: digest collection with in-run dedup"
```

---

## Phase 4: Obsidian output + cross-run dedup

### Task 4.1: Title sanitization

**Files:**
- Create: `sotawhat/obsidian.py`
- Test: `tests/test_obsidian.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_obsidian.py
from sotawhat.obsidian import sanitize_title

def test_sanitize_strips_invalid_windows_chars():
    assert sanitize_title('A:Model/With\\Bad?*"<>|chars') == "A-Model-With-Bad-chars"

def test_sanitize_truncates_and_trims():
    assert sanitize_title("  spaced  ") == "spaced"
    assert len(sanitize_title("x" * 200)) <= 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_obsidian.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

```python
# sotawhat/obsidian.py
import json
import re
from pathlib import Path

_INVALID = re.compile(r'[:/\\?*"<>|]+')

def sanitize_title(title):
    cleaned = _INVALID.sub("-", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    return cleaned[:100]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_obsidian.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add sotawhat/obsidian.py tests/test_obsidian.py
git commit -m "feat: Obsidian filename sanitization"
```

### Task 4.2: Note rendering (frontmatter + body)

**Files:**
- Modify: `sotawhat/obsidian.py`
- Test: `tests/test_obsidian.py`

- [ ] **Step 1: Write the failing test (append)**

```python
# append to tests/test_obsidian.py
from sotawhat.models import Result
from sotawhat.obsidian import render_note

def test_render_note_has_frontmatter_and_link():
    r = Result(id="2401.1", title="Cool: Model", authors=["A B", "C D"],
               date="2026-06-01", url="http://x/abs/2401.1",
               abstract="We improve BLEU by 2.3 points. More text.",
               source="arxiv")
    note = render_note(r, tags=["ml-ai"], keywords=["model"], added="2026-06-13")
    assert note.startswith("---\n")
    assert 'title: "Cool: Model"' in note
    assert "source: arxiv" in note
    assert "#ml-ai" in note or "ml-ai" in note
    assert "http://x/abs/2401.1" in note
    assert "2.3" in note  # summarized extract present
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_obsidian.py -v`
Expected: FAIL (`ImportError: cannot import name 'render_note'`).

- [ ] **Step 3: Implement (append to `obsidian.py`)**

```python
from sotawhat.summarize import extract_line

def _yaml_list(values):
    return "[" + ", ".join(json.dumps(v) for v in values) + "]"

def render_note(result, tags, keywords, added):
    all_tags = list(tags) + [f"source/{result.source}"]
    extract, _ = extract_line(result.abstract, (keywords[0] if keywords else "").lower(), 280)
    body = extract or result.abstract
    front = (
        "---\n"
        f'title: {json.dumps(result.title)}\n'
        f"authors: {_yaml_list(result.authors)}\n"
        f"date: {json.dumps(result.date)}\n"
        f"source: {result.source}\n"
        f"url: {json.dumps(result.url)}\n"
        f"keywords: {_yaml_list(keywords)}\n"
        f"tags: {_yaml_list(all_tags)}\n"
        f"added: {json.dumps(added)}\n"
        "---\n\n"
    )
    return f"{front}# {result.title}\n\n{body}\n\n[Source]({result.url})\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_obsidian.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add sotawhat/obsidian.py tests/test_obsidian.py
git commit -m "feat: Obsidian note rendering with YAML frontmatter"
```

### Task 4.3: `write_notes` with cross-run dedup index

**Files:**
- Modify: `sotawhat/obsidian.py`
- Test: `tests/test_obsidian.py`

- [ ] **Step 1: Write the failing test (append)**

```python
# append to tests/test_obsidian.py
from sotawhat.obsidian import write_notes

def test_write_notes_dedupes_across_runs(tmp_path):
    r = Result(id="2401.1", title="M One", authors=["A"], date="2026-06-01",
               url="u1", abstract="We improve by 2.3.", source="arxiv")
    n1 = write_notes([r], vault=str(tmp_path), profile_name="geral",
                     tags=["ml-ai"], keywords=["model"], added="2026-06-13")
    n2 = write_notes([r], vault=str(tmp_path), profile_name="geral",
                     tags=["ml-ai"], keywords=["model"], added="2026-06-14")
    assert n1 == 1
    assert n2 == 0  # already seen -> not rewritten
    md = list(tmp_path.rglob("*.md"))
    assert len(md) == 1
    seen = (tmp_path / ".sotawhat_seen.json")
    assert seen.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_obsidian.py -v`
Expected: FAIL (`ImportError: cannot import name 'write_notes'`).

- [ ] **Step 3: Implement (append to `obsidian.py`)**

```python
def _load_seen(vault_path):
    f = vault_path / ".sotawhat_seen.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}

def _save_seen(vault_path, seen):
    (vault_path / ".sotawhat_seen.json").write_text(
        json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")

def write_notes(results, vault, profile_name, tags, keywords, added="unknown"):
    vault_path = Path(vault)
    vault_path.mkdir(parents=True, exist_ok=True)
    seen = _load_seen(vault_path)
    written = 0
    for r in results:
        if r.id in seen:
            continue
        folder = vault_path / profile_name / r.source.replace(":", "-")
        folder.mkdir(parents=True, exist_ok=True)
        fname = f"{(r.date or added)[:10]}-{sanitize_title(r.title) or r.id}.md"
        path = folder / fname
        path.write_text(render_note(r, tags, keywords, added), encoding="utf-8")
        seen[r.id] = str(path.relative_to(vault_path))
        written += 1
    _save_seen(vault_path, seen)
    return written
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python -m pytest tests/test_obsidian.py -v`
Expected: PASS.

- [ ] **Step 5: Wire `added` date in `digest.run_digest`**

In `sotawhat/digest.py`, compute today's date string and pass it through. Modify `run_digest` to build `added` from the system date and pass `added=` to `write_notes`:

```python
# at top of digest.py
from datetime import date

# inside run_digest, replace the write_notes call:
    written = write_notes(results, vault=ns.vault, profile_name=ns.profile,
                          tags=profile["tags"], keywords=profile["keywords"],
                          added=date.today().isoformat())
```

- [ ] **Step 6: Run full suite**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 7: Manual end-to-end (network) into a temp vault**

Run: `.\.venv\Scripts\sotawhat digest --profile geral --vault .\_tmp_vault --limit 3`
Expected: prints `Digest 'geral': N found, M new note(s) written.` and `_tmp_vault/geral/<source>/*.md` files exist with frontmatter. Then delete `_tmp_vault`.

- [ ] **Step 8: Commit**

```
git add sotawhat/obsidian.py sotawhat/digest.py tests/test_obsidian.py
git commit -m "feat: write Obsidian notes with cross-run dedup"
```

---

## Phase 5: Scheduling (Windows Task Scheduler)

### Task 5.1: Digest runner script

**Files:**
- Create: `scripts/schedule_digest.ps1`

- [ ] **Step 1: Create the script**

```powershell
# scripts/schedule_digest.ps1
param(
    [string]$Vault = "D:\Lucas\obsidian_vaults\ml_ai_med_vault",
    [string]$Python = "$PSScriptRoot\..\.venv\Scripts\sotawhat.exe",
    [int]$Limit = 10
)
& $Python digest --profile geral  --vault $Vault --limit $Limit
& $Python digest --profile medico --vault $Vault --limit $Limit
```

- [ ] **Step 2: Manual test (network)**

Run: `powershell -ExecutionPolicy Bypass -File scripts\schedule_digest.ps1 -Vault .\_tmp_vault -Limit 2`
Expected: two digest lines printed; notes written under `_tmp_vault\geral` and `_tmp_vault\medico`. Delete `_tmp_vault` afterward.

- [ ] **Step 3: Commit**

```
git add scripts/schedule_digest.ps1
git commit -m "feat: digest runner script for both profiles"
```

### Task 5.2: Register the daily task (user-confirmed)

**Files:**
- Modify: `README.md` (document the command)

- [ ] **Step 1: Document the `schtasks` command in README**

Add a "Scheduled daily digest" section to `README.md` with:

```
schtasks /Create /SC DAILY /ST 08:00 /TN "sotawhat-digest" ^
  /TR "powershell -ExecutionPolicy Bypass -File \"D:\Lucas\code_projects\sotawhat\scripts\schedule_digest.ps1\""
```
and the removal command: `schtasks /Delete /TN "sotawhat-digest" /F`.

- [ ] **Step 2: Ask the user to confirm before creating the task**

Do NOT run `schtasks /Create` automatically. Present the command and ask the user to confirm. Only run it after explicit approval. After creation, verify with:

Run: `schtasks /Query /TN "sotawhat-digest"`
Expected: shows the task scheduled daily at 08:00.

- [ ] **Step 3: Commit**

```
git add README.md
git commit -m "docs: document daily digest scheduling"
```

---

## Phase 6: Docs & final polish

### Task 6.1: Update README usage

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Rewrite usage section**

Document: install via `pip install -e .`, `sotawhat <keyword> [N]` (classic), `sotawhat search ...`, `sotawhat digest --profile geral|medico --vault <path>`, the source list, and that nltk/punkt are no longer required.

- [ ] **Step 2: Run the full suite one last time**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: all green.

- [ ] **Step 3: Commit**

```
git add README.md
git commit -m "docs: update README for sotawhat 2.0"
```

---

## Verification checklist (end of implementation)

- [ ] `pytest -q` all green (no network needed — adapters tested against fixtures).
- [ ] `sotawhat transformer 3` prints grouped arXiv results.
- [ ] `sotawhat digest --profile geral --vault <tmp>` writes notes; rerun writes 0 new (dedup works).
- [ ] `sotawhat digest --profile medico --vault <tmp>` writes PubMed/arXiv/medical notes.
- [ ] Notes contain valid YAML frontmatter and open cleanly in Obsidian.
- [ ] PubMed `_EMAIL` replaced with the user's real email (`lmlopes33@gmail.com`).
- [ ] Scheduled task created only after user confirmation.
