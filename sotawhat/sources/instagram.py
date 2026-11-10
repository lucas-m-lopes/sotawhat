# sotawhat/sources/instagram.py
"""Instagram (P5, SDD §7.2): public posts of the curated accounts, through the Apify scraper (T3).

- The accounts come from config/instagram_accounts.yaml (`sotawhat instagram import` writes it from the
  Accounts Center export; you review it). One source per category: "ia" in the general profile, "saude"
  in the medical one.
- The window starts at a watermark (the last successful scan, at most `max_days` back), so a failed day
  loses nothing and no post is paid twice. Pinned posts that come back are dropped by their shortcode.
- INSTAGRAM_MAX_USD_RUN is the cap of the daily run, shared by the two categories (`daily_shares`). The account
  order turns every day, so when the cap cuts a scan it is not always the same accounts that are left out.
- Every post goes through `describer` (images and, if installed, the reel transcript) in the same run,
  because the CDN URLs expire. No Meta app and no Instagram login are ever used (T4 stays off)."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sotawhat.configfiles import ConfigError, read_yaml
from sotawhat.models import Result
from sotawhat.sources.base import Source

ACTOR = "apify~instagram-scraper"
CATEGORIES = ("ia", "saude")
POST_URL = re.compile(r"https?://(?:www\.)?instagram\.com/(?:[A-Za-z0-9_.]+/)?(p|reel|reels|tv)/([A-Za-z0-9_-]{5,})")
USERNAME = re.compile(r"^[A-Za-z0-9_.]{1,30}$")
FLOOR_USD = 0.02            # the least share of the daily cap a category with accounts gets (≈ 7 posts)


def load_accounts(path) -> list:
    """-> [{"username", "category", "enabled", ...}] from the YAML; a missing file is an empty list."""
    path = Path(path)
    if not path.exists():
        return []
    data = read_yaml(path) or {}
    accounts = data.get("accounts") or []
    if not isinstance(accounts, list):
        raise ConfigError(f"{path.name}: `accounts` precisa ser uma lista")
    out = []
    for n, acc in enumerate(accounts):
        if not isinstance(acc, dict) or not USERNAME.match(str(acc.get("username", ""))):
            raise ConfigError(f"{path.name}: conta {n + 1} sem `username` válido")
        if acc.get("category") not in CATEGORIES + ("fora",):
            raise ConfigError(f"{path.name}: @{acc['username']}: `category` deve ser ia, saude ou fora")
        out.append(acc)
    return out


def daily_shares(accounts, max_usd, floor=FLOOR_USD) -> dict:
    """The daily cap split between the categories by their enabled accounts, in cents. A category with accounts gets at
    least `floor` (when the cap allows it), and the largest takes the rest, so the shares add up to the cap."""
    counts = {c: sum(1 for a in accounts if a.get("enabled") and a.get("category") == c) for c in CATEGORIES}
    total, cents = sum(counts.values()), round(max_usd * 100)
    if not total or cents <= 0:
        return dict.fromkeys(CATEGORIES, 0.0)
    least = min(round(floor * 100), cents // sum(1 for n in counts.values() if n))
    shares = {c: max(round(cents * n / total), least) if n else 0 for c, n in counts.items()}
    largest = max(CATEGORIES, key=counts.get)
    shares[largest] = cents - sum(v for c, v in shares.items() if c != largest)
    return {c: v / 100 for c, v in shares.items()}


def post_urls(text) -> list:
    """Canonical post URLs (one per shortcode) found in a message."""
    seen, out = set(), []
    for kind, code in POST_URL.findall(text or ""):
        if code not in seen:
            seen.add(code)
            out.append(f"https://www.instagram.com/{'reel' if kind in ('reel', 'reels') else 'p'}/{code}/")
    return out


def normalize(post, provider="apify") -> dict | None:
    """Apify post -> {shortcode, owner, caption, media[], timestamp, type, provider, url, video_url}."""
    code = post.get("shortCode") or post.get("shortcode")
    if not code:
        return None
    media = []
    children = post.get("childPosts") or []
    for child in children:
        if child.get("displayUrl"):
            media.append({"type": (child.get("type") or "Image").lower(), "url": child["displayUrl"],
                          "alt": child.get("alt") or ""})
    if not media:
        for url in (post.get("images") or [])[:10]:
            media.append({"type": "image", "url": url, "alt": ""})
    if not media and post.get("displayUrl"):
        media.append({"type": (post.get("type") or "Image").lower(), "url": post["displayUrl"], "alt": post.get("alt") or ""})
    kind = "reel" if post.get("productType") == "clips" or post.get("type") == "Video" else \
        "carousel" if post.get("type") == "Sidecar" else "image"
    return {"shortcode": code, "owner": post.get("ownerUsername") or "", "owner_name": post.get("ownerFullName") or "",
            "caption": (post.get("caption") or "").strip(), "media": media, "timestamp": post.get("timestamp") or "",
            "type": kind, "provider": provider, "url": f"https://www.instagram.com/{'reel' if kind == 'reel' else 'p'}/{code}/",
            "video_url": post.get("videoUrl") or "", "pinned": bool(post.get("isPinned"))}


def to_result(post, source, description="", manual=False) -> Result:
    caption = post["caption"]
    first = next((line.strip() for line in caption.splitlines() if line.strip()), "")
    title = f"@{post['owner']}: {first[:110]}" if first else f"@{post['owner']} · {post['type']}"
    text = caption + (f"\n\n[conteúdo visual] {description}" if description else "")
    return Result(id=post["shortcode"], title=title, authors=[post["owner"]] if post["owner"] else [],
                  date=post["timestamp"][:10], url=post["url"], abstract=text, source=source,
                  extra={"canonical_id": f"ig:{post['shortcode']}", "kind": "instagram_post", "manual": manual,
                         "instagram": {k: post[k] for k in ("owner", "type", "provider", "timestamp")}
                         | {"media": len(post["media"])}})


class InstagramSource(Source):
    keywordless = True
    ai_specific = True          # the accounts were curated as AI or health: no keyword filter

    def __init__(self, apify, accounts_path, state_path, category, describer=None, per_account=3, max_days=3,
                 max_usd=0.15, now=None):
        self.name = f"instagram-{category}"
        self.apify, self.accounts_path, self.state_path = apify, Path(accounts_path), Path(state_path)
        self.category, self.describer, self.per_account = category, describer, per_account
        self.max_days, self.max_usd, self._now = max_days, max_usd, now
        self.max_items = 60

    def _state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save(self, state) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")

    def fetch(self, limit):
        accounts = load_accounts(self.accounts_path)
        names = [a["username"] for a in accounts if a.get("enabled") and a["category"] == self.category]
        budget = daily_shares(accounts, self.max_usd)[self.category]
        if not names or budget <= 0 or not self.apify.configured:
            return []
        now = self._now or datetime.now(timezone.utc)
        turn = now.date().toordinal() % len(names)
        names = names[turn:] + names[:turn]               # when the cap cuts a run, other accounts are left out each day
        state = self._state()
        mark = state.get(f"since_{self.category}")
        since = max(datetime.fromisoformat(mark), now - timedelta(days=self.max_days)) if mark else now - timedelta(days=1)
        payload = {"directUrls": [f"https://www.instagram.com/{u}/" for u in names], "resultsType": "posts",
                   "resultsLimit": self.per_account, "onlyPostsNewerThan": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "addParentData": False}
        raw = self.apify.run(ACTOR, payload, max_usd=budget, max_items=len(names) * self.per_account)
        order = list(state.get("seen") or [])             # oldest first, so the trim drops the oldest
        seen = set(order)
        out = []
        for post in (normalize(p) for p in raw):
            if post is None or post["shortcode"] in seen:
                continue
            if post["timestamp"] and post["timestamp"] < since.isoformat()[:19] and post["pinned"]:
                continue                                  # an old pinned post that the filter let through
            seen.add(post["shortcode"])
            order.append(post["shortcode"])
            description = self.describer(post) if self.describer else ""
            out.append(to_result(post, "instagram", description))
            if len(out) >= limit:
                break
        state[f"since_{self.category}"] = now.isoformat(timespec="seconds")
        state["seen"] = order[-2000:]
        self._save(state)
        return out
