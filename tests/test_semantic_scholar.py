# tests/test_semantic_scholar.py
import json
from datetime import date

import httpx
import pytest

from sotawhat.config import Settings
from sotawhat.items import canonical_id
from sotawhat.profiles import build_sources
from sotawhat.sources.semantic_scholar import KEY_HINT, RateLimited, SemanticScholarSource, parse_response

PAPERS = {"total": 3, "data": [
    {"paperId": "p1", "title": "Agents that plan", "abstract": "We study agents.", "year": 2026,
     "publicationDate": "2026-10-02", "url": "https://www.semanticscholar.org/paper/p1", "citationCount": 41,
     "authors": [{"name": "A. Silva"}], "externalIds": {"ArXiv": "2610.01234", "DOI": "10.48550/arXiv.2610.01234"}},
    {"paperId": "p2", "title": "A personal health agent", "abstract": None, "year": 2026, "publicationDate": None,
     "url": "https://www.semanticscholar.org/paper/p2", "citationCount": 12, "authors": [],
     "externalIds": {"DOI": "10.1038/s41591-026-0001-1"}},
    {"paperId": "p3", "title": "No ids", "abstract": "x", "year": None, "publicationDate": None,
     "url": "https://www.semanticscholar.org/paper/p3", "authors": None, "externalIds": None}]}


def test_parse_semantic_scholar():
    payload = json.load(open("tests/fixtures/semantic_scholar_transformer.json", encoding="utf-8"))
    results = parse_response(payload)
    assert len(results) >= 1
    r = results[0]
    assert r.source == "semantic_scholar"
    assert r.title
    assert r.id  # paperId or DOI


def test_a_paper_on_arxiv_is_the_item_the_arxiv_source_brings():
    arxiv, journal, bare = parse_response(PAPERS)
    assert arxiv.url == "https://arxiv.org/abs/2610.01234" and arxiv.extra == {"citations": 41}
    assert canonical_id(arxiv) == ("arxiv:2610.01234", {"arxiv_id": "2610.01234"})
    assert canonical_id(journal)[0] == "doi:10.1038/s41591-026-0001-1" and journal.date == "2026" and journal.abstract == ""
    assert bare.id == "p3" and bare.authors == [] and bare.extra == {}


class _Api:
    """Answers the statuses given, in order; records every call and every wait."""
    def __init__(self, *statuses, retry_after=None):
        self.statuses, self.calls, self.waits, self.retry_after = list(statuses), [], [], retry_after

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        status = self.statuses.pop(0)
        headers = {"retry-after": self.retry_after} if status == 429 and self.retry_after else {}
        return httpx.Response(status, json=PAPERS if status == 200 else {"message": "Too Many Requests"},
                              headers=headers, request=httpx.Request("GET", url))


def _source(api, **kwargs):
    return SemanticScholarSource(get=api.get, sleep=api.waits.append, today=lambda: date(2026, 11, 20), **kwargs)


def test_bulk_search_of_the_most_cited_recent_papers():
    api = _Api(200)
    results = _source(api, top=2).search("large language model", 1)
    url, sent = api.calls[0]
    assert url.endswith("/graph/v1/paper/search/bulk")
    assert sent["params"]["query"] == '"large language model"' and sent["params"]["sort"] == "citationCount:desc"
    assert sent["params"]["publicationDateOrYear"] == "2026-09-21:2026-11-20"
    assert sent["params"]["fieldsOfStudy"] == "Computer Science" and sent["params"]["minCitationCount"] == 2
    assert "x-api-key" not in sent["headers"]
    assert [r.title for r in results] == ["Agents that plan", "A personal health agent"]     # the `top` most cited
    assert api.waits == []


def test_the_key_goes_in_the_header_and_requests_are_paced():
    api = _Api(200, 200)
    source = _source(api, api_key=" s2-key ")
    source.search("agent", 10)
    source.search("diffusion model", 10)
    assert api.calls[0][1]["headers"]["x-api-key"] == "s2-key" and api.calls[0][1]["params"]["query"] == "agent"
    assert api.waits == [1.1]                              # between the keywords, not before the first one


def test_a_429_is_retried_and_then_explained():
    api = _Api(429, 429, 200)
    assert len(_source(api).search("agent", 10)) == 3
    assert api.waits == [2.0, 4.0]
    asked = _Api(429, 200, retry_after="7")
    _source(asked).search("agent", 10)
    assert asked.waits == [7.0]
    saturated = _Api(429, 429, 429, 429)
    with pytest.raises(RateLimited) as err:
        _source(saturated).search("agent", 10)
    assert str(err.value) == KEY_HINT and len(saturated.calls) == 4 and saturated.waits == [2.0, 4.0, 8.0]
    warnings = []
    assert _source(_Api(429, 429, 429, 429)).safe_search("agent", 10, on_error=warnings.append) == []
    assert "SEMANTIC_SCHOLAR_API_KEY" in warnings[0]
    with pytest.raises(RateLimited, match="mesmo com a chave"):
        _source(_Api(429, 429, 429, 429), api_key="k").search("agent", 10)
    with pytest.raises(httpx.HTTPStatusError):
        _source(_Api(500)).search("agent", 10)


def test_the_profile_passes_the_key_from_the_settings():
    source = next(s for s in build_sources("geral", settings=None) if s.name == "semantic_scholar")
    assert source.api_key == ""
    keyed = Settings(_env_file=None, semantic_scholar_api_key="abc")
    sources = build_sources("geral", settings=keyed)
    assert next(s for s in sources if s.name == "semantic_scholar").api_key == "abc"
