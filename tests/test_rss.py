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

def _response(content, content_type):
    import httpx
    return httpx.Response(200, headers={"content-type": content_type}, content=content,
                          request=httpx.Request("GET", "https://www.nature.com/npjdigitalmed.rss"))

def test_fetch_feed_rejects_html_challenge(monkeypatch):
    import pytest
    html = open("tests/fixtures/nature_challenge.html", "rb").read()
    monkeypatch.setattr(rssmod.httpx, "get", lambda *a, **k: _response(html, "text/html; charset=utf-8"))
    with pytest.raises(rssmod.FeedError):
        rssmod.fetch_feed("https://www.nature.com/npjdigitalmed.rss")

def test_fetch_feed_rejects_html_even_with_xml_content_type(monkeypatch):
    import pytest
    monkeypatch.setattr(rssmod.httpx, "get", lambda *a, **k: _response(b"  <html><body>x</body></html>", "application/rss+xml"))
    with pytest.raises(rssmod.FeedError):
        rssmod.fetch_feed("https://x/feed")

def test_search_records_feed_errors_and_fetches_each_feed_once(monkeypatch):
    fixture = open("tests/fixtures/sample_feed.xml", "rb").read()
    calls = []
    def fake_fetch(url):
        calls.append(url)
        if "bad" in url:
            raise rssmod.FeedError("HTML instead of a feed")
        return fixture
    monkeypatch.setattr(rssmod, "fetch_feed", fake_fetch)
    src = RSSSource("medical", [("bad", "http://bad/feed"), ("good", "http://good/feed")])
    src.search("transformer", 10)
    src.search("attention", 10)
    assert calls == ["http://bad/feed", "http://good/feed"]
    assert list(src.feed_errors) == ["bad"]
    assert "FeedError" in src.feed_errors["bad"]
