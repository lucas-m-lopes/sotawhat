# sotawhat/sources/crossref.py
"""Recent works of a journal by ISSN via the Crossref REST API.

Replaces the Nature/npj RSS feeds, which serve an anti-bot HTML page to non-browser clients (SDD §5.1).
"""
import re
from datetime import date, timedelta

import httpx

from sotawhat.models import Result
from sotawhat.sources.base import Source

_API = "https://api.crossref.org/journals/{issn}/works"
_SELECT = "DOI,title,abstract,author,published,URL,type,container-title"
_TAG = re.compile(r"<[^>]+>")


def strip_jats(text):
    plain = " ".join(_TAG.sub(" ", text or "").split())
    return plain[9:] if plain.lower().startswith("abstract ") else plain


def _published(item):
    parts = ((item.get("published") or {}).get("date-parts") or [[]])[0]
    if not parts or parts[0] is None:
        return ""
    return "-".join([str(parts[0])] + [f"{p:02d}" for p in parts[1:3]])


def parse_works(payload, source):
    results = []
    for it in (payload.get("message") or {}).get("items", []):
        doi = (it.get("DOI") or "").lower()
        title = " ".join(it.get("title") or []).strip()
        if not doi or not title:
            continue
        authors = [" ".join(p for p in (a.get("given"), a.get("family")) if p) for a in it.get("author", [])]
        results.append(Result(
            id=f"doi:{doi}", title=" ".join(title.split()), authors=[a for a in authors if a],
            date=_published(it), url=it.get("URL") or f"https://doi.org/{doi}",
            abstract=strip_jats(it.get("abstract", "")), source=source,
            extra={"doi": doi, "journal": (it.get("container-title") or [""])[0]}))
    return results


class CrossrefJournalSource(Source):
    """Since P2 a channel: every journal here is AI or AI-heavy (the medico AI-term filter still applies),
    so a run takes the recent works of each journal, up to `max_items` per journal, instead of keyword hits."""
    name = "crossref"
    keywordless = True
    max_items = 10

    def __init__(self, journals, days=7, rows=50, mailto=""):
        # journals: list of (label, ISSN) — same shape as RSSSource.feeds
        self.feeds = journals
        self.days = days
        self.rows = rows
        self.mailto = mailto
        self.feed_errors = {}
        self._cache = {}

    def _params(self):
        since = (date.today() - timedelta(days=self.days)).isoformat()
        params = {"filter": f"from-pub-date:{since}", "sort": "published", "order": "desc",
                  "rows": self.rows, "select": _SELECT}
        if self.mailto:
            params["mailto"] = self.mailto
        return params

    def _fetch_once(self, issn):
        if issn not in self._cache:
            ua = f"sotawhat/3.0 (mailto:{self.mailto})" if self.mailto else "sotawhat/3.0"
            r = httpx.get(_API.format(issn=issn), params=self._params(), timeout=30,
                          follow_redirects=True, headers={"User-Agent": ua})
            r.raise_for_status()
            self._cache[issn] = r.json()
        return self._cache[issn]

    def search(self, keyword, limit):
        collected = []
        self.feed_errors = {}
        for label, issn in self.feeds:
            try:
                payload = self._fetch_once(issn)
            except Exception as exc:  # noqa: BLE001 - one journal failing must not abort the others
                self.feed_errors[label] = f"{type(exc).__name__}: {exc}"
                continue
            collected.extend(parse_works(payload, source=f"crossref:{label}"))
        kw = keyword.lower()
        return [r for r in collected if kw in (r.title + " " + r.abstract).lower()][:limit]

    def fetch(self, limit):
        collected = []
        self.feed_errors = {}
        for label, issn in self.feeds:
            try:
                payload = self._fetch_once(issn)
            except Exception as exc:  # noqa: BLE001 - one journal failing must not abort the others
                self.feed_errors[label] = f"{type(exc).__name__}: {exc}"
                continue
            collected.extend(parse_works(payload, source=f"crossref:{label}")[:limit])
        return collected
