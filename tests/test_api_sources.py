# tests/test_api_sources.py
"""P2 API channel sources against recorded answers (2026-11-08): GitHub, Hugging Face Hub, MCP registry, medRxiv."""
import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

from sotawhat.items import to_item
from sotawhat.sources.github import GitHubSource
from sotawhat.sources.hf_hub import HFHubSource
from sotawhat.sources.mcp_registry import MCPRegistrySource
from sotawhat.sources.medrxiv import MedRxivSource

FIX = Path("tests/fixtures")
TODAY = date(2026, 11, 8)


def fixture(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def client(handler, log):
    def wrapped(request):
        log.append(request)
        return handler(request)
    return httpx.Client(transport=httpx.MockTransport(wrapped))


def test_github_search_readme_and_dedup():
    log = []

    def handler(request):
        path = request.url.path
        if path == "/search/repositories":
            q = parse_qs(urlsplit(str(request.url)).query)["q"][0]
            return httpx.Response(200, json=fixture("github_search_medical.json" if "medical" in q else "github_search.json"))
        if path.endswith("/readme"):
            if "sandbox-mcp" in path:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(200, text="# Title\n\nA README that explains the project. " * 200)
        return httpx.Response(500)

    src = GitHubSource("github-med", [("medical-imaging", "topic:medical-imaging"), ("mcp", "topic:mcp-server")],
                       days=7, min_stars=3, token="ghp_x", client=client(handler, log), today=TODAY)
    results = src.fetch(10)
    searches = [r for r in log if r.url.path == "/search/repositories"]
    q = parse_qs(urlsplit(str(searches[0].url)).query)
    assert q["q"][0] == "topic:medical-imaging created:>2026-11-01 stars:>=3 fork:false archived:false"
    assert q["sort"] == ["stars"] and searches[0].headers["authorization"] == "Bearer ghp_x"
    names = [r.id for r in results]
    assert len(names) == len(set(names)) == 5                               # sandbox-mcp came from both queries
    stars = [int(r.abstract.split("★ ")[1].split(" ")[0].replace(",", "")) for r in results]
    assert stars == sorted(stars, reverse=True)                             # most starred first
    sandbox = next(r for r in results if "sandbox-mcp" in r.id)
    assert sandbox.id == "https://github.com/shanselman/sandbox-mcp" and sandbox.extra["kind"] == "repo"
    assert sandbox.title.startswith("shanselman/sandbox-mcp — Fresh, throwaway Windows machines")
    assert "★ 314" in sandbox.abstract and "license MIT" in sandbox.abstract and "topics: ai-agents, mcp" in sandbox.abstract
    assert "README" not in sandbox.abstract                                 # a missing README is fine
    other = next(r for r in results if "sandbox-mcp" not in r.id)
    assert "A README that explains" in other.abstract and len(other.abstract) < 3200
    assert to_item(sandbox).id == "url:https://github.com/shanselman/sandbox-mcp" and to_item(sandbox).kind == "repo"
    assert len(src.fetch(2)) == 2


def test_github_without_token_and_failing_query():
    log = []

    def handler(request):
        if "mcp" in str(request.url):
            return httpx.Response(403, json={"message": "API rate limit exceeded"})
        return httpx.Response(200, json=fixture("github_search_medical.json"))

    src = GitHubSource("github", [("medical", "topic:medical-imaging"), ("mcp", "topic:mcp-server")], readme_chars=0,
                       client=client(handler, log), today=TODAY)
    assert len(src.fetch(10)) == 3 and "mcp" in src.feed_errors and "authorization" not in log[0].headers


def test_hugging_face_models_datasets_and_trending():
    log = []

    def handler(request):
        kind = request.url.path.rsplit("/", 1)[-1]
        params = parse_qs(urlsplit(str(request.url)).query)
        if kind == "datasets":
            return httpx.Response(200, json=fixture("hf_datasets_medical.json"))
        return httpx.Response(200, json=fixture("hf_models_medical.json" if "filter" in params else "hf_trending.json"))

    src = HFHubSource("hf-med", [("medical-models", "models", {"filter": "medical", "sort": "trendingScore"}),
                                 ("medical-datasets", "datasets", {"filter": "medical", "sort": "trendingScore"}),
                                 ("trending", "models", {"sort": "trendingScore"})],
                      per_query=3, token="hf_x", client=client(handler, log))
    results = src.fetch(20)
    assert {r.extra["kind"] for r in results} == {"model", "dataset"} and src.ai_specific
    model = next(r for r in results if r.id.endswith("medec-biomedbert-detector"))
    assert model.id == "https://huggingface.co/crissebasbol/medec-biomedbert-detector"
    assert "machine learning model" in model.abstract and "text-classification" in model.abstract
    dataset = next(r for r in results if r.extra["kind"] == "dataset")
    assert dataset.id.startswith("https://huggingface.co/datasets/") and "colonoscopy" in dataset.abstract.lower()
    assert log[0].headers["authorization"] == "Bearer hf_x"
    assert parse_qs(urlsplit(str(log[0].url)).query)["direction"] == ["-1"]


def test_mcp_registry_terms_status_and_ids():
    log, data = [], fixture("mcp_registry_servers.json")
    data["servers"][2]["_meta"]["io.modelcontextprotocol.registry/official"]["status"] = "deprecated"

    def handler(request):
        return httpx.Response(200, json=data)

    src = MCPRegistrySource("mcp-health", terms=("health", "fhir"), per_term=5, client=client(handler, log), today=TODAY)
    results = src.fetch(10)
    assert [parse_qs(urlsplit(str(r.url)).query)["search"] for r in log] == [["health"], ["fhir"]]
    assert len(results) == 2                                               # deduplicated, deprecated one dropped
    first = results[0]
    assert first.id == "https://github.com/kipmcc/aviado-mcp" and first.extra["kind"] == "mcp_server"
    assert first.title == "Aviado AI — servidor MCP" and "MCP server (AI agents tool)" in first.abstract
    assert "streamable-http" in first.abstract and first.date == "2026-10-14"
    recent = MCPRegistrySource("mcp-new", recent_days=2, client=client(handler, log), today=TODAY)
    recent.fetch(5)
    assert parse_qs(urlsplit(str(log[-1].url)).query)["updated_since"] == ["2026-11-06T00:00:00Z"]


def test_medrxiv_window_categories_and_paging():
    log = []
    page = fixture("medrxiv_details.json")
    first_page = {"messages": [page["messages"][0] | {"count": 2, "total": "4"}], "collection": page["collection"][:2]}
    second_page = {"messages": [page["messages"][0] | {"count": 2, "total": "4"}], "collection": page["collection"][2:4]}

    def handler(request):
        cursor = request.url.path.rstrip("/").split("/")[-2]
        return httpx.Response(200, json=first_page if cursor == "0" else second_page)

    src = MedRxivSource(categories=("health informatics", "oncology"), days=2, client=client(handler, log), today=TODAY)
    results = src.fetch(10)
    assert [r.url.path for r in log] == ["/details/medrxiv/2026-11-06/2026-11-08/0/json",
                                         "/details/medrxiv/2026-11-06/2026-11-08/2/json"]
    assert {r.extra["category"] for r in results} == {"health informatics", "oncology"}
    paper = results[0]
    assert paper.id.startswith("doi:10.") and paper.url.startswith("https://www.medrxiv.org/content/10.")
    assert len(paper.authors) > 1 and to_item(paper).kind == "paper" and not src.ai_specific
