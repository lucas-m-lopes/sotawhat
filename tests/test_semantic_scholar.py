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
