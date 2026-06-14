# tests/test_rss.py
from sotawhat.sources.rss import parse_feed, RSSSource
import sotawhat.sources.rss as rssmod

def test_search_skips_failing_feed(monkeypatch):
    fixture = open("tests/fixtures/sample_feed.xml", "rb").read()
    def fake_fetch(url):
        if "bad" in url:
            raise RuntimeError("403 Forbidden")
        return fixture
    monkeypatch.setattr(rssmod, "fetch_feed", fake_fetch)
    src = RSSSource("labs", [("bad", "http://bad/feed"), ("good", "http://good/feed")])
    results = src.search("transformer", 10)
    assert len(results) == 1
    assert results[0].source == "rss:good"

def test_parse_feed_maps_and_filters():
    results = parse_feed("tests/fixtures/sample_feed.xml", source="rss:lab")
    assert len(results) == 2
    filtered = RSSSource._filter(results, "transformer", 10)
    assert len(filtered) == 1
    assert filtered[0].url == "https://lab.example/post1"
    assert filtered[0].source == "rss:lab"
