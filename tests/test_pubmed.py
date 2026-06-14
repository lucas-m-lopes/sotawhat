# tests/test_pubmed.py
from sotawhat.sources.pubmed import parse_efetch, PubMedSource

def test_parse_efetch():
    xml = open("tests/fixtures/pubmed_efetch.xml", encoding="utf-8").read()
    results = parse_efetch(xml)
    assert len(results) >= 1
    r = results[0]
    assert r.source == "pubmed"
    assert r.title
    assert r.url.startswith("https://pubmed.ncbi.nlm.nih.gov/")
    assert r.id  # PMID

def test_term_plain_without_clause():
    src = PubMedSource()
    assert src._term("radiology") == "radiology"

def test_term_with_and_clause():
    src = PubMedSource(and_clause='"Artificial Intelligence"[Mesh]')
    assert src._term("radiology") == '(radiology) AND ("Artificial Intelligence"[Mesh])'
