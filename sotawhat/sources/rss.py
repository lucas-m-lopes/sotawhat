# sotawhat/sources/rss.py
import feedparser
from sotawhat.models import Result
from sotawhat.sources.base import Source

def parse_feed(url_or_path, source):
    feed = feedparser.parse(url_or_path)
    results = []
    for e in feed.entries:
        summary = getattr(e, "summary", "") or ""
        authors = []
        if getattr(e, "author", ""):
            authors = [e.author]
        link = getattr(e, "link", "")
        results.append(Result(
            id=link or getattr(e, "id", "") or getattr(e, "title", ""),
            title=getattr(e, "title", ""), authors=authors,
            date=getattr(e, "published", "")[:16], url=link,
            abstract=summary, source=source))
    return results

class RSSSource(Source):
    def __init__(self, name, feeds):
        # feeds: list of (label, url)
        self.name = name
        self.feeds = feeds

    @staticmethod
    def _filter(results, keyword, limit):
        kw = keyword.lower()
        hits = [r for r in results if kw in (r.title + " " + r.abstract).lower()]
        return hits[:limit]

    def search(self, keyword, limit):
        collected = []
        for label, url in self.feeds:
            collected.extend(parse_feed(url, source=f"rss:{label}"))
        return self._filter(collected, keyword, limit)
