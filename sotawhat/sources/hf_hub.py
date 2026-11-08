# sotawhat/sources/hf_hub.py
"""Hugging Face Hub models and datasets (SDD §7.6) through the REST API: medical-tagged and trending ones.
HF_TOKEN raises the rate limit; the TLS store is the Windows one (truststore, injected by the CLI)."""
import httpx

from sotawhat.models import Result
from sotawhat.sources.base import Source

API = "https://huggingface.co/api"


class HFHubSource(Source):
    keywordless = True
    ai_specific = True

    def __init__(self, name, queries, per_query=10, max_items=20, token="", client=None):
        # queries: (label, "models" | "datasets", params), e.g. ("medical-models", "models", {"filter": "medical"})
        self.name = name
        self.queries = list(queries)
        self.feeds = [(label, kind) for label, kind, _ in self.queries]
        self.per_query, self.max_items, self.token = per_query, max_items, token
        self.feed_errors = {}
        self._client = client

    def fetch(self, limit):
        client = self._client or httpx.Client(timeout=30, follow_redirects=True)
        headers = {"User-Agent": "sotawhat/3.0"} | ({"Authorization": f"Bearer {self.token}"} if self.token else {})
        self.feed_errors, results, seen = {}, [], set()
        try:
            for label, kind, params in self.queries:
                try:
                    r = client.get(f"{API}/{kind}", headers=headers,
                                   params={"direction": "-1", "limit": self.per_query, "full": "true", **params})
                    r.raise_for_status()
                except httpx.HTTPError as exc:
                    self.feed_errors[label] = f"{type(exc).__name__}: {exc}"
                    continue
                for entry in r.json():
                    key = (kind, entry["id"])
                    if key not in seen:
                        seen.add(key)
                        results.append(self._result(kind, entry))
        finally:
            if self._client is None:
                client.close()
        return results[:limit]

    def _result(self, kind, entry) -> Result:
        repo_id = entry["id"]
        tags = [t for t in entry.get("tags") or [] if not t.startswith(("region:", "endpoints_compatible"))][:12]
        facts = [f"♥ {entry.get('likes', 0)}", f"↓ {entry.get('downloads', 0)}", f"created {(entry.get('createdAt') or '')[:10]}"]
        if kind == "models":
            head = f"Hugging Face machine learning model · pipeline {entry.get('pipeline_tag') or '?'}"
            if entry.get("library_name"):
                head += f" · library {entry['library_name']}"
            url, item_kind = f"https://huggingface.co/{repo_id}", "model"
            title = f"{repo_id} ({entry.get('pipeline_tag') or 'modelo'})"
            body = ""
        else:
            head, url, item_kind = "Hugging Face dataset for machine learning", f"https://huggingface.co/datasets/{repo_id}", "dataset"
            body = " ".join((entry.get("description") or "").split())[:1500]
            title = f"{repo_id}: {body[:100]}" if body else repo_id
        text = " · ".join([head] + facts + ([f"tags: {', '.join(tags)}"] if tags else [])) + (f"\n{body}" if body else "")
        return Result(id=url, title=title[:200], authors=[entry.get("author") or repo_id.split("/")[0]],
                      date=(entry.get("createdAt") or "")[:10], url=url, abstract=text, source=f"hf:{self.name}",
                      extra={"kind": item_kind, "likes": entry.get("likes", 0)})
