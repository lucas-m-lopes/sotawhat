"""Star history for the radar, from GitHub's star history endpoint (`GET /repos/{owner}/{repo}/stargazers/history`,
changelog 2026-09-04). It gives the stars given on each day, in weeks that start on Sunday, newest first, and never who
gave them. GITHUB_TOKEN reads it (5,000 requests an hour; it also answers without a token, at 60).

Who starred a repository, with the date, is no longer an option: since July 2026 GitHub lists it only to the
repository's admins and collaborators. Others get an empty list from GraphQL, 404 with a classic token and 403 with a
fine-grained one, whatever the scopes (measured 2026-11-10).

The count at the end of day d is the latest daily count minus the stars given after d up to that count's day, so the
week the radar measures is the sum of the days the endpoint gives. Removed stars leave the history, so a past count can
be a few stars high. A real daily count is never overwritten, and an empty or malformed answer stops the run instead of
writing flat counts."""
from datetime import date, datetime, timedelta, timezone

import httpx

from sotawhat.radar.discover import GITHUB, github_headers

API_VERSION = "2026-03-10"
PROBE_REPO = "octocat/Hello-World"


class HistoryError(Exception):
    """The endpoint refused, changed its answer, or the rate limit is near: the history stops for this run."""


def star_days(client, token, name, today, weeks=3):
    """({day: stars given that day}, requests left in the hour) for the last `weeks` weeks up to `today` (today is
    partial). None when the repository no longer exists."""
    r = client.get(f"{GITHUB}/repos/{name}/stargazers/history", params={"per_page": weeks},
                   headers=github_headers(token) | {"X-GitHub-Api-Version": API_VERSION})
    if r.status_code == 404:
        return None
    if r.status_code in (401, 403, 422, 429):
        raise HistoryError(f"o GitHub recusou o histórico de estrelas (HTTP {r.status_code})")
    r.raise_for_status()
    days = {}
    try:
        weeks_back = r.json()
        for week in weeks_back:
            start = datetime.fromtimestamp(week["week"], timezone.utc).date()
            if len(week["days"]) != 7:
                raise ValueError("a week without 7 days")
            for n, count in enumerate(week["days"]):
                if (day := start + timedelta(days=n)) <= today:
                    days[day] = int(count)
    except (KeyError, TypeError, ValueError) as exc:
        raise HistoryError(f"o histórico de estrelas mudou de formato ({exc})") from None
    if not days:
        raise HistoryError(f"o GitHub devolveu o histórico de estrelas de {name} vazio")
    remaining = r.headers.get("x-ratelimit-remaining")
    return days, int(remaining) if remaining is not None else None


def backfill(store, client, token, today, days=14, limit=None, min_remaining=100) -> dict:
    """Counts for the `days` before the latest daily count of every tracked repository without a count from a week ago
    or earlier (the most recent finds first, at most `limit`). -> {"repos", "days", "gone", "stopped"}."""
    since, week_ago = today - timedelta(days=days), (today - timedelta(days=7)).isoformat()
    rows = store.conn.execute(
        "SELECT r.full_name, r.name, s.day, s.stars FROM radar_repos r JOIN radar_stars s ON s.full_name = r.full_name"
        " AND s.day = (SELECT MAX(day) FROM radar_stars m WHERE m.full_name = r.full_name AND m.day <= ?)"
        " WHERE NOT EXISTS (SELECT 1 FROM radar_stars o WHERE o.full_name = r.full_name AND o.day <= ?)"
        " ORDER BY r.last_seen DESC, r.full_name" + (" LIMIT ?" if limit else ""),
        (today.isoformat(), week_ago) + ((limit,) if limit else ())).fetchall()
    out = {"repos": 0, "days": 0, "gone": 0, "stopped": None}
    for row in rows:
        try:
            got = star_days(client, token, row["name"], today, weeks=min(30, days // 7 + 2))
        except (HistoryError, httpx.HTTPError, ValueError) as exc:
            out["stopped"] = str(exc)[:200]
            break
        if got is None:
            out["gone"] += 1
            continue
        given, remaining = got
        anchor = date.fromisoformat(row["day"])
        counts = []
        for n in range(days):
            day = since + timedelta(days=n)
            if day < anchor:
                after = sum(stars for d, stars in given.items() if day < d <= anchor)
                counts.append((day.isoformat(), max(row["stars"] - after, 0)))
        with store._lock:
            cur = store.conn.executemany("INSERT OR IGNORE INTO radar_stars(full_name, day, stars) VALUES(?,?,?)",
                                         [(row["full_name"], day, count) for day, count in counts])
            store.conn.commit()
        out["repos"] += 1
        out["days"] += cur.rowcount
        if remaining is not None and remaining < min_remaining:
            out["stopped"] = f"limite da API do GitHub quase no fim ({remaining} pedidos); o resto fica para a próxima varredura"
            break
    return out


def probe(client, token, today=None) -> str | None:
    """None when the star history endpoint answers with a week of days; otherwise the reason (for `doctor`)."""
    try:
        got = star_days(client, token, PROBE_REPO, today or datetime.now(timezone.utc).date(), weeks=1)
    except (HistoryError, httpx.HTTPError) as exc:
        return str(exc)[:160]
    return f"{PROBE_REPO} não encontrado" if got is None else None
