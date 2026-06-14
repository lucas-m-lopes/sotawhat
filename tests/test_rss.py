# tests/test_rss.py
from sotawhat.sources.rss import parse_feed, RSSSource

def test_parse_feed_maps_and_filters():
    results = parse_feed("tests/fixtures/sample_feed.xml", source="rss:lab")
    assert len(results) == 2
    filtered = RSSSource._filter(results, "transformer", 10)
    assert len(filtered) == 1
    assert filtered[0].url == "https://lab.example/post1"
    assert filtered[0].source == "rss:lab"
