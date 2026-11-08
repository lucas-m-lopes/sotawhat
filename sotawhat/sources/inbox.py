# sotawhat/sources/inbox.py
"""Manual capture (P5, SDD §7.2 T2 and §7.7): every link you send to the Telegram bot becomes an item.

- Instagram posts and reels are resolved through the Apify scraper (`directUrls` of the posts), also
  for accounts outside the curated list. Private posts cannot be read and become a plain link item.
- Any other link becomes an item with the page title and description (a size and time cap, http or
  https only, and every hop of a redirect must resolve to a public address).
- These items carry source `manual:telegram`: the triage skips the mute filter and the classifier for them
  and never rejects them (the worst outcome is the radar)."""
import ipaddress
import json
import logging
import re
import socket
from html import unescape
from urllib.parse import urljoin, urlsplit

import httpx

from sotawhat.models import Result
from sotawhat.sources.base import Source
from sotawhat.sources.instagram import ACTOR, normalize, post_urls, to_result
from sotawhat.store.db import utcnow

log = logging.getLogger("sotawhat.inbox")
SOURCE = "manual:telegram"
MAX_PAGE_BYTES = 2 * 1024 * 1024
_META = re.compile(r'<meta\s+[^>]*?(?:property|name)=["\'](og:title|og:description|description|twitter:title)["\']'
                   r'[^>]*?content=["\']([^"\']*)["\']', re.I | re.S)
_META_REV = re.compile(r'<meta\s+[^>]*?content=["\']([^"\']*)["\'][^>]*?(?:property|name)=["\']'
                       r'(og:title|og:description|description|twitter:title)["\']', re.I | re.S)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def public_host(url) -> bool:
    """Only http(s) URLs whose host resolves to public addresses (no SSRF into the local network)."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
    except OSError:
        return False
    return all(ipaddress.ip_address(info[4][0]).is_global for info in infos)


def page_summary(html) -> tuple:
    """-> (title, description) from <meta> tags and <title>."""
    found = {}
    for key, value in _META.findall(html):
        found.setdefault(key.lower(), value)
    for value, key in _META_REV.findall(html):
        found.setdefault(key.lower(), value)
    title = found.get("og:title") or found.get("twitter:title")
    if not title:
        match = _TITLE.search(html)
        title = match.group(1) if match else ""
    description = found.get("og:description") or found.get("description") or ""
    return " ".join(unescape(title).split())[:300], " ".join(unescape(description).split())[:1500]


class InboxSource(Source):
    keywordless = True
    ai_specific = True          # you sent it: no keyword filter
    name = "manual-telegram"
    max_items = 50

    def __init__(self, store, apify=None, describer=None, client=None, check_host=public_host):
        self.store, self.apify, self.describer = store, apify, describer
        self._client, self.check_host = client, check_host

    def _pending(self):
        return self.store.conn.execute("SELECT id, payload_json FROM inbox WHERE processed_at IS NULL AND "
                                       "channel = 'telegram' ORDER BY id").fetchall()

    def fetch(self, limit):
        rows = self._pending()
        if not rows:
            return []
        links = []                                   # (inbox id, url, note)
        for row in rows:
            payload = json.loads(row["payload_json"] or "{}")
            note = (payload.get("text") or "").strip()
            for url in dict.fromkeys(payload.get("urls") or []):
                links.append((row["id"], url.rstrip(").,;!?»\"'"), note))
        out, posts = [], {}
        for _, url, note in links:
            for canonical in post_urls(url):
                posts.setdefault(canonical, note)
        if posts and self.apify is not None and self.apify.configured:
            try:
                raw = self.apify.run(ACTOR, {"directUrls": list(posts), "resultsType": "posts", "resultsLimit": 1},
                                     max_usd=0.05, max_items=len(posts))
                for post in (normalize(p) for p in raw):
                    if post is not None:
                        description = self.describer(post) if self.describer else ""
                        out.append(to_result(post, SOURCE, description, manual=True))
            except Exception as exc:  # noqa: BLE001 - the links still become plain items below
                log.warning("inbox: Apify falhou (%s)", exc)
        resolved = {r.extra["canonical_id"][3:] for r in out}
        client = self._client or httpx.Client(follow_redirects=False, timeout=20,
                                              headers={"User-Agent": "Mozilla/5.0 (sotawhat/3.0)"})
        try:
            for _, url, note in links:
                codes = [u.rstrip("/").rsplit("/", 1)[-1] for u in post_urls(url)]
                if codes and all(code in resolved for code in codes):
                    continue
                out.append(self._link(client, url, note))
        finally:
            if self._client is None:
                client.close()
        ids = [row["id"] for row in rows]
        self.store.conn.execute(f"UPDATE inbox SET processed_at = ? WHERE id IN ({','.join('?' * len(ids))})",
                                [utcnow()] + ids)
        self.store.conn.commit()
        return out[:limit]

    def _page(self, client, url, hops=3) -> str:
        """The HTML of `url`, following up to `hops` redirects and checking the host of every hop."""
        for _ in range(hops + 1):
            if not self.check_host(url):
                return ""
            with client.stream("GET", url) as r:
                if r.is_redirect and r.headers.get("location"):
                    url = urljoin(url, r.headers["location"])
                    continue
                if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
                    return ""
                body, size = [], 0
                for chunk in r.iter_bytes():
                    size += len(chunk)
                    body.append(chunk)
                    if size > MAX_PAGE_BYTES:
                        break
                return b"".join(body).decode(r.encoding or "utf-8", "replace")
        return ""

    def _link(self, client, url, note) -> Result:
        title, description = "", ""
        try:
            html = self._page(client, url)
            if html:
                title, description = page_summary(html)
        except httpx.HTTPError as exc:
            log.warning("inbox: %s (%s)", url, exc)
        host = urlsplit(url).hostname or url
        text = "\n\n".join(p for p in (description, f"Mensagem enviada: {note}" if note and note != url else "") if p)
        return Result(id=url, title=title or f"Link enviado: {host}", authors=[], date="", url=url, abstract=text,
                      source=SOURCE, extra={"kind": "article", "manual": True})
