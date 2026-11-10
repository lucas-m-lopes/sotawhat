"""The week of the radar. Its signals are the stars gained (from the radar's own daily counts), the downloads and the
Hacker News points. The score is the mean percentile of the signals each repository has: absolute and relative star
growth, download growth and attention."""
import json
import re
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date, timedelta

# a repository that only Hacker News brought is measured only if it looks like AI tooling
AI_TERMS = re.compile(r"\b(ai|llms?|agents?|agentic|mcp|claude|codex|gpt|openai|anthropic|gemini|prompts?|tokens?|"
                      r"context|rag|embeddings?|evals?|inference|transformers?|tts|speech|voice|video|animation|"
                      r"manim|remotion|diffusion|models?|skills?)\b", re.I)
SIGNALS = ("week", "growth", "downloads_growth", "hn_points")


@dataclass
class Metrics:
    key: str                          # owner/repo in lower case
    name: str                         # as GitHub writes it
    fronts: list
    description: str
    topics: list
    language: str | None
    license: str | None
    created_at: str | None
    stars: int
    week: int | None = None           # stars gained in the last 7 days
    prev_week: int | None = None      # in the 7 days before
    estimated: bool = False           # fewer than 7 days of counts: scaled from what there is
    hn_points: int = 0
    hn_title: str = ""
    packages: list = field(default_factory=list)
    downloads: int | None = None      # npm + PyPI, the last 7 days
    prev_downloads: int | None = None
    release_at: str | None = None
    score: float = 0.0

    @property
    def url(self) -> str:
        return f"https://github.com/{self.name}"

    @property
    def growth(self):
        """Stars gained over the stars at the start of the week (at least 50, so a tiny repository does not win)."""
        return None if self.week is None else self.week / max(self.stars - self.week, 50)

    @property
    def downloads_growth(self):
        if self.downloads is None or self.prev_downloads is None:
            return None
        return (self.downloads - self.prev_downloads) / max(self.prev_downloads, 100)


def _near(series, target, tolerance=1):
    """Stars counted on `target` or on the nearest day within `tolerance` (earlier days first)."""
    for delta in range(tolerance + 1):
        for day in (target - timedelta(days=delta), target + timedelta(days=delta)):
            if day.isoformat() in series:
                return series[day.isoformat()]
    return None


def week_metrics(store, today) -> list:
    """Metrics of every tracked repository counted in the last two days. Without a count from a week ago, the stars
    gained are scaled to 7 days from the earliest count at least 2 days old, or, for a repository younger than 90
    days, from its age; both are marked as estimates."""
    conn, stars, hn = store.conn, {}, {}
    for full_name, day, count in conn.execute("SELECT full_name, day, stars FROM radar_stars WHERE day >= ?",
                                              ((today - timedelta(days=16)).isoformat(),)):
        stars.setdefault(full_name, {})[day] = count
    for full_name, title, points in conn.execute("SELECT full_name, title, points FROM radar_hn WHERE created_at >= ?"
                                                 " ORDER BY points DESC", ((today - timedelta(days=7)).isoformat(),)):
        total, first = hn.get(full_name, (0, title))
        hn[full_name] = (total + (points or 0), first)
    out = []
    for row in conn.execute("SELECT * FROM radar_repos ORDER BY full_name"):
        series = stars.get(row["full_name"], {})
        now = _near(series, today)
        if now is None:
            continue
        m = Metrics(key=row["full_name"], name=row["name"], fronts=json.loads(row["fronts_json"]),
                    description=row["description"] or "", topics=json.loads(row["topics_json"] or "[]"),
                    language=row["language"], license=row["license"], created_at=row["created_at"], stars=now,
                    packages=json.loads(row["packages_json"]) if row["packages_json"] else [], release_at=row["release_at"])
        week_ago = _near(series, today - timedelta(days=7))
        if week_ago is not None:
            m.week = max(now - week_ago, 0)
            two_ago = _near(series, today - timedelta(days=14))
            if two_ago is not None:
                m.prev_week = max(week_ago - two_ago, 0)
        else:
            older = sorted(d for d in series if (today - date.fromisoformat(d)).days >= 2)
            if older:
                gap = (today - date.fromisoformat(older[0])).days
                m.week, m.estimated = round(max(now - series[older[0]], 0) * 7 / gap), True
            elif m.created_at and 0 <= (age := (today - date.fromisoformat(m.created_at)).days) <= 90:
                m.week, m.estimated = round(now * min(7, age) / max(age, 1)), True
        m.hn_points, m.hn_title = hn.get(row["full_name"], (0, ""))
        out.append(m)
    return out


def eligible(m, cfg) -> bool:
    lim = cfg.limits
    if not m.fronts and not AI_TERMS.search(" ".join([m.description, m.hn_title, " ".join(m.topics),
                                                       m.name.replace("-", " ").replace("_", " ")])):
        return False
    return ((m.week or 0) >= lim["min_stars_week"] or (m.downloads or 0) >= lim["min_downloads_week"]
            or m.hn_points >= lim["min_hn_points"])


def rank(metrics, cfg) -> list:
    """The eligible repositories, best first. `score` (0–100) is the mean percentile of the signals each one has,
    over at least two, so a lone signal (Hacker News points only, say) scores 50 at most."""
    pool = [m for m in metrics if eligible(m, cfg)]
    values = {s: sorted(v for m in pool if (v := getattr(m, s)) is not None and (s != "hn_points" or v > 0))
              for s in SIGNALS}
    for m in pool:
        parts = [bisect_right(values[s], v) / len(values[s]) for s in SIGNALS
                 if (v := getattr(m, s)) is not None and (s != "hn_points" or v > 0)]
        m.score = round(100 * sum(parts) / max(len(parts), 2), 1) if parts else 0.0
    return sorted(pool, key=lambda m: (-m.score, -(m.week or 0), m.key))
