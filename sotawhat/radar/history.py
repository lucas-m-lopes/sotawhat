"""Star history for the radar, from who starred each repository and when. It uses GITHUB_STARS_TOKEN, a classic personal
access token without scopes (read-only public data). GitHub requires authentication to list stargazers, and a
fine-grained token gets 403 there.

The GraphQL API lists stargazers newest first, so a few pages give the stars of the last two weeks, even for
repositories past the REST pagination limit. The count at the end of day d is the stars now minus the stars given after
d. Unstars are not visible, so a count is at most a few stars high. A real daily count is never overwritten."""
from datetime import date, timedelta

import httpx

from sotawhat.radar.discover import github_headers

GRAPHQL = "https://api.github.com/graphql"
QUERY = """query($owner: String!, $name: String!, $after: String) {
  rateLimit { remaining }
  repository(owner: $owner, name: $name) {
    stargazerCount
    stargazers(first: 100, after: $after, orderBy: {field: STARRED_AT, direction: DESC}) {
      edges { starredAt }
      pageInfo { hasNextPage endCursor }
    }
  }
}"""
PROBE = 'query { repository(owner: "octocat", name: "Hello-World") { stargazers(first: 1) { edges { starredAt } } } }'


class HistoryError(Exception):
    """The token cannot read stargazers, or the GraphQL limit is near: the history stops for this run."""


def _post(client, token, query, variables=None) -> dict:
    r = client.post(GRAPHQL, headers=github_headers(token), json={"query": query, "variables": variables or {}})
    if r.status_code in (401, 403):
        raise HistoryError(f"o GitHub recusou o GITHUB_STARS_TOKEN (HTTP {r.status_code})")
    r.raise_for_status()
    return r.json()


def _errors(body) -> set:
    return {e.get("type") or e.get("message", "?") for e in body.get("errors") or []}


def star_dates(client, token, name, since, max_pages=5):
    """(stars now, [days of the stars given on or after `since`], first day with an exact count, GraphQL points
    left), newest first, at most `max_pages` pages of 100. None when the repository no longer exists."""
    owner, repo = name.split("/", 1)
    after, days, oldest = None, [], None
    for _ in range(max_pages):
        body = _post(client, token, QUERY, {"owner": owner, "name": repo, "after": after})
        errors = _errors(body)
        if "NOT_FOUND" in errors:
            return None
        if errors:
            raise HistoryError("GraphQL: " + ", ".join(sorted(errors))[:200])
        data = body["data"]
        node, remaining = data.get("repository"), (data.get("rateLimit") or {}).get("remaining")
        if node is None:
            return None
        page = node["stargazers"]
        stamps = [date.fromisoformat(e["starredAt"][:10]) for e in page["edges"]]
        days += [d for d in stamps if d >= since]
        if stamps:
            oldest = stamps[-1]
        if not stamps or oldest < since or not page["pageInfo"]["hasNextPage"]:
            return node["stargazerCount"], days, since, remaining
        after = page["pageInfo"]["endCursor"]
    return node["stargazerCount"], days, oldest, remaining     # cut: exact from the oldest star read on


def backfill(store, client, token, today, days=14, limit=None, max_pages=5, min_remaining=200) -> dict:
    """Counts for the `days` before today, for every tracked repository without a count from a week ago or earlier
    (the most recent finds first, at most `limit`). -> {"repos", "days", "gone", "stopped"}."""
    since, week_ago = today - timedelta(days=days), (today - timedelta(days=7)).isoformat()
    rows = store.conn.execute("SELECT full_name, name FROM radar_repos r WHERE NOT EXISTS (SELECT 1 FROM radar_stars s"
                              " WHERE s.full_name = r.full_name AND s.day <= ?) ORDER BY last_seen DESC, full_name"
                              + (" LIMIT ?" if limit else ""), (week_ago, limit) if limit else (week_ago,)).fetchall()
    out = {"repos": 0, "days": 0, "gone": 0, "stopped": None}
    for row in rows:
        try:
            got = star_dates(client, token, row["name"], since, max_pages)
        except (HistoryError, httpx.HTTPError, ValueError) as exc:
            out["stopped"] = str(exc)[:200]
            break
        if got is None:
            out["gone"] += 1
            continue
        total, starred, exact_from, remaining = got
        counts = [((since + timedelta(days=n)).isoformat(), total - sum(1 for d in starred if d > since + timedelta(days=n)))
                  for n in range(days) if since + timedelta(days=n) >= exact_from]
        with store._lock:
            cur = store.conn.executemany("INSERT OR IGNORE INTO radar_stars(full_name, day, stars) VALUES(?,?,?)",
                                         [(row["full_name"], day, count) for day, count in counts])
            store.conn.commit()
        out["repos"] += 1
        out["days"] += cur.rowcount
        if remaining is not None and remaining < min_remaining:
            out["stopped"] = f"limite do GraphQL quase no fim ({remaining} pontos); o resto fica para a próxima varredura"
            break
    return out


def probe(client, token) -> str | None:
    """None when the token can read stargazers; otherwise the reason (for `doctor`)."""
    try:
        errors = _errors(_post(client, token, PROBE))
    except (HistoryError, httpx.HTTPError, ValueError) as exc:
        return str(exc)[:160]
    return ("GraphQL: " + ", ".join(sorted(errors)))[:160] if errors else None
