# sotawhat/sources/rss.py
import feedparser
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_UA = {"User-Agent": "Mozilla/5.0 (sotawhat/2.0)"}


class FeedError(Exception):
    """The URL answered, but not with a feed (e.g. an anti-bot HTML challenge page)."""


def _looks_like_html(content_type, body):
    head = body[:512].lstrip().lower()
    return "text/html" in (content_type or "").lower() or head.startswith((b"<!doctype html", b"<html"))


def fetch_feed(url):
    r = httpx.get(url, headers=_UA, timeout=30, follow_redirects=True)
    r.raise_for_status()
    if _looks_like_html(r.headers.get("content-type"), r.content):
        raise FeedError(f"HTML instead of a feed (anti-bot page?) from {url}")
    return r.content


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
        self.feed_errors = {}   # label -> error message (last search)
        self._cache = {}        # url -> content or exception; one fetch per feed per run

    @staticmethod
    def _filter(results, keyword, limit):
        kw = keyword.lower()
        hits = [r for r in results if kw in (r.title + " " + r.abstract).lower()]
        return hits[:limit]

    def _fetch_once(self, url):
        if url not in self._cache:
            try:
                self._cache[url] = fetch_feed(url)
            except Exception as exc:  # noqa: BLE001 - cached so a failing feed is hit once per run
                self._cache[url] = exc
        cached = self._cache[url]
        if isinstance(cached, Exception):
            raise cached
        return cached

    def search(self, keyword, limit):
        collected = []
        self.feed_errors = {}
        for label, url in self.feeds:
            try:
                content = self._fetch_once(url)
            except Exception as exc:  # noqa: BLE001 - a failing feed must not abort the others
                self.feed_errors[label] = f"{type(exc).__name__}: {exc}"
                continue
            collected.extend(parse_feed(content, source=f"rss:{label}"))
        return self._filter(collected, keyword, limit)
