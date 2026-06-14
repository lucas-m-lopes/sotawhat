# tests/test_obsidian.py
from sotawhat.models import Result
from sotawhat.obsidian import sanitize_title, render_note, write_notes

def test_sanitize_strips_invalid_windows_chars():
    assert sanitize_title('A:Model/With\\Bad?*"<>|chars') == "A-Model-With-Bad-chars"

def test_sanitize_truncates_and_trims():
    assert sanitize_title("  spaced  ") == "spaced"
    assert len(sanitize_title("x" * 200)) <= 100

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
