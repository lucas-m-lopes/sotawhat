# tests/test_crossref.py
import json

import httpx

import sotawhat.sources.crossref as crmod
from sotawhat.sources.crossref import CrossrefJournalSource, parse_works, strip_jats

PAYLOAD = json.load(open("tests/fixtures/crossref_works.json", encoding="utf-8"))


def test_parse_works_maps_fields_and_skips_items_without_doi():
    out = parse_works(PAYLOAD, source="crossref:npj-digital-medicine")
    assert [r.id for r in out] == ["doi:10.1000/example.sepsis.1", "doi:10.1000/example.ppg.2"]
    first = out[0]
    assert first.title == "Deep learning for early sepsis prediction in the ICU"
    assert first.authors == ["Ana Souza", "Lima"]
    assert first.date == "2026-11-07"
    assert first.abstract.startswith("We trained a transformer")
    assert first.extra == {"doi": "10.1000/example.sepsis.1", "journal": "npj Digital Medicine"}
    assert out[1].date == "2026-11"


def test_strip_jats():
    assert strip_jats("<jats:title>Abstract</jats:title><jats:p>A  b</jats:p>") == "A b"


def test_search_filters_by_keyword_fetches_once_and_sends_polite_params(monkeypatch):
    calls = []

    def fake_get(url, params=None, **kwargs):
        calls.append((url, params, kwargs["headers"]["User-Agent"]))
        return httpx.Response(200, json=PAYLOAD, request=httpx.Request("GET", url))

    monkeypatch.setattr(crmod.httpx, "get", fake_get)
    src = CrossrefJournalSource([("npj-digital-medicine", "2398-6352")], mailto="me@example.org")
    assert [r.id for r in src.search("sepsis", 10)] == ["doi:10.1000/example.sepsis.1"]
    assert src.search("photoplethysmography", 10)[0].source == "crossref:npj-digital-medicine"
    assert len(calls) == 1
    url, params, ua = calls[0]
    assert url == "https://api.crossref.org/journals/2398-6352/works"
    assert params["filter"].startswith("from-pub-date:")
    assert params["mailto"] == "me@example.org" and "mailto:me@example.org" in ua


def test_search_records_errors_per_journal(monkeypatch):
    def fake_get(url, params=None, **kwargs):
        if "0000-0000" in url:
            return httpx.Response(503, request=httpx.Request("GET", url))
        return httpx.Response(200, json=PAYLOAD, request=httpx.Request("GET", url))

    monkeypatch.setattr(crmod.httpx, "get", fake_get)
    src = CrossrefJournalSource([("down", "0000-0000"), ("npj", "2398-6352")])
    assert len(src.search("sepsis", 10)) == 1
    assert list(src.feed_errors) == ["down"]


def test_crossref_channel_mode_takes_recent_works_of_every_journal(monkeypatch):
    import json as _json

    from sotawhat.sources.crossref import CrossrefJournalSource

    payload = _json.loads(open("tests/fixtures/crossref_works.json", encoding="utf-8").read())
    src = CrossrefJournalSource([("nejm-ai", "2836-9386"), ("jamia", "1527-974X")])
    monkeypatch.setattr(src, "_fetch_once", lambda issn: payload)
    assert src.keywordless and src.max_items >= 10
    results = src.fetch(1)
    assert [r.source for r in results] == ["crossref:nejm-ai", "crossref:jamia"]       # capped per journal
