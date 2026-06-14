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
