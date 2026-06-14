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
