# tests/test_fda_batch.py
"""FDA AI-enabled device list (baseline + diff) and The Batch (sitemap + issue split), recorded 2026-11-08."""
import json
from pathlib import Path

import httpx
import pytest

from sotawhat.items import to_item
from sotawhat.sources.fda import FDAAIDevicesSource
from sotawhat.sources.the_batch import TheBatchSource, split_issue

FIX = Path("tests/fixtures")
CSV = (FIX / "fda_ai_devices.csv").read_text(encoding="utf-8")


def _client(handler, log):
    def wrapped(request):
        log.append(request)
        return handler(request)
    return httpx.Client(transport=httpx.MockTransport(wrapped))


def test_fda_first_run_is_a_baseline_then_new_submissions_come_in(tmp_path):
    state, body = tmp_path / "state" / "fda.json", {"csv": CSV}
    src = FDAAIDevicesSource(state, client=_client(lambda r: httpx.Response(200, text=body["csv"]), []))
    assert src.fetch(30) == [] and len(json.loads(state.read_text())["known"]) == 10
    body["csv"] = CSV + ('07/02/2026,K261234,"NeuroScan AI (v2)","Brain Co, Inc.",Neurology,QIH\n'
                         '07/01/2026,DEN260001,SepsisWatch,Duke Health,Clinical Chemistry,SKH\n')
    results = src.fetch(30)
    assert [r.title for r in results] == ["FDA autoriza dispositivo com IA: NeuroScan AI (v2) (Brain Co, Inc.)",
                                          "FDA autoriza dispositivo com IA: SepsisWatch (Duke Health)"]
    k, den = results
    assert k.url == "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K261234"
    assert den.url == "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/denovo.cfm?ID=DEN260001"
    assert k.date == "2026-07-02" and "AI-enabled medical device" in k.abstract and "panel Neurology" in k.abstract
    assert to_item(k).kind == "regulation" and src.ai_specific
    assert src.fetch(30) == []                                              # already known
    pma = FDAAIDevicesSource(tmp_path / "x.json")._url("P250008")
    assert pma == "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?id=P250008"


def test_fda_download_failure_keeps_the_state(tmp_path):
    state = tmp_path / "fda.json"
    state.write_text(json.dumps({"known": ["K1"]}))
    src = FDAAIDevicesSource(state, client=_client(lambda r: httpx.Response(503, text="down"), []))
    with pytest.raises(httpx.HTTPError):
        src.fetch(30)
    assert json.loads(state.read_text()) == {"known": ["K1"]}


def test_split_issue_into_stories():
    html = (FIX / "batch_issue_378.html").read_text(encoding="utf-8")
    published, stories = split_issue(html)
    assert published == "2026-11-06"
    assert [s["slug"] for s in stories] == ["gemini-leads-the-pack-again", "anthropic-pursues-a-public-offering",
                                            "world-models-become-robot-playgrounds", "context-engineering-for-images"]
    first = stories[0]
    assert first["title"] == "Gemini Leads the Pack Again" and first["text"].startswith("Google’s Gemini 4 Carbon")
    assert "What’s new:" in first["text"] and "<" not in first["text"] and len(first["text"]) <= 3000
    assert first["link"].startswith("https://blog.google/")


def test_the_batch_reads_the_newest_issues_once(tmp_path):
    log = []
    sitemap = (FIX / "batch_sitemap.xml").read_text(encoding="utf-8")
    issue = (FIX / "batch_issue_378.html").read_text(encoding="utf-8")

    def handler(request):
        if request.url.path.endswith("sitemap.xml"):
            return httpx.Response(200, text=sitemap)
        return httpx.Response(200, text=issue)

    src = TheBatchSource(tmp_path / "batch.json", max_issues=2, client=_client(handler, log))
    results = src.fetch(20)
    pages = [r.url.path for r in log if "issue-" in r.url.path]
    assert pages == ["/the-batch/issue-378", "/the-batch/issue-377"]
    assert len(results) == 8 and results[0].id == "https://www.deeplearning.ai/the-batch/issue-378#gemini-leads-the-pack-again"
    assert results[0].source == "the-batch" and to_item(results[0]).kind == "newsletter_item"
    assert results[0].date == "2026-11-06" and results[0].extra["link"].startswith("https://blog.google/")
    log.clear()
    assert src.fetch(20) == [] and [r.url.path for r in log] == ["/sitemap.xml"]      # issues already read


def test_stories_of_one_issue_keep_distinct_canonical_ids(tmp_path):
    sitemap = (FIX / "batch_sitemap.xml").read_text(encoding="utf-8")
    issue = (FIX / "batch_issue_378.html").read_text(encoding="utf-8")
    src = TheBatchSource(tmp_path / "b.json", max_issues=1, client=_client(
        lambda r: httpx.Response(200, text=sitemap if r.url.path.endswith("sitemap.xml") else issue), []))
    ids = [to_item(r).id for r in src.fetch(20)]
    assert len(set(ids)) == 4 and ids[0] == "thebatch:378#gemini-leads-the-pack-again"
