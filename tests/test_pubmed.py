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
