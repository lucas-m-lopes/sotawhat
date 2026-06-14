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
