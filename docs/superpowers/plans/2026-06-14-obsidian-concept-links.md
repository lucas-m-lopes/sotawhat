# Obsidian Concept Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect digest notes into thematic clusters in the Obsidian graph by linking each paper to per-keyword concept notes, with a backfill command for existing notes.

**Architecture:** `collect()` records which search keyword(s) surfaced each result into `Result.extra["concepts"]`. `render_note()` emits a `**Conceitos:** [[...]]` wikilink line. `write_notes()` creates stub concept notes under `<vault>/concepts/`. A new `backfill.py` module + `backfill-links` CLI subcommand retro-links existing notes via word-boundary content scan.

**Tech Stack:** Python 3.9+, stdlib only (`re`, `pathlib`, `json`), pytest.

---

## File Structure

- `sotawhat/digest.py` — modify `collect()` to record concept provenance.
- `sotawhat/obsidian.py` — add `_concept_line()`, `ensure_concept_notes()`; wire concept line into `render_note()`; call `ensure_concept_notes()` from `write_notes()`.
- `sotawhat/backfill.py` — NEW. Content-scan backfill logic + `run_backfill(ns)`.
- `sotawhat/cli.py` — register `backfill-links` subcommand.
- `tests/test_digest.py`, `tests/test_obsidian.py`, `tests/test_backfill.py` (new), `tests/test_cli.py` — tests.
- `README.md` — document concept links + backfill.

---

## Task 1: Record concept provenance in `collect()`

**Files:**
- Modify: `sotawhat/digest.py:5-15`
- Test: `tests/test_digest.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_digest.py`:

```python
def test_collect_records_concepts_per_id():
    src = FakeSource("arxiv", [_r("1", "arxiv"), _r("2", "arxiv")])
    out = collect([src], keywords=["k1", "k2"], limit=10)
    by_id = {r.id: r for r in out}
    assert by_id["1"].extra["concepts"] == ["k1", "k2"]
    assert by_id["2"].extra["concepts"] == ["k1", "k2"]
```

(The existing `FakeSource` returns the same items for every keyword, so each id is
surfaced under both `k1` and `k2`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python -m pytest tests/test_digest.py::test_collect_records_concepts_per_id -v`
Expected: FAIL with `KeyError: 'concepts'`.

- [ ] **Step 3: Write minimal implementation**

Replace the body of `collect` in `sotawhat/digest.py` with:

```python
def collect(sources, keywords, limit, on_error=None):
    by_id = {}
    out = []
    for source in sources:
        for kw in keywords:
            for r in source.safe_search(kw, limit, on_error=on_error):
                if r.id in by_id:
                    concepts = by_id[r.id].extra.setdefault("concepts", [])
                    if kw not in concepts:
                        concepts.append(kw)
                    continue
                r.extra.setdefault("concepts", [])
                if kw not in r.extra["concepts"]:
                    r.extra["concepts"].append(kw)
                by_id[r.id] = r
                out.append(r)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_digest.py -v`
Expected: PASS (both the new test and the existing `test_collect_dedupes_by_id_across_keywords`).

- [ ] **Step 5: Commit**

```bash
git add sotawhat/digest.py tests/test_digest.py
git commit -m "feat: record concept provenance in collect()"
```

---

## Task 2: Render the concept wikilink line

**Files:**
- Modify: `sotawhat/obsidian.py:18-34`
- Test: `tests/test_obsidian.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_obsidian.py`:

```python
def test_render_note_includes_concepts_when_present():
    r = Result(id="1", title="T", authors=[], date="2026-06-01", url="u",
               abstract="We improve BLEU by 2.3 points.", source="arxiv",
               extra={"concepts": ["large language model", "agent"]})
    note = render_note(r, tags=["ml-ai"], keywords=["model"], added="2026-06-13")
    assert "**Conceitos:** [[large language model]] · [[agent]]" in note
    assert note.index("Conceitos") < note.index("[Source]")

def test_render_note_omits_concepts_when_absent():
    r = Result(id="1", title="T", authors=[], date="2026-06-01", url="u",
               abstract="abc", source="arxiv")
    note = render_note(r, tags=["ml-ai"], keywords=["model"], added="2026-06-13")
    assert "Conceitos" not in note
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests/test_obsidian.py -k concepts -v`
Expected: `test_render_note_includes_concepts_when_present` FAILS (no Conceitos line);
`test_render_note_omits_concepts_when_absent` passes already.

- [ ] **Step 3: Write minimal implementation**

In `sotawhat/obsidian.py`, add this helper above `render_note`:

```python
def _concept_line(concepts):
    if not concepts:
        return ""
    links = " · ".join(f"[[{c}]]" for c in concepts)
    return f"**Conceitos:** {links}\n\n"
```

Then change the last two lines of `render_note` from:

```python
    return f"{front}# {result.title}\n\n{body}\n\n[Source]({result.url})\n"
```

to:

```python
    concepts = result.extra.get("concepts", [])
    return (f"{front}# {result.title}\n\n{body}\n\n"
            f"{_concept_line(concepts)}[Source]({result.url})\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_obsidian.py -v`
Expected: PASS (new tests + existing render/dedup tests still green).

- [ ] **Step 5: Commit**

```bash
git add sotawhat/obsidian.py tests/test_obsidian.py
git commit -m "feat: render concept wikilink line in notes"
```

---

## Task 3: Create concept stub notes from `write_notes()`

**Files:**
- Modify: `sotawhat/obsidian.py` (add `ensure_concept_notes`, call it in `write_notes`)
- Test: `tests/test_obsidian.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_obsidian.py`:

```python
def test_write_notes_creates_concept_stubs(tmp_path):
    r = Result(id="c1", title="M", authors=[], date="2026-06-01", url="u",
               abstract="a", source="arxiv", extra={"concepts": ["agent"]})
    write_notes([r], vault=str(tmp_path), profile_name="geral",
                tags=["ml-ai"], keywords=["agent"], added="2026-06-13")
    stub = tmp_path / "concepts" / "agent.md"
    assert stub.exists()
    text = stub.read_text(encoding="utf-8")
    assert "type: concept" in text
    assert "# agent" in text

def test_ensure_concept_notes_idempotent(tmp_path):
    from sotawhat.obsidian import ensure_concept_notes
    n1 = ensure_concept_notes(tmp_path, ["agent"])
    (tmp_path / "concepts" / "agent.md").write_text("custom", encoding="utf-8")
    n2 = ensure_concept_notes(tmp_path, ["agent"])
    assert n1 == 1
    assert n2 == 0
    assert (tmp_path / "concepts" / "agent.md").read_text(encoding="utf-8") == "custom"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests/test_obsidian.py -k "concept_stubs or idempotent" -v`
Expected: FAIL — `ensure_concept_notes` does not exist / stub not created.

- [ ] **Step 3: Write minimal implementation**

In `sotawhat/obsidian.py`, add near the top (after `_INVALID`):

```python
_CONCEPT_FRONT = "---\ntype: concept\ntags: [concept]\n---\n"
```

Add this function (e.g. after `sanitize_title`):

```python
def ensure_concept_notes(vault_path, concepts):
    folder = Path(vault_path) / "concepts"
    created = 0
    for c in concepts:
        path = folder / f"{sanitize_title(c)}.md"
        if path.exists():
            continue
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{_CONCEPT_FRONT}# {c}\n", encoding="utf-8")
        created += 1
    return created
```

In `write_notes`, track concepts and create stubs. Change the loop + tail from:

```python
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

to:

```python
    written = 0
    used_concepts = []
    for r in results:
        if r.id in seen:
            continue
        folder = vault_path / profile_name / r.source.replace(":", "-")
        folder.mkdir(parents=True, exist_ok=True)
        fname = f"{(r.date or added)[:10]}-{sanitize_title(r.title) or r.id}.md"
        path = folder / fname
        path.write_text(render_note(r, tags, keywords, added), encoding="utf-8")
        for c in r.extra.get("concepts", []):
            if c not in used_concepts:
                used_concepts.append(c)
        seen[r.id] = str(path.relative_to(vault_path))
        written += 1
    ensure_concept_notes(vault_path, used_concepts)
    _save_seen(vault_path, seen)
    return written
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_obsidian.py -v`
Expected: PASS (new tests + existing tests still green).

- [ ] **Step 5: Commit**

```bash
git add sotawhat/obsidian.py tests/test_obsidian.py
git commit -m "feat: create concept stub notes from write_notes"
```

---

## Task 4: Backfill module

**Files:**
- Create: `sotawhat/backfill.py`
- Test: `tests/test_backfill.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_backfill.py`:

```python
# tests/test_backfill.py
from sotawhat.backfill import backfill_profile, _matches

def _make_note(path, title, abstract, url="http://x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {title}\n---\n\n# {title}\n\n{abstract}\n\n[Source]({url})\n",
        encoding="utf-8")

def test_matches_word_boundary():
    assert _matches("we built an agent system", "agent")
    assert not _matches("we used a reagent here", "agent")

def test_backfill_adds_concepts_line(tmp_path):
    note = tmp_path / "geral" / "arxiv" / "n.md"
    _make_note(note, "An agent paper", "We study reinforcement learning here.")
    scanned, linked, stubs = backfill_profile(
        str(tmp_path), "geral",
        ["large language model", "reinforcement learning", "agent"])
    text = note.read_text(encoding="utf-8")
    assert "**Conceitos:** [[reinforcement learning]] · [[agent]]" in text
    assert text.index("Conceitos") < text.index("[Source]")
    assert scanned == 1
    assert linked == 1
    assert (tmp_path / "concepts" / "agent.md").exists()

def test_backfill_idempotent(tmp_path):
    note = tmp_path / "geral" / "arxiv" / "n.md"
    _make_note(note, "agent", "agent stuff")
    backfill_profile(str(tmp_path), "geral", ["agent"])
    first = note.read_text(encoding="utf-8")
    _, linked2, _ = backfill_profile(str(tmp_path), "geral", ["agent"])
    assert note.read_text(encoding="utf-8") == first
    assert linked2 == 0

def test_backfill_skips_unmatched(tmp_path):
    note = tmp_path / "geral" / "arxiv" / "n.md"
    _make_note(note, "biology", "cells and proteins only")
    _, linked, _ = backfill_profile(str(tmp_path), "geral", ["agent"])
    assert linked == 0
    assert "Conceitos" not in note.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests/test_backfill.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sotawhat.backfill'`.

- [ ] **Step 3: Write minimal implementation**

Create `sotawhat/backfill.py`:

```python
# sotawhat/backfill.py
import re
from pathlib import Path

from sotawhat.obsidian import ensure_concept_notes

_CONCEPT_MARKER = "**Conceitos:**"

def _matches(text, keyword):
    pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
    return re.search(pattern, text.lower()) is not None

def _insert_concepts(content, concepts):
    line = f"{_CONCEPT_MARKER} " + " · ".join(f"[[{c}]]" for c in concepts)
    lines = content.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("[Source]"):
            lines.insert(i, "")
            lines.insert(i + 1, line)
            return "\n".join(lines) + "\n"
    return content.rstrip("\n") + f"\n\n{line}\n"

def backfill_profile(vault, profile_name, keywords):
    vault_path = Path(vault)
    profile_dir = vault_path / profile_name
    scanned = 0
    linked = 0
    all_concepts = []
    if not profile_dir.exists():
        return scanned, linked, 0
    for path in sorted(profile_dir.rglob("*.md")):
        scanned += 1
        content = path.read_text(encoding="utf-8")
        if _CONCEPT_MARKER in content:
            continue
        matched = [k for k in keywords if _matches(content, k)]
        if not matched:
            continue
        path.write_text(_insert_concepts(content, matched), encoding="utf-8")
        for c in matched:
            if c not in all_concepts:
                all_concepts.append(c)
        linked += 1
    stubs = ensure_concept_notes(vault_path, all_concepts)
    return scanned, linked, stubs

def run_backfill(ns):
    from sotawhat.profiles import PROFILES
    if ns.profile == "all":
        profiles = list(PROFILES)
    else:
        if ns.profile not in PROFILES:
            raise SystemExit(f"Unknown profile '{ns.profile}'. "
                             f"Choose from: {', '.join(PROFILES)}, all")
        profiles = [ns.profile]
    total_scanned = total_linked = total_stubs = 0
    for p in profiles:
        s, l, st = backfill_profile(ns.vault, p, PROFILES[p]["keywords"])
        total_scanned += s
        total_linked += l
        total_stubs += st
    print(f"Backfill: {total_scanned} scanned, {total_linked} linked, "
          f"{total_stubs} concept stubs ensured.")
```

Note: `profile_dir.rglob` only walks `<vault>/<profile>/...`; concept stubs live in
`<vault>/concepts/`, so they are never scanned or modified.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_backfill.py -v`
Expected: PASS (all four tests).

- [ ] **Step 5: Commit**

```bash
git add sotawhat/backfill.py tests/test_backfill.py
git commit -m "feat: backfill-links content-scan module"
```

---

## Task 5: Register `backfill-links` CLI subcommand

**Files:**
- Modify: `sotawhat/cli.py:5`, `sotawhat/cli.py` (subparser + dispatch)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
def test_parse_backfill_links():
    ns = parse_args(["backfill-links", "--vault", "V"])
    assert ns.command == "backfill-links"
    assert ns.vault == "V"
    assert ns.profile == "all"

def test_parse_backfill_links_with_profile():
    ns = parse_args(["backfill-links", "--vault", "V", "--profile", "medico"])
    assert ns.profile == "medico"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests/test_cli.py -k backfill -v`
Expected: FAIL — `backfill-links` is treated as a search keyword (argparse error).

- [ ] **Step 3: Write minimal implementation**

In `sotawhat/cli.py`, change line 5:

```python
_SUBCOMMANDS = {"search", "digest"}
```

to:

```python
_SUBCOMMANDS = {"search", "digest", "backfill-links"}
```

After the `p_digest` block in `parse_args`, add:

```python
    p_backfill = sub.add_parser("backfill-links")
    p_backfill.add_argument("--vault", required=True)
    p_backfill.add_argument("--profile", default="all")
```

In `main`, after the `digest` branch, add:

```python
    elif ns.command == "backfill-links":
        from sotawhat.backfill import run_backfill
        run_backfill(ns)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python -m pytest tests/test_cli.py -v`
Expected: PASS (new + existing tests).

- [ ] **Step 5: Commit**

```bash
git add sotawhat/cli.py tests/test_cli.py
git commit -m "feat: add backfill-links CLI subcommand"
```

---

## Task 6: Full suite + README docs

**Files:**
- Modify: `README.md`
- Test: full suite

- [ ] **Step 1: Run the full test suite**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: all tests PASS (27 prior + new ones).

- [ ] **Step 2: Document concept links and backfill in README**

In `README.md`, after the "Digest → Obsidian vault" section, add:

````markdown
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
````

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document concept links and backfill-links"
```

---

## Task 7: End-to-end verification on a temp vault

**Files:** none (manual verification)

- [ ] **Step 1: Run a digest into a throwaway vault and confirm concept line + stubs**

Run:
```bash
.\.venv\Scripts\sotawhat digest --profile geral --vault _tmp_vault --limit 3
```
Expected: notes under `_tmp_vault/geral/<source>/` contain a `**Conceitos:** [[...]]`
line, and `_tmp_vault/concepts/` contains stub files like `agent.md` with
`type: concept` frontmatter.

- [ ] **Step 2: Run backfill twice and confirm idempotency**

Run:
```bash
.\.venv\Scripts\sotawhat backfill-links --vault _tmp_vault
.\.venv\Scripts\sotawhat backfill-links --vault _tmp_vault
```
Expected: first run reports some `linked`; second run reports `0 linked`.
(`_tmp_vault/` is already in `.gitignore`.)

- [ ] **Step 3: Clean up**

```bash
rm -rf _tmp_vault
```

---

## Self-Review Notes

- **Spec coverage:** collect provenance (Task 1), render line (Task 2), stubs (Task 3),
  backfill command (Tasks 4–5), tests across all, docs (Task 6). All spec sections covered.
- **Concept link text vs filename:** wikilink uses the keyword verbatim; stub filename uses
  `sanitize_title(keyword)`. All current profile keywords contain no Windows-invalid
  characters, so basenames match the link targets and resolve in Obsidian.
- **Asymmetry:** forward path = provenance (Task 1); backfill = word-boundary content scan
  (Task 4). Documented in spec and README.
