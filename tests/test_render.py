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
