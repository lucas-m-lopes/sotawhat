# sotawhat/sources/hf_papers.py
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_API = "https://huggingface.co/api/daily_papers"

def parse_response(payload):
    results = []
    for item in payload:
        paper = item.get("paper") or {}
        pid = paper.get("id") or ""
        authors = [a.get("name", "") for a in (paper.get("authors") or [])]
        url = f"https://huggingface.co/papers/{pid}" if pid else ""
        results.append(Result(
            id=str(pid), title=paper.get("title") or "", authors=authors,
            date=(item.get("publishedAt") or "")[:10], url=url,
            abstract=paper.get("summary") or "", source="hf_papers"))
    return results

class HFPapersSource(Source):
    name = "hf_papers"

    @staticmethod
    def _filter(results, keyword, limit):
        kw = keyword.lower()
        hits = [r for r in results if kw in (r.title + " " + r.abstract).lower()]
        return hits[:limit]

    def search(self, keyword, limit):
        resp = httpx.get(_API, params={"limit": 100}, timeout=30,
                         follow_redirects=True,
                         headers={"User-Agent": "sotawhat/2.0"})
        resp.raise_for_status()
        results = parse_response(resp.json())
        return self._filter(results, keyword, limit)
