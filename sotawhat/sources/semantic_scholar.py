# sotawhat/sources/semantic_scholar.py
"""Semantic Scholar (keyword source of the general profile): the most cited papers of the last `days` days.

Until 2026-11-20 this source asked the relevance search (`/paper/search`) without a key. That endpoint answers
429 to the anonymous pool practically always (14 daily runs in a row), and when it did answer it ranked by
relevance with no date, so the digest got classics of 2023. Now:
- the bulk search (`/paper/search/bulk`), which the anonymous pool still serves (a 429 goes away after a short
  wait), restricted to the last `days` days and sorted by citations: what the field is already building on,
  which neither arXiv nor the newsletters rank;
- `SEMANTIC_SCHOLAR_API_KEY` goes in the `x-api-key` header when set (free, 1 request a second of your own);
- a 429 is retried with a growing wait, and one request a second at most.
A paper that is on arXiv takes its arXiv id and URL, so it is the same item the arXiv source brings."""
import time
from datetime import date, timedelta

import httpx

from sotawhat.models import Result
from sotawhat.sources.base import Source

_API = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
_FIELDS = "title,abstract,authors,year,url,externalIds,publicationDate,citationCount"
KEY_HINT = ("o pool anônimo do Semantic Scholar está saturado (429): peça a chave grátis em "
            "semanticscholar.org/product/api e ponha em SEMANTIC_SCHOLAR_API_KEY no .env")


class RateLimited(Exception):
    pass


def parse_response(payload):
    results = []
    for p in payload.get("data") or []:
        ext = p.get("externalIds") or {}
        arxiv = ext.get("ArXiv")
        pid = arxiv or ext.get("DOI") or p.get("paperId") or p.get("url") or ""
        url = f"https://arxiv.org/abs/{arxiv}" if arxiv else (p.get("url") or "")
        authors = [a.get("name", "") for a in (p.get("authors") or [])]
        when = p.get("publicationDate") or (str(p.get("year")) if p.get("year") else "")
        extra = {"citations": p["citationCount"]} if p.get("citationCount") is not None else {}
        results.append(Result(
            id=str(pid), title=p.get("title") or "", authors=authors,
            date=when or "", url=url,
            abstract=p.get("abstract") or "", source="semantic_scholar", extra=extra))
    return results


class SemanticScholarSource(Source):
    name = "semantic_scholar"

    def __init__(self, api_key="", days=60, top=10, min_citations=2, fields_of_study="Computer Science", retries=3,
                 pause=1.1, get=httpx.get, sleep=time.sleep, today=date.today):
        self.api_key = (api_key or "").strip()
        self.days, self.top, self.min_citations = days, top, min_citations
        self.fields_of_study = fields_of_study
        self.retries, self.pause = retries, pause
        self._get, self._sleep, self._today = get, sleep, today
        self._called = False

    def _params(self, keyword) -> dict:
        end = self._today()
        params = {"query": f'"{keyword}"' if " " in keyword else keyword, "fields": _FIELDS,
                  "publicationDateOrYear": f"{end - timedelta(days=self.days)}:{end}", "sort": "citationCount:desc"}
        if self.min_citations:
            params["minCitationCount"] = self.min_citations
        if self.fields_of_study:
            params["fieldsOfStudy"] = self.fields_of_study
        return params

    def search(self, keyword, limit):
        headers = {"User-Agent": "sotawhat/3.0"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        if self._called:
            self._sleep(self.pause)          # one request a second, with or without a key
        self._called = True
        for attempt in range(self.retries + 1):
            resp = self._get(_API, params=self._params(keyword), timeout=60, follow_redirects=True, headers=headers)
            if resp.status_code != 429:
                break
            if attempt < self.retries:
                asked = resp.headers.get("retry-after", "")
                self._sleep(min(float(asked), 30.0) if asked.replace(".", "", 1).isdigit() else 2.0 * 2 ** attempt)
        else:
            raise RateLimited(KEY_HINT if not self.api_key else
                              f"429 mesmo com a chave, depois de {self.retries + 1} tentativas")
        resp.raise_for_status()
        return parse_response(resp.json())[:max(limit, self.top)]
