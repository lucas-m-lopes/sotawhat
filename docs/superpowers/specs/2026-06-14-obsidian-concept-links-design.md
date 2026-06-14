# Design — Obsidian concept links (graph edges)

Date: 2026-06-14
Status: approved (pending spec review)

## Problem

The digest writes one Markdown note per item into the Obsidian vault. Each note
has YAML frontmatter with `tags`, but **no `[[wikilinks]]` between notes**. The
Obsidian graph only draws edges from wikilinks (or from tags, if the user enables
tag nodes), so every note floats unconnected.

## Goal

Connect notes into thematic clusters by linking each paper to **concept notes**,
one per profile keyword (e.g. `large language model`, `agent`, `radiology`). This
turns the vault into a knowledge graph: ~9 concept nodes (4 from `geral`, 5 from
`medico`) with papers drawing edges to the concept(s) that surfaced them.

Decisions taken during brainstorming:
- Edge type: **concept notes only** (no author/source/date hubs).
- Concept notes are **stubs** (rely on Obsidian's Backlinks panel; not
  auto-populated indexes).
- Forward path links by **provenance** — the search keyword(s) that returned the
  paper, accumulated across keywords.
- Existing notes are connected via a one-time **backfill command**.

## Architecture

### 1. Data flow — `collect()` in `digest.py`

Today `collect` dedups results by `id` and discards which keyword found each one.
Change it to record provenance:

- Maintain `by_id: dict[str, Result]`.
- For each `(source, keyword, result)`: if the id is new, set
  `result.extra["concepts"] = [keyword]` and append to output; if the id was seen,
  append `keyword` to the existing result's `extra["concepts"]` (dedup, preserve
  first-seen order).
- Return type is unchanged (`list[Result]`); concepts ride along in `extra`.

`Result.extra` already exists (`dataclass` field), so no model change.

### 2. Rendering — `render_note()` in `obsidian.py`

After the abstract body, emit one line when concepts are present:

```
**Conceitos:** [[large language model]] · [[agent]]
```

- Source of concepts: `result.extra.get("concepts", [])`.
- Omit the line entirely when the list is empty.
- Existing frontmatter, tags, title, body, and `[Source]` link are unchanged.
- The wikilink target is the keyword verbatim (keywords contain no
  Windows-invalid characters, so no sanitization is needed for the link text).

### 3. Concept stub notes — `ensure_concept_notes()` in `obsidian.py`

New helper: for each concept, create `<vault>/concepts/<keyword>.md` if it does
not already exist. Stub content:

```
---
type: concept
tags: [concept]
---
# large language model
```

- Called from `write_notes` for the union of concepts across the notes written in
  that run.
- Never overwrites an existing concept note (idempotent).
- Obsidian resolves `[[large language model]]` to the basename
  `large language model.md` regardless of folder, so the `concepts/` location does
  not affect linking.

### 4. Backfill command — new `sotawhat/backfill.py` + CLI subcommand

`sotawhat backfill-links --vault <path> [--profile geral|medico|all]`
(default profile: `all`).

For each selected profile:
- Walk `<vault>/<profile>/**/*.md`, skipping the `concepts/` directory.
- For each note:
  - If it already contains a `**Conceitos:**` line → skip (idempotent).
  - **Content-scan** the profile's keywords against the note's title + body using
    **word-boundary, case-insensitive** matching (so `agent` does not match
    `reagent`). Collect matches in profile-keyword order.
  - If ≥1 match: insert the `**Conceitos:** [[...]]` line immediately before the
    trailing `[Source](...)` line (or at end of body if absent), and ensure the
    concept stubs exist.
  - If 0 matches: leave the note unchanged (stays orphan).
- Print a summary: `Backfill: N scanned, M linked, K concept stubs ensured.`

**Asymmetry (documented):** the forward path links by provenance (the actual
search keyword); backfill links by content-scan, because old notes do not record
which keyword surfaced them. Content-scan is the only signal available
retroactively.

## Testing (TDD)

- `collect`: a single id surfaced by two keywords ends with both in
  `extra["concepts"]`, deduped and order-preserved.
- `render_note`: includes the `**Conceitos:**` line with wikilinks when concepts
  are present; omits it entirely when empty.
- `ensure_concept_notes`: creates `concepts/<kw>.md` stubs; does not overwrite an
  existing stub (idempotent).
- `write_notes`: notes written in a run produce the corresponding concept stubs.
- `backfill`: adds a `**Conceitos:**` line based on word-boundary content scan;
  creates stubs; a second run makes no changes (idempotent); respects the
  profile's keyword set; `agent` does not match `reagent`.

## Out of scope (YAGNI)

- Author, source, or date hub/MOC notes.
- Auto-generated concept indexes (listing papers in the concept body).
- Dataview queries or any plugin dependency.

## Files touched

- `sotawhat/digest.py` — `collect` records provenance.
- `sotawhat/obsidian.py` — `render_note` concept line; `ensure_concept_notes`;
  `write_notes` calls it.
- `sotawhat/backfill.py` — new module with the backfill logic.
- `sotawhat/cli.py` — `backfill-links` subcommand.
- `tests/` — new/updated tests per the TDD list above.
