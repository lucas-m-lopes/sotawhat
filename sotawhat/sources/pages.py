# sotawhat/sources/pages.py
"""Web pages read by the sources: links sent to the bot (P5) and the articles of newsletters whose feed only
carries an excerpt.

- Only http(s) URLs whose host resolves to public addresses are read, and every redirect hop is checked again
  (no SSRF into the local network: the web UI listens on 127.0.0.1).
- Only `200 text/html` answers, at most 2 MB, 20 s.
- The article's main content comes from trafilatura: menus, footers and comments are dropped, links are kept.
- `read_article` never raises: on any failure it answers "" and the caller keeps what it had."""
import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlsplit

import httpx

log = logging.getLogger("sotawhat.pages")
MAX_PAGE_BYTES = 2 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (sotawhat/3.0)"


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


def new_client(timeout=20) -> httpx.Client:
    """Redirects are followed by `get_html`, one checked hop at a time."""
    return httpx.Client(follow_redirects=False, timeout=timeout, headers={"User-Agent": USER_AGENT})


def get_html(client, url, check_host=public_host, hops=3) -> str:
    """The HTML of `url`, following up to `hops` redirects and checking the host of every hop; "" when a host is
    not public or the answer is not `200 text/html`."""
    for _ in range(hops + 1):
        if not check_host(url):
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


def main_content(html, url=None) -> str:
    """The article of a page as simple HTML (headings, paragraphs, lists, tables and links), without menus,
    footers and comments; "" when no article is found."""
    if not html:
        return ""
    import trafilatura          # lxml and friends load only when a page is actually read

    return trafilatura.extract(html, url=url, output_format="html", include_links=True, include_comments=False,
                               include_tables=True, favor_precision=True) or ""


def read_article(url, client=None, check_host=public_host) -> str:
    """The main content of the article at `url` as HTML; "" on any failure (blocked, not HTML, private host...)."""
    own = client is None
    client = client or new_client()
    try:
        return main_content(get_html(client, url, check_host), url)
    except Exception as exc:  # noqa: BLE001 - a page that cannot be read leaves the feed's excerpt in place
        log.info("página não lida (%s): %s: %s", url, type(exc).__name__, exc)
        return ""
    finally:
        if own:
            client.close()
