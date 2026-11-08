# sotawhat/sources/gmail.py
"""Newsletters from Gmail over IMAP with an app password (SDD §7.1).

- Read only: the `\\All` mailbox is selected with `readonly=True`, and bodies are fetched with
  `BODY.PEEK[]`, so nothing is marked as read or moved.
- Gmail search syntax through X-GM-RAW (`GMAIL_QUERY`, e.g. `label:newsletters-ai newer_than:2d`).
- Each message is read once: its X-GM-MSGID goes to `data/state/`.
- The HTML becomes text with numbered links. The LLM (task `segment`) splits it into stories and answers
  with a link number, never a copied URL.
- Each chosen link is resolved past tracking redirects and stripped of tracking parameters.
  Unsubscribe, preferences and mailto links are never followed."""
import email
import imaplib
import json
import re
import ssl
from email import policy
from email.utils import parsedate_to_datetime, parseaddr
from html.parser import HTMLParser
from pathlib import Path

import httpx

from sotawhat.items import normalize_url
from sotawhat.models import Result
from sotawhat.sources.base import Source

DROP = {"sponsor", "job", "event"}
_SKIP = re.compile(r"unsubscribe|preferences|manage[ -]?(your)?[ -]?subscription|opt[ -]?out|view (it )?in (your )?browser|"
                   r"forward to a friend|refer(ral)?\b", re.I)
_MSGID = re.compile(rb"X-GM-MSGID (\d+)")
_BLOCKS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "section"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.labels = [], {}, {}
        self._skip, self._href, self._anchor = 0, None, []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "title"):
            self._skip += 1
        elif tag in _BLOCKS:
            self.parts.append("\n")
        elif tag == "a":
            self._href, self._anchor = dict(attrs).get("href"), []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "title"):
            self._skip = max(0, self._skip - 1)
        elif tag == "a" and self._href:
            number = len(self.links) + 1
            self.links[number] = self._href
            self.labels[number] = " ".join("".join(self._anchor).split())
            self.parts.append(f" [{number}]")
            self._href = None
        elif tag in _BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        self.parts.append(data)
        if self._href:
            self._anchor.append(data)


def _parse(html):
    parser = _Text()
    parser.feed(html or "")
    lines = (" ".join(line.split()) for line in "".join(parser.parts).split("\n"))
    return "\n".join(line for line in lines if line), parser.links, parser.labels


def html_to_text(html):
    """-> (text with "anchor [n]" markers, {n: url})."""
    text, links, _ = _parse(html)
    return text, links


def skip_link(url, label="") -> bool:
    return not (url or "").lower().startswith(("http://", "https://")) or bool(_SKIP.search(url) or _SKIP.search(label or ""))


def resolve_link(url, timeout=10) -> str:
    """Follow tracking redirects; on any failure keep the URL as it was."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (sotawhat/3.0)"}) as c:
            r = c.head(url)
            if r.status_code in (403, 405) or r.status_code >= 500:
                with c.stream("GET", url) as streamed:
                    return str(streamed.url)
            return str(r.url)
    except httpx.HTTPError:
        return url


def make_segmenter(gateway, max_chars=24000):
    from sotawhat.llm.prompts import load as load_prompt
    from sotawhat.llm.schemas import NewsletterStories

    system = load_prompt("segment_v1")

    def segment(subject, sender, text):
        message = f"Newsletter from {sender}\nsubject: {subject}\n\n{text[:max_chars]}"
        return gateway.structured("segment", [{"role": "system", "content": system},
                                              {"role": "user", "content": message}], NewsletterStories).stories

    return segment


def _gmail_imap():
    return imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=ssl.create_default_context())


class GmailNewsletterSource(Source):
    keywordless = True
    ai_specific = True

    def __init__(self, address, app_password, query, segmenter, state_path, name="gmail", max_messages=10,
                 max_items=40, imap_factory=None, resolve=None):
        self.name, self.address, self.password, self.query = name, address, app_password, query
        self.segmenter, self.state_path = segmenter, Path(state_path)
        self.max_messages, self.max_items = max_messages, max_items
        self._imap_factory, self._resolve = imap_factory or _gmail_imap, resolve or resolve_link

    def _seen(self) -> list:
        if not self.state_path.exists():
            return []
        return json.loads(self.state_path.read_text(encoding="utf-8")).get("seen", [])

    def fetch(self, limit):
        if not (self.address and self.password and self.query and self.segmenter):
            return []
        seen = self._seen()
        imap = self._imap_factory()
        results, read = [], []
        try:
            imap.login(self.address, "".join(self.password.split()))
            _, boxes = imap.list()
            box = next((b.decode("utf-8", "replace").split(' "/" ')[-1] for b in boxes if b"\\All" in b), "INBOX")
            imap.select(box, readonly=True)
            _, data = imap.uid("SEARCH", "X-GM-RAW", f'"{self.query}"')
            uids = (data[0] or b"").split()[-self.max_messages:] if data else []
            for uid in reversed(uids):                                   # newest first
                _, parts = imap.uid("FETCH", uid, "(X-GM-MSGID BODY.PEEK[])")
                header, raw = next((p for p in parts if isinstance(p, tuple)), (b"", b""))
                match = _MSGID.search(header)
                msgid = match.group(1).decode() if match else uid.decode()
                if msgid in seen or not raw:
                    continue
                results += self._stories(msgid, email.message_from_bytes(raw, policy=policy.default))
                read.append(msgid)
                if len(results) >= limit:
                    break
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001 - the connection is going away anyway
                pass
        if read:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps({"seen": (seen + read)[-1000:]}), encoding="utf-8")
        return results[:limit]

    def _stories(self, msgid, message) -> list:
        subject, sender = str(message.get("Subject", "")), str(message.get("From", ""))
        domain = parseaddr(sender)[1].rsplit("@", 1)[-1].lower() or "desconhecido"
        try:
            day = parsedate_to_datetime(message.get("Date")).date().isoformat()
        except (TypeError, ValueError):
            day = ""
        body = message.get_body(preferencelist=("html", "plain"))
        content = body.get_content() if body is not None else ""
        text, links, labels = _parse(content) if body is not None and body.get_content_subtype() == "html" \
            else (content, {}, {})
        usable = {n: url for n, url in links.items() if not skip_link(url, labels.get(n, ""))}
        listing = "\n".join(f"[{n}] {url}" for n, url in usable.items())
        stories = self.segmenter(subject, sender, f"{text}\n\nLinks:\n{listing}" if listing else text)
        out = []
        for position, story in enumerate(stories, 1):
            if story.category in DROP:
                continue
            url = usable.get(story.link, "")
            url = normalize_url(self._resolve(url)) if url else ""
            out.append(Result(id=url or f"gmail:{msgid}#{position}", title=" ".join(story.title.split()),
                              authors=[domain], date=day, url=url, abstract=" ".join(story.summary.split()),
                              source=f"gmail:{domain}", extra={"kind": "newsletter_item", "category": story.category}))
        return out
