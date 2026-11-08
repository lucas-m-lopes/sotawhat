# tests/test_channel_sources.py
"""Channel sources (P2): fetched once per run without profile keywords, capped, typed, recency-filtered."""
import time

import sotawhat.sources.rss as rssmod
from sotawhat.items import to_item
from sotawhat.models import Result
from sotawhat.pipeline.collect import collect, filter_relevant
from sotawhat.sources.base import Source
from sotawhat.sources.rss import RSSSource

FEED = """<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>
<item><title>Old story</title><link>https://n.example/old</link><pubDate>{old}</pubDate><description>old</description></item>
<item><title>Fresh story A</title><link>https://n.example/a</link><pubDate>{a}</pubDate><description>about AI</description></item>
<item><title>Fresh story B</title><link>https://n.example/b</link><pubDate>{b}</pubDate><description>clinic</description></item>
<item><title>Undated story</title><link>https://n.example/u</link><description>no date</description></item>
</channel></rss>"""


def _rfc822(hours_ago):
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() - hours_ago * 3600))


class Channel(Source):
    name = "chan"
    keywordless = True
    max_items = 2

    def __init__(self):
        self.calls = []

    def fetch(self, limit):
        self.calls.append(limit)
        return [Result(id=f"c{n}", title=f"Repo {n}", authors=[], date="", url=f"https://github.com/o/r{n}",
                       abstract="repo", source="github", extra={"kind": "repo"}) for n in range(limit)]


class Broken(Channel):
    name = "broken"

    def fetch(self, limit):
        raise RuntimeError("HTTP 503")


def test_collect_fetches_channel_sources_once_with_their_cap():
    chan, failures = Channel(), []
    out = collect([chan, Broken()], keywords=["k1", "k2", "k3"], limit=10,
                  on_source_error=lambda src, msg: failures.append(src.name))
    assert chan.calls == [2] and [r.id for r in out] == ["c0", "c1"]
    assert out[0].extra["concepts"] == ["chan"] and failures == ["broken"]


def test_kind_comes_from_the_source_and_ai_channels_skip_the_term_filter():
    repo = Result(id="x", title="DICOM viewer", authors=[], date="", url="https://github.com/o/viewer", abstract="",
                  source="github", extra={"kind": "repo", "ai_source": True})
    paper = Result(id="y", title="Aspirin trial", authors=[], date="", url="https://example.org/y", abstract="",
                   source="pubmed")
    assert to_item(repo).kind == "repo" and to_item(paper).kind == "paper"
    assert filter_relevant([repo, paper], ["machine learning"]) == [repo]


def test_rss_channel_mode_keeps_recent_entries_newest_first(monkeypatch):
    body = FEED.format(old=_rfc822(24 * 10), a=_rfc822(5), b=_rfc822(30)).encode()
    monkeypatch.setattr(rssmod, "fetch_feed", lambda url: body)
    src = RSSSource("news", [("stat", "https://s.example/feed")], keywordless=True, max_items=5, max_age_days=3,
                    ai_specific=True)
    results = src.fetch(src.max_items)
    assert [r.title for r in results] == ["Fresh story A", "Fresh story B"]        # old and undated left out
    assert results[0].source == "rss:stat" and results[0].extra["ai_source"] is True
    assert [r.title for r in src.fetch(1)] == ["Fresh story A"]
    assert RSSSource("labs", [("l", "u")]).keywordless is False                    # lab feeds keep keywords
