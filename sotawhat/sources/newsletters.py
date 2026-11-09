# sotawhat/sources/newsletters.py
"""Newsletters read by RSS (Substack, beehiiv, Ghost, WordPress...), listed in config/newsletters.yaml.

Each entry has a `profile` (ia -> perfil geral, "Fronteira de IA"; saude -> perfil médico, "IA ∩ Saúde")
and a `kind`:
- post: every post is one item (essays, analyses, news sites);
- digest: every issue carries several stories (Import AI, Top AI Papers...), so the LLM splits it like a
  Gmail newsletter (task `segment`, ≈ US$ 0,0005 per issue) and each story keeps its source link.
A run reads the entries of the last `max_age_days`, at most `per_feed` per newsletter, and never reads an
entry twice (`data/state/newsletters-<profile>.json`). Health newsletters cover much more than AI, so the
source filters them itself with English and Portuguese AI terms ("IA" only in capitals: "ia" is a verb).
A Substack is added with `sotawhat newsletters add <endereço> --profile saude`."""
import calendar
import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

import feedparser
import httpx
import yaml

from sotawhat.configfiles import ConfigError, read_yaml
from sotawhat.items import normalize_url
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.models import Result
from sotawhat.sources.base import Source
from sotawhat.sources.gmail import html_to_text, resolve_link, stories_from_html
from sotawhat.sources.rss import FeedError, fetch_feed

log = logging.getLogger("sotawhat.newsletters")

PROFILES = ("ia", "saude")
KINDS = ("post", "digest")
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
_AI_PT = re.compile(r"\bIAs?\b|(?i:\b(intelig[eê]ncia artificial|aprendizado de m[aá]quina|aprendizado profundo|"
                    r"redes? neura(l|is)|modelos? de linguagem|vis[aã]o computacional|chatbots?|algoritmos? de ia)\b)")
HEADER = """# config/newsletters.yaml - newsletters lidas pelo RSS no run diário (Substack, beehiiv, sites).
#   profile: ia (seção Fronteira de IA, perfil geral) | saude (seção IA ∩ Saúde, perfil médico)
#   kind:    post (cada post é um item) | digest (cada edição traz várias notícias; o LLM separa uma a uma,
#            ≈ US$ 0,0005 por edição)
#   enabled: false deixa a newsletter listada sem ler
# As de saúde passam por um filtro de termos de IA (inglês e português) antes da triagem.
# Acrescentar um Substack (ou outro feed): sotawhat newsletters add https://exemplo.substack.com --profile saude
"""


def mentions_ai_pt(text) -> bool:
    return bool(_AI_PT.search(text or ""))


def load_newsletters(path) -> list:
    """-> [{"name", "url", "profile", "kind", "enabled", ...}]; a missing file is an empty list."""
    path = Path(path)
    data = read_yaml(path) or {}
    rows = data.get("newsletters") or []
    if not isinstance(rows, list):
        raise ConfigError(f"{path.name}: `newsletters` precisa ser uma lista")
    out, names = [], set()
    for n, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not NAME.match(str(row.get("name", ""))):
            raise ConfigError(f"{path.name}: newsletter {n} sem `name` válido (minúsculas, números e hífen)")
        name = row["name"]
        if name in names:
            raise ConfigError(f"{path.name}: `{name}` aparece duas vezes")
        names.add(name)
        if not str(row.get("url", "")).startswith(("https://", "http://")):
            raise ConfigError(f"{path.name}: {name}: `url` precisa começar com https://")
        if row.get("profile") not in PROFILES:
            raise ConfigError(f"{path.name}: {name}: `profile` deve ser ia ou saude")
        kind = row.get("kind", "post")
        if kind not in KINDS:
            raise ConfigError(f"{path.name}: {name}: `kind` deve ser post ou digest")
        out.append({**row, "kind": kind, "enabled": bool(row.get("enabled", True))})
    return out


def _timestamp(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return calendar.timegm(parsed) if parsed else None


def _body(entry) -> str:
    return (entry.get("content") or [{}])[0].get("value") or entry.get("summary", "") or ""


class NewsletterFeedSource(Source):
    keywordless = True
    ai_specific = True      # the frontier feeds only carry AI; the health ones are filtered here (EN + PT)

    def __init__(self, name, path, profile, state_path, segmenter=None, ai_filter=None, max_age_days=4,
                 per_feed=2, max_items=40, fetch=None, resolve=None, now=None):
        self.name, self.path, self.profile, self.state_path = name, Path(path), profile, Path(state_path)
        self.segmenter, self.ai_filter = segmenter, ai_filter
        self.max_age_days, self.per_feed, self.max_items = max_age_days, per_feed, max_items
        self._fetch, self._resolve, self._now = fetch or fetch_feed, resolve or resolve_link, now
        self.feeds, self.feed_errors, self.stopped = [], {}, None   # feeds: (name, url), for the per-feed health

    def _seen(self) -> list:
        if not self.state_path.exists():
            return []
        return json.loads(self.state_path.read_text(encoding="utf-8")).get("seen", [])

    def fetch(self, limit):
        feeds = [f for f in load_newsletters(self.path) if f["profile"] == self.profile and f["enabled"]]
        self.feeds, self.feed_errors, self.stopped = [(f["name"], f["url"]) for f in feeds], {}, None
        seen = self._seen()
        known, read, results = set(seen), [], []
        oldest = (self._now or time.time()) - self.max_age_days * 86400
        for feed in feeds:
            if len(results) >= limit or self.stopped:
                break
            try:
                entries = feedparser.parse(self._fetch(feed["url"])).entries
            except Exception as exc:  # noqa: BLE001 - one failing newsletter must not stop the others
                self.feed_errors[feed["name"]] = f"{type(exc).__name__}: {exc}"
                continue
            fresh = []
            for entry in entries:
                stamp, key = _timestamp(entry), f"{feed['name']}:{entry.get('id') or entry.get('link') or entry.get('title')}"
                if stamp is not None and stamp >= oldest and key not in known:
                    fresh.append((stamp, key, entry))
            taken = 0
            for stamp, key, entry in sorted(fresh, key=lambda t: -t[0]):
                if taken >= self.per_feed or len(results) >= limit:
                    break
                try:
                    found = self._entry(feed, entry, stamp, key)
                except (BudgetExceeded, InsufficientCredits) as exc:
                    self.stopped = str(exc)
                    break
                except LLMFailure as exc:       # read again next run
                    log.warning("newsletter %s: %s", feed["name"], exc)
                    continue
                read.append(key)
                known.add(key)
                if found:
                    taken += 1
                    results += found
        if read:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps({"seen": (seen + read)[-3000:]}), encoding="utf-8")
        return results[:limit]

    def _entry(self, feed, entry, stamp, key) -> list:
        """The items of one entry; [] when a health post does not mention AI."""
        link = entry.get("link", "") or ""
        title = " ".join((entry.get("title", "") or "").split())
        html = _body(entry)
        day = time.strftime("%Y-%m-%d", time.gmtime(stamp))
        source = f"newsletter:{feed['name']}"
        if feed["kind"] == "digest" and self.segmenter is not None and len(html) > 500:
            out = []
            for position, story, url in stories_from_html(self.segmenter, title, feed["name"], html,
                                                          resolve=self._resolve):
                summary = " ".join(story.summary.split())
                story_title = " ".join(story.title.split())
                if self.ai_filter is not None and not self.ai_filter(f"{story_title} {summary}"):
                    continue
                extra = {"kind": "newsletter_item", "category": story.category}
                if not url:     # the issue page is shared by every story without a link of its own
                    extra["canonical_id"] = f"newsletter:{normalize_url(link) if link else key}#{position}"
                out.append(Result(id=url or f"{link}#{position}", title=story_title, authors=[feed["name"]],
                                  date=day, url=url or link, abstract=summary, source=source, extra=extra))
            return out
        text, _ = html_to_text(html)
        summary = " ".join(text.split())[:1500]
        if self.ai_filter is not None and not self.ai_filter(f"{title} {summary[:600]}"):
            return []
        return [Result(id=normalize_url(link) if link else key, title=title, authors=[feed["name"]], date=day,
                       url=link, abstract=summary, source=source, extra={"kind": "newsletter_item"})]


# ----- sotawhat newsletters add -------------------------------------------------------------------------

_ALTERNATE = re.compile(r"<link[^>]+type=[\"']application/(?:rss|atom)\+xml[\"'][^>]*>", re.I)
_HREF = re.compile(r"href=[\"']([^\"']+)[\"']", re.I)


def _page(url) -> str:
    r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0 (sotawhat/3.0)"}, timeout=20, follow_redirects=True)
    r.raise_for_status()
    return r.text


def home_url(address) -> str:
    """`importai` -> https://importai.substack.com; `site.com/x` -> https://site.com/x."""
    address = address.strip()
    if "://" in address:
        return address
    return "https://" + (f"{address}.substack.com" if re.fullmatch(r"[a-z0-9-]+", address) else address)


def feed_candidates(address) -> list:
    """Where the feed of an address can be: the address itself when it looks like a feed, the page's own feed
    (a WordPress topic: .../topic/ai/feed/), then /feed (Substack, WordPress, Ghost), /rss, /feed.xml and
    /rss.xml of its site."""
    address = home_url(address)
    parts = urlsplit(address)
    origin = f"https://{parts.netloc}"
    if re.search(r"(/feed|/rss|\.xml|\.rss|\.atom)/?$", parts.path):
        out = [address]
    else:
        out = [f"{origin}{parts.path.rstrip('/')}/feed/"] if parts.path.strip("/") else []
    out += [f"{origin}/feed", f"{origin}/rss", f"{origin}/feed.xml", f"{origin}/rss.xml"]
    return list(dict.fromkeys(out))


def discover_feed(address, fetch=None, page=None):
    """-> (feed url, parsed feed) of the first candidate that answers with entries; ValueError when none."""
    fetch, page = fetch or fetch_feed, page or _page
    tried = feed_candidates(address)
    for url in tried:
        try:
            parsed = feedparser.parse(fetch(url))
        except (httpx.HTTPError, FeedError):
            continue
        if parsed.entries:
            return url, parsed
    try:                                            # last resort: the page announces its feed
        html = page(home_url(address))
    except httpx.HTTPError:
        html = ""
    for tag in _ALTERNATE.findall(html):
        href = _HREF.search(tag)
        if not href:
            continue
        url = href.group(1) if "://" in href.group(1) else f"https://{urlsplit(tried[0]).netloc}{href.group(1)}"
        try:
            parsed = feedparser.parse(fetch(url))
        except (httpx.HTTPError, FeedError):
            continue
        if parsed.entries:
            return url, parsed
    raise ValueError(f"nenhum feed RSS encontrado para {address} (tentei {', '.join(tried)})")


def default_name(feed_url) -> str:
    host = urlsplit(feed_url).netloc.lower().removeprefix("www.")
    label = host.split(".")[0] if host.endswith(".substack.com") or host.count(".") <= 1 else host.rsplit(".", 2)[0]
    return re.sub(r"[^a-z0-9-]+", "-", label).strip("-")[:40] or "newsletter"


def add_newsletter(path, address, profile, kind="post", name=None, fetch=None, page=None, today=None) -> dict:
    """Appends one newsletter to the YAML (comments kept). -> the new entry plus "title", "posts", "newest"."""
    if profile not in PROFILES:
        raise ValueError("profile deve ser ia ou saude")
    if kind not in KINDS:
        raise ValueError("kind deve ser post ou digest")
    path = Path(path)
    feeds = load_newsletters(path)
    url, parsed = discover_feed(address, fetch=fetch, page=page)
    name = name or default_name(url)
    if not NAME.match(name):
        raise ValueError(f"nome inválido: {name} (minúsculas, números e hífen)")
    for feed in feeds:
        if feed["name"] == name or normalize_url(feed["url"]) == normalize_url(url):
            raise ValueError(f"já está na lista como {feed['name']} ({feed['url']})")
    title = " ".join((parsed.feed.get("title") or name).split())
    stamps = [s for s in (_timestamp(e) for e in parsed.entries) if s]
    newest = time.strftime("%Y-%m-%d", time.gmtime(max(stamps))) if stamps else "?"
    entry = {"name": name, "url": url, "profile": profile, "kind": kind, "enabled": True,
             "note": f"{title} (adicionada em {today or time.strftime('%Y-%m-%d')})"}
    before = path.read_text(encoding="utf-8") if path.exists() else ""
    text = before if before.strip() else HEADER + "newsletters:\n"
    block = yaml.safe_dump([entry], allow_unicode=True, sort_keys=False, width=120)
    text = text.rstrip("\n") + "\n" + "".join(f"  {line}\n" for line in block.splitlines())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    try:
        load_newsletters(path)
    except ConfigError:
        path.write_text(before, encoding="utf-8")
        raise
    return {**entry, "title": title, "posts": len(parsed.entries), "newest": newest}


def main_newsletters(ns) -> int:
    import sys

    from sotawhat.config import load_settings

    settings = load_settings()
    path = Path(settings.sotawhat_config_dir) / "newsletters.yaml"
    try:
        added = add_newsletter(path, ns.address, ns.profile, kind=ns.kind, name=ns.name)
    except (ValueError, ConfigError, OSError) as exc:
        print(f"[newsletters] {exc}", file=sys.stderr)
        return 1
    print(f"adicionada: {added['name']} · {added['title']} · {added['posts']} posts no feed, o mais novo em "
          f"{added['newest']} · perfil {added['profile']} · tipo {added['kind']}\n[arquivo] {path}")
    return 0
