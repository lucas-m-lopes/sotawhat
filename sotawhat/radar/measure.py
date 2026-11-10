"""Measures of the radar. Every day it counts the stars of every tracked repository. Every week, for the candidates, it
looks up their npm and PyPI packages, the downloads of the last two weeks, the latest release (for the two-week
rule) and the start of the README for the judge."""
import json
import tomllib
from datetime import timedelta

import httpx

from sotawhat.radar.discover import GITHUB, github_headers, repo_fields

NPM = "https://api.npmjs.org/downloads/range"
PYPI = "https://pypistats.org/api/packages"


def _drop(conn, keys) -> None:
    for table in ("radar_repos", "radar_stars", "radar_hn"):
        conn.executemany(f"DELETE FROM {table} WHERE full_name = ?", [(k,) for k in keys])


def snapshot(store, client, token, cfg, today, errors=None) -> dict:
    """GET /repos for each tracked repository without stars today, the most recent finds first, up to `track_max`.
    A repository GitHub no longer serves, an archived one, or one that nothing found for `forget_days` leaves the
    radar. -> {"counted", "gone", "forgotten"}."""
    day, conn = today.isoformat(), store.conn
    forget = (today - timedelta(days=cfg.limits["forget_days"])).isoformat()
    with store._lock:
        old = [r[0] for r in conn.execute("SELECT full_name FROM radar_repos WHERE last_seen < ?", (forget,))]
        _drop(conn, old)
        conn.commit()
    rows = conn.execute("SELECT full_name, name FROM radar_repos r WHERE NOT EXISTS (SELECT 1 FROM radar_stars s"
                        " WHERE s.full_name = r.full_name AND s.day = ?) ORDER BY last_seen DESC, full_name LIMIT ?",
                        (day, cfg.limits["track_max"])).fetchall()
    out = {"counted": 0, "gone": 0, "forgotten": len(old)}
    for row in rows:
        try:
            r = client.get(f"{GITHUB}/repos/{row['name']}", headers=github_headers(token))
        except httpx.HTTPError as exc:
            if errors is not None:
                errors[f"repo {row['name']}"] = f"{type(exc).__name__}: {str(exc)[:120]}"
            continue
        repo = r.json() if r.status_code == 200 else None
        if r.status_code in (404, 410, 451) or (repo and repo.get("archived")):
            with store._lock:
                _drop(conn, [row["full_name"]])
                conn.commit()
            out["gone"] += 1
            continue
        if repo is None:
            if errors is not None:
                errors[f"repo {row['name']}"] = f"HTTP {r.status_code}"
            if r.status_code in (403, 429):              # the rate limit: the rest are counted tomorrow
                break
            continue
        fields = repo_fields(repo)
        with store._lock:
            conn.execute("UPDATE radar_repos SET " + ", ".join(f"{k} = ?" for k in fields) + " WHERE full_name = ?",
                         [*fields.values(), row["full_name"]])
            conn.execute("INSERT OR REPLACE INTO radar_stars(full_name, day, stars, forks, pushed_at) VALUES(?,?,?,?,?)",
                         (row["full_name"], day, repo.get("stargazers_count") or 0, repo.get("forks_count"),
                          repo.get("pushed_at")))
            conn.commit()
        out["counted"] += 1
    return out


def find_packages(client, token, name) -> list:
    """The npm and PyPI packages published from the repository root: the package.json name (unless private) and
    the pyproject.toml project name."""
    out = []
    for path in ("package.json", "pyproject.toml"):
        try:
            r = client.get(f"{GITHUB}/repos/{name}/contents/{path}", headers=github_headers(token, raw=True))
        except httpx.HTTPError:
            continue
        if r.status_code != 200:
            continue
        try:
            if path == "package.json":
                data = json.loads(r.text)
                if isinstance(data, dict) and isinstance(data.get("name"), str) and not data.get("private"):
                    out.append({"registry": "npm", "name": data["name"]})
            else:
                data = tomllib.loads(r.text)
                pname = (data.get("project") or {}).get("name") or ((data.get("tool") or {}).get("poetry") or {}).get("name")
                if isinstance(pname, str) and pname:
                    out.append({"registry": "pypi", "name": pname})
        except ValueError:                                # JSON and TOML errors are both ValueErrors
            continue
    return out


def downloads(client, package, today):
    """(downloads in the 7 days up to yesterday, in the 7 before) of an npm or PyPI package; None when the registry
    does not know it. Both registries publish yesterday's counts at the earliest."""
    end = today - timedelta(days=1)
    start = end - timedelta(days=13)
    days = [(start + timedelta(days=n)).isoformat() for n in range(14)]
    try:
        if package["registry"] == "npm":
            r = client.get(f"{NPM}/{start.isoformat()}:{end.isoformat()}/{package['name']}")
            if r.status_code != 200:
                return None
            by_day = {d["day"]: d["downloads"] for d in r.json().get("downloads") or []}
        else:
            r = client.get(f"{PYPI}/{package['name'].lower()}/overall", params={"mirrors": "false"})
            if r.status_code != 200:
                return None
            by_day = {d["date"]: d["downloads"] for d in r.json().get("data") or []
                      if d.get("category") == "without_mirrors"}
    except (httpx.HTTPError, ValueError, KeyError):
        return None
    if not by_day:
        return None
    return sum(by_day.get(d, 0) for d in days[7:]), sum(by_day.get(d, 0) for d in days[:7])


def latest_release(client, token, name):
    try:
        r = client.get(f"{GITHUB}/repos/{name}/releases/latest", headers=github_headers(token))
        return (r.json().get("published_at") or "")[:10] or None if r.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None


def readme(client, token, name, chars=1500) -> str:
    try:
        r = client.get(f"{GITHUB}/repos/{name}/readme", headers=github_headers(token, raw=True))
    except httpx.HTTPError:
        return ""
    return " ".join(r.text.split())[:chars] if r.status_code == 200 else ""
