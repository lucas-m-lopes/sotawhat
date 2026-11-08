# sotawhat/sources/medrxiv.py
"""medRxiv preprints through api.biorxiv.org (SDD §5.3, Tier 1 #6): every preprint of the last `days` days
in the chosen categories, cursor-paginated. The profile's AI-term filter then keeps the AI ones."""
from datetime import date, timedelta

import httpx

from sotawhat.models import Result
from sotawhat.sources.base import Source

API = "https://api.biorxiv.org/details/medrxiv/{start}/{end}/{cursor}/json"
CATEGORIES = ("health informatics", "radiology and imaging", "health systems and quality improvement",
              "emergency medicine", "intensive care and critical care medicine", "medical education")


class MedRxivSource(Source):
    keywordless = True

    def __init__(self, name="medrxiv", categories=CATEGORIES, days=2, max_pages=10, max_items=40, client=None,
                 today=None):
        self.name = name
        self.categories = {c.lower() for c in categories}
        self.days, self.max_pages, self.max_items = days, max_pages, max_items
        self._client, self._today = client, today

    def fetch(self, limit):
        end = self._today or date.today()
        start = end - timedelta(days=self.days)
        client = self._client or httpx.Client(timeout=40, follow_redirects=True)
        latest, cursor = {}, 0
        try:
            for _ in range(self.max_pages):
                r = client.get(API.format(start=start.isoformat(), end=end.isoformat(), cursor=cursor),
                               headers={"User-Agent": "sotawhat/3.0"})
                r.raise_for_status()
                data = r.json()
                page = data.get("collection") or []
                for paper in page:
                    if (paper.get("category") or "").lower() not in self.categories:
                        continue
                    kept = latest.get(paper["doi"])
                    if kept is None or int(paper.get("version") or 1) > int(kept.get("version") or 1):
                        latest[paper["doi"]] = paper
                message = (data.get("messages") or [{}])[0]
                cursor += int(message.get("count") or len(page))
                if not page or cursor >= int(message.get("total") or 0):
                    break
        finally:
            if self._client is None:
                client.close()
        papers = sorted(latest.values(), key=lambda p: p.get("date") or "", reverse=True)[:limit]
        return [Result(id=f"doi:{p['doi']}", title=" ".join(p["title"].split()),
                       authors=[a.strip() for a in (p.get("authors") or "").split(";") if a.strip()],
                       date=p.get("date") or "", url=f"https://www.medrxiv.org/content/{p['doi']}v{p.get('version') or 1}",
                       abstract=" ".join((p.get("abstract") or "").split()), source="medrxiv",
                       extra={"doi": p["doi"], "category": (p.get("category") or "").lower()}) for p in papers]
