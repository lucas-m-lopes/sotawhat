"""Discovery, every day: the GitHub searches of each front, and the GitHub repositories in the news on Hacker News
(Algolia's public API, no key). The official MCP registry is not crawled: more than 6,000 servers changed in the two
weeks before 2026-11-10, and a change says nothing about use. MCP servers come from the searches, and their use
from the downloads of their packages (measure.py)."""
import json
import re
import time
from dataclasses import dataclass
from datetime import timedelta

import httpx

GITHUB = "https://api.github.com"
HN = "https://hn.algolia.com/api/v1/search"
_REPO = re.compile(r"https?://(?:www\.)?github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)")
_PAGES = {"orgs", "topics", "features", "sponsors", "marketplace", "settings", "apps", "collections", "trending",
          "about", "pricing", "login", "site", "enterprise", "events", "explore", "notifications", "search", "users"}


def repo_name(url):
    """'owner/repo' from a GitHub URL; None for the pages that are no repository."""
    match = _REPO.match(url or "")
    if match is None or match.group(1).lower() in _PAGES:
        return None
    repo = match.group(2).removesuffix(".git")
    return f"{match.group(1)}/{repo}" if repo.strip(".") else None


def github_headers(token, raw=False) -> dict:
    headers = {"Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "sotawhat/3.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@dataclass
class Find:
    name: str                       # owner/repo as GitHub writes it
    source: str                     # github | hn
    front: str | None = None
    repo: dict | None = None        # the search answer: stars, description, topics...
    story: dict | None = None       # the Hacker News story


def _error(errors, label, exc) -> None:
    if errors is not None:
        errors[label] = f"{type(exc).__name__}: {str(exc)[:160]}"


def search_github(client, token, cfg, today, sleep=time.sleep, errors=None) -> list:
    """Two searches per query: the active ones already in use (stars, recent push) and the new ones that climb."""
    lim, finds = cfg.limits, []
    active = (today - timedelta(days=lim["active_pushed_days"])).isoformat()
    new = (today - timedelta(days=lim["new_created_days"])).isoformat()
    for front in cfg.fronts.values():
        for query in front.queries:
            for q in (f"{query} stars:>={lim['active_min_stars']} pushed:>={active} fork:false archived:false",
                      f"{query} created:>={new} stars:>={lim['new_min_stars']} fork:false archived:false"):
                try:
                    r = client.get(f"{GITHUB}/search/repositories", headers=github_headers(token),
                                   params={"q": q, "sort": "stars", "order": "desc", "per_page": lim["per_query"]})
                    r.raise_for_status()
                    finds += [Find(repo["full_name"], "github", front.key, repo=repo)
                              for repo in r.json().get("items", []) if repo.get("full_name")]
                except (httpx.HTTPError, ValueError) as exc:
                    _error(errors, f"github: {query}", exc)
                if sleep:
                    sleep(lim["search_pause_s"])
    return finds


def hn_repos(client, cfg, now, errors=None) -> list:
    """GitHub repositories linked by the Hacker News stories of the last `hn_days` with at least `hn_min_points`."""
    lim = cfg.limits
    since = int((now - timedelta(days=lim["hn_days"])).timestamp())
    try:
        r = client.get(HN, headers={"User-Agent": "sotawhat/3.0"},
                       params={"query": "github.com", "restrictSearchableAttributes": "url", "tags": "story",
                               "numericFilters": f"created_at_i>{since},points>={lim['hn_min_points']}",
                               "hitsPerPage": 200})
        r.raise_for_status()
        hits = r.json().get("hits", [])
    except (httpx.HTTPError, ValueError) as exc:
        _error(errors, "hn", exc)
        return []
    finds = []
    for hit in hits:
        name = repo_name(hit.get("url"))
        if name:
            finds.append(Find(name, "hn", story={"id": str(hit.get("objectID")), "title": hit.get("title") or "",
                                                 "points": hit.get("points") or 0,
                                                 "comments": hit.get("num_comments") or 0,
                                                 "created_at": hit.get("created_at") or ""}))
    return finds


def repo_fields(repo) -> dict:
    """The radar_repos columns that a GitHub repository answer refreshes."""
    return {"name": repo["full_name"], "description": " ".join((repo.get("description") or "").split())[:300],
            "language": repo.get("language"), "license": (repo.get("license") or {}).get("spdx_id") or None,
            "topics_json": json.dumps(repo.get("topics") or []), "created_at": (repo.get("created_at") or "")[:10] or None,
            "homepage": repo.get("homepage") or None}


def record(store, finds, today) -> dict:
    """Upserts what was found. Fronts and sources accumulate, a search answer refreshes the description and gives today's
    stars, and the Hacker News stories are kept with their points. -> {"found", "new"}."""
    day, merged = today.isoformat(), {}
    for find in finds:
        entry = merged.setdefault(find.name.lower(), {"name": find.name, "fronts": set(), "sources": set(), "repo": None,
                                                      "stories": {}})
        if find.front:
            entry["fronts"].add(find.front)
        entry["sources"].add(find.source)
        entry["repo"] = entry["repo"] or find.repo
        if find.story:
            entry["stories"][find.story["id"]] = find.story
    new, conn = 0, store.conn
    with store._lock:
        for key, entry in merged.items():
            row = conn.execute("SELECT fronts_json, sources_json FROM radar_repos WHERE full_name = ?", (key,)).fetchone()
            if row is None:
                new += 1
                conn.execute("INSERT INTO radar_repos(full_name, name, first_seen, last_seen) VALUES(?,?,?,?)",
                             (key, entry["name"], day, day))
            fronts = sorted(entry["fronts"] | set(json.loads(row["fronts_json"]) if row else ()))
            sources = sorted(entry["sources"] | set(json.loads(row["sources_json"]) if row else ()))
            fields = {"fronts_json": json.dumps(fronts), "sources_json": json.dumps(sources), "last_seen": day,
                      **(repo_fields(entry["repo"]) if entry["repo"] else {})}
            conn.execute("UPDATE radar_repos SET " + ", ".join(f"{k} = ?" for k in fields) + " WHERE full_name = ?",
                         [*fields.values(), key])
            repo = entry["repo"]
            if repo:
                conn.execute("INSERT OR REPLACE INTO radar_stars(full_name, day, stars, forks, pushed_at) VALUES(?,?,?,?,?)",
                             (key, day, repo.get("stargazers_count") or 0, repo.get("forks_count"), repo.get("pushed_at")))
            for story in entry["stories"].values():
                conn.execute("INSERT OR REPLACE INTO radar_hn(full_name, story_id, title, points, comments, created_at)"
                             " VALUES(?,?,?,?,?,?)", (key, story["id"], story["title"], story["points"],
                                                       story["comments"], story["created_at"]))
        conn.commit()
    return {"found": len(merged), "new": new}
