# sotawhat/ideation/prior_art.py
"""Prior art by layers (SDD §8.3, stage 6). Each layer returns up to `per_layer` neighbors and fails on its
own (a layer that errors returns [] and an error note):
- interno: items already in the graph;
- literatura: OpenAlex (polite pool with OPENALEX_EMAIL/CROSSREF_MAILTO) and Semantic Scholar (no key: 429s
  are tolerated);
- codigo: GitHub repository search;
- mercado: Exa (only with EXA_API_KEY).
Patents (Lens.org, EPO OPS) stay "não verificado" until the user gets the keys."""
import httpx

from sotawhat.graph import query as graph_query


class PriorArt:
    def __init__(self, store=None, mailto="", github_token="", exa_key="", client=None, per_layer=5):
        self.store, self.mailto, self.github_token, self.exa_key = store, mailto, github_token, exa_key
        self.per_layer, self._client = per_layer, client

    def _get(self, client, url, **kwargs):
        r = client.get(url, timeout=25, **kwargs)
        r.raise_for_status()
        return r.json()

    def search(self, query) -> dict:
        """-> {layer: [{"title", "year", "url"}], "_erros": {layer: message}, "_nao_verificado": [...]}."""
        out, errors = {}, {}
        client = self._client or httpx.Client(follow_redirects=True, headers={"User-Agent": "sotawhat/3.0"})
        try:
            layers = (("interno", self._internal), ("openalex", self._openalex), ("semantic_scholar", self._s2),
                      ("github", self._github), ("exa", self._exa))
            for name, fetch in layers:
                try:
                    found = fetch(client, query)
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    errors[name] = f"{type(exc).__name__}: {str(exc)[:120]}"
                    found = []
                if found is not None:
                    out[name] = found[:self.per_layer]
        finally:
            if self._client is None:
                client.close()
        out["_erros"] = errors
        out["_nao_verificado"] = ["patentes (Lens.org/EPO OPS sem chave)"] + ([] if self.exa_key else ["mercado (EXA_API_KEY vazio)"])
        return out

    def _internal(self, client, query):
        if self.store is None:
            return []
        hits = graph_query.search(self.store, query, limit=self.per_layer)["items"]
        return [{"title": h["title"], "year": (h["fetched_at"] or "")[:4], "url": h["url"]} for h in hits]

    def _openalex(self, client, query):
        params = {"search": query, "per-page": self.per_layer, "select": "title,publication_year,doi,id"}
        if self.mailto:
            params["mailto"] = self.mailto
        data = self._get(client, "https://api.openalex.org/works", params=params)
        return [{"title": w.get("title") or "", "year": w.get("publication_year"), "url": w.get("doi") or w.get("id")}
                for w in data.get("results", [])]

    def _s2(self, client, query):
        data = self._get(client, "https://api.semanticscholar.org/graph/v1/paper/search",
                         params={"query": query, "limit": self.per_layer, "fields": "title,year,url"})
        return [{"title": p.get("title") or "", "year": p.get("year"), "url": p.get("url")} for p in data.get("data", [])]

    def _github(self, client, query):
        headers = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        data = self._get(client, "https://api.github.com/search/repositories", headers=headers,
                         params={"q": f"{query} in:name,description,readme", "sort": "stars", "per_page": self.per_layer})
        return [{"title": f"{r['full_name']} — {(r.get('description') or '')[:120]}", "year": (r.get("created_at") or "")[:4],
                 "url": r["html_url"]} for r in data.get("items", [])]

    def _exa(self, client, query):
        if not self.exa_key:
            return None
        r = client.post("https://api.exa.ai/search", headers={"x-api-key": self.exa_key},
                        json={"query": query, "numResults": self.per_layer, "type": "auto"}, timeout=25)
        r.raise_for_status()
        return [{"title": x.get("title") or "", "year": (x.get("publishedDate") or "")[:4], "url": x.get("url")}
                for x in r.json().get("results", [])]


def render_neighbors(found) -> str:
    lines = []
    for layer, neighbors in found.items():
        if layer.startswith("_"):
            continue
        for n in neighbors:
            lines.append(f"[{layer}] {n['title']} ({n.get('year') or '?'})")
    for layer, error in (found.get("_erros") or {}).items():
        lines.append(f"[{layer}] indisponível: {error}")
    return "\n".join(lines) or "(nenhum vizinho encontrado)"
