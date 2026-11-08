# sotawhat/sources/mcp_registry.py
"""Official MCP registry (SDD §7.4, registry.modelcontextprotocol.io v0.1, public, no key): servers found by
health terms and, optionally, every server updated in the last `recent_days`. Only `active` servers."""
from datetime import date, timedelta

import httpx

from sotawhat.models import Result
from sotawhat.sources.base import Source

BASE = "https://registry.modelcontextprotocol.io/v0.1"
_OFFICIAL = "io.modelcontextprotocol.registry/official"


class MCPRegistrySource(Source):
    keywordless = True
    ai_specific = True

    def __init__(self, name, terms=(), recent_days=None, per_term=20, max_items=25, client=None, base_url=BASE,
                 today=None):
        self.name = name
        self.terms, self.recent_days, self.per_term = tuple(terms), recent_days, per_term
        self.max_items, self.base_url = max_items, base_url.rstrip("/")
        self.feeds = [(term, term) for term in self.terms] + ([("recent", "recent")] if recent_days else [])
        self.feed_errors = {}
        self._client, self._today = client, today

    def _requests(self):
        for term in self.terms:
            yield term, {"search": term, "version": "latest", "limit": self.per_term}
        if self.recent_days:
            since = (self._today or date.today()) - timedelta(days=self.recent_days)
            yield "recent", {"updated_since": f"{since.isoformat()}T00:00:00Z", "version": "latest", "limit": self.per_term}

    def fetch(self, limit):
        client = self._client or httpx.Client(timeout=30, follow_redirects=True)
        self.feed_errors, found = {}, {}
        try:
            for label, params in self._requests():
                try:
                    r = client.get(f"{self.base_url}/servers", params=params, headers={"User-Agent": "sotawhat/3.0"})
                    r.raise_for_status()
                except httpx.HTTPError as exc:
                    self.feed_errors[label] = f"{type(exc).__name__}: {exc}"
                    continue
                for entry in r.json().get("servers", []):
                    server, meta = entry.get("server") or {}, (entry.get("_meta") or {}).get(_OFFICIAL) or {}
                    if server.get("name") and meta.get("status", "active") == "active":
                        found.setdefault(server["name"], (server, meta))
        finally:
            if self._client is None:
                client.close()
        return [self._result(server, meta) for server, meta in list(found.values())[:limit]]

    def _result(self, server, meta) -> Result:
        name = server["name"]
        repo = (server.get("repository") or {}).get("url") or ""
        url = repo or server.get("websiteUrl") or f"{self.base_url}/servers?search={name}"
        remotes = sorted({r.get("type", "?") for r in server.get("remotes") or []})
        packages = sorted({p.get("registryType") or p.get("registry_type") or "?" for p in server.get("packages") or []})
        published = (meta.get("publishedAt") or "")[:10]
        facts = [f"MCP server (AI agents tool) · {name} v{server.get('version', '?')}", f"published {published}"]
        if remotes:
            facts.append("remotes: " + ", ".join(remotes))
        if packages:
            facts.append("packages: " + ", ".join(packages))
        description = " ".join((server.get("description") or "").split())
        return Result(id=url, title=f"{server.get('title') or name} — servidor MCP", authors=[name.split("/")[0]],
                      date=published, url=url, abstract=" · ".join(facts) + (f"\n{description}" if description else ""),
                      source=f"mcp:{self.name.removeprefix('mcp-') or 'registry'}", extra={"kind": "mcp_server"})
