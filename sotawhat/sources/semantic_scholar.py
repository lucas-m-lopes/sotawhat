# sotawhat/sources/semantic_scholar.py
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_API = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,abstract,authors,year,url,externalIds,publicationDate"

def parse_response(payload):
    results = []
    for p in payload.get("data", []):
        ext = p.get("externalIds") or {}
        pid = ext.get("DOI") or p.get("paperId") or p.get("url") or ""
        authors = [a.get("name", "") for a in (p.get("authors") or [])]
        date = p.get("publicationDate") or (str(p.get("year")) if p.get("year") else "")
        results.append(Result(
            id=str(pid), title=p.get("title") or "", authors=authors,
            date=date or "", url=p.get("url") or "",
            abstract=p.get("abstract") or "", source="semantic_scholar"))
    return results

class SemanticScholarSource(Source):
    name = "semantic_scholar"

    def search(self, keyword, limit):
        params = {"query": keyword, "limit": limit, "fields": _FIELDS}
        resp = httpx.get(_API, params=params, timeout=30, follow_redirects=True,
                         headers={"User-Agent": "sotawhat/2.0"})
        resp.raise_for_status()
        return parse_response(resp.json())
