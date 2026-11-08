# sotawhat/sources/github.py
"""New and rising GitHub repositories (SDD §7.3): one Search API query per topic or term, created in the
last `days` with at least `min_stars`, most starred first, plus the start of each README so the triage
and the extraction see what the project does. Authenticated with GITHUB_TOKEN when present (30 search
requests/min instead of 10); a failing query is reported per label and the others go on."""
from datetime import date, timedelta

import httpx

from sotawhat.models import Result
from sotawhat.sources.base import Source

API = "https://api.github.com"


class GitHubSource(Source):
    keywordless = True

    def __init__(self, name, queries, days=7, min_stars=5, per_query=10, max_items=25, token="", readme_chars=2500,
                 client=None, today=None):
        self.name = name
        self.feeds = list(queries)          # (label, query): per-label health, like the RSS feeds
        self.days, self.min_stars, self.per_query = days, min_stars, per_query
        self.max_items, self.token, self.readme_chars = max_items, token, readme_chars
        self.feed_errors = {}
        self._client, self._today = client, today

    def _headers(self, raw=False):
        headers = {"Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "sotawhat/3.0"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _readme(self, client, full_name) -> str:
        if not self.readme_chars:
            return ""
        try:
            r = client.get(f"{API}/repos/{full_name}/readme", headers=self._headers(raw=True), timeout=20)
        except httpx.HTTPError:
            return ""
        return " ".join(r.text.split())[:self.readme_chars] if r.status_code == 200 else ""

    def fetch(self, limit):
        since = ((self._today or date.today()) - timedelta(days=self.days)).isoformat()
        client = self._client or httpx.Client(timeout=30, follow_redirects=True)
        self.feed_errors = {}
        repos = {}
        try:
            for label, query in self.feeds:
                q = f"{query} created:>{since} stars:>={self.min_stars} fork:false archived:false"
                try:
                    r = client.get(f"{API}/search/repositories", headers=self._headers(),
                                   params={"q": q, "sort": "stars", "order": "desc", "per_page": self.per_query})
                    r.raise_for_status()
                except httpx.HTTPError as exc:
                    self.feed_errors[label] = f"{type(exc).__name__}: {exc}"
                    continue
                for repo in r.json().get("items", []):
                    repos.setdefault(repo["full_name"], repo)
            ranked = sorted(repos.values(), key=lambda repo: -(repo.get("stargazers_count") or 0))[:limit]
            return [self._result(repo, self._readme(client, repo["full_name"])) for repo in ranked]
        finally:
            if self._client is None:
                client.close()

    def _result(self, repo, readme) -> Result:
        description = " ".join((repo.get("description") or "").split())
        license_id = (repo.get("license") or {}).get("spdx_id") or "?"
        facts = [f"GitHub repository · ★ {repo.get('stargazers_count', 0):,}", f"forks {repo.get('forks_count', 0)}",
                 repo.get("language") or "?", f"license {license_id}", f"created {(repo.get('created_at') or '')[:10]}"]
        topics = repo.get("topics") or []
        if topics:
            facts.append("topics: " + ", ".join(topics))
        text = " · ".join(facts) + (f"\n{description}" if description else "") + (f"\n\nREADME: {readme}" if readme else "")
        title = repo["full_name"] + (f" — {description}" if description else "")
        return Result(id=repo["html_url"], title=title[:200], authors=[repo["full_name"].split("/")[0]],
                      date=(repo.get("created_at") or "")[:10], url=repo["html_url"], abstract=text,
                      source=f"github:{self.name.removeprefix('github-') or 'search'}",
                      extra={"kind": "repo", "stars": repo.get("stargazers_count", 0)})
