# tests/test_daily.py
from datetime import date

from sotawhat.models import Result
from sotawhat.pipeline.daily import ALERT_AFTER, render_summary, run_daily, to_plain
from sotawhat.store.db import Store

DAY = date(2026, 11, 8)


class FakeSource:
    def __init__(self, name, results=(), error=None, feeds=(), feed_errors=None):
        self.name = name
        self.results = list(results)
        self.error = error
        self.feeds = list(feeds)
        self.feed_errors = dict(feed_errors or {})

    def safe_search(self, keyword, limit, on_error=None):
        if self.error:
            if on_error:
                on_error(f"[{self.name}] failed: {self.error}")
            return []
        return list(self.results)


def _r(rid, source, title="Deep learning for sepsis", url=None):
    return Result(id=rid, title=title, authors=["A"], date="2026-11-07",
                  url=url or f"https://arxiv.org/abs/{rid}", abstract="machine learning model", source=source)


def test_new_items_are_stored_once_across_runs(tmp_path):
    sources = {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv"), _r("2511.00002", "arxiv")])]}
    with Store(tmp_path / "insight.db") as st:
        first = run_daily(st, sources, today=DAY)
        assert first.ok and first.collected == {"geral": 2} and len(first.new_items) == 2
        second = run_daily(st, sources, today=DAY)
        assert second.new_items == [] and st.count_items() == 2


def test_same_paper_from_arxiv_and_hf_counts_once(tmp_path):
    sources = {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv")]),
                         FakeSource("hf_papers", [_r("2511.00001", "hf_papers",
                                                     url="https://huggingface.co/papers/2511.00001")])]}
    with Store(tmp_path / "insight.db") as st:
        report = run_daily(st, sources, today=DAY)
        assert report.collected == {"geral": 1}
        assert [it.id for it in report.new_items] == ["arxiv:2511.00001"]


def test_medico_keeps_only_ai_items(tmp_path):
    clinical = Result(id="41000001", title="Aspirin dosing trial", authors=[], date="", url="",
                      abstract="no method here", source="pubmed")
    ai = _r("41000002", "pubmed", url="https://pubmed.ncbi.nlm.nih.gov/41000002/")
    sources = {"medico": [FakeSource("pubmed", [clinical, ai])]}
    with Store(tmp_path / "insight.db") as st:
        report = run_daily(st, sources, today=DAY)
        assert [it.id for it in report.new_items] == ["pmid:41000002"]


def test_failing_sources_and_feeds_raise_alert_after_three_runs(tmp_path):
    rss = FakeSource("medical", feeds=[("nature", "u1"), ("jmir-ai", "u2")],
                     feed_errors={"nature": "FeedError: HTML instead of a feed"})
    down = FakeSource("pubmed", error="HTTP 503")
    with Store(tmp_path / "insight.db") as st:
        for _ in range(ALERT_AFTER):
            report = run_daily(st, {"medico": [rss, down]}, today=DAY)
        assert report.failing["medical/nature"][0] == ALERT_AFTER
        assert report.failing["pubmed"][0] == ALERT_AFTER
        assert "medical/jmir-ai" not in report.failing and "medical" not in report.failing
        text = render_summary(report)
        assert "medical/nature" in text and f"alerta: {ALERT_AFTER}ª falha seguida" in text


def test_summary_escapes_html_and_links_new_items(tmp_path):
    evil = _r("2511.00009", "arxiv", title='<script>x</script> & "LLM"')
    with Store(tmp_path / "insight.db") as st:
        text = render_summary(run_daily(st, {"geral": [FakeSource("arxiv", [evil])]}, today=DAY))
    assert "&lt;script&gt;" in text and "<script>" not in text
    assert '<a href="https://arxiv.org/abs/2511.00009">' in text
    assert "run diário 2026-11-08" in to_plain(text)


def test_unexpected_error_closes_run_as_failed(tmp_path, monkeypatch):
    with Store(tmp_path / "insight.db") as st:
        def boom(items, run_id):
            raise RuntimeError("disk full")
        monkeypatch.setattr(st, "upsert_items", boom)
        report = run_daily(st, {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv")])]}, today=DAY)
        assert not report.ok and "disk full" in report.error
        assert st.last_run("daily")["ok"] == 0
        assert "❌" in render_summary(report)


def test_triage_stage_runs_after_collection_and_is_recorded(tmp_path):
    import json

    from sotawhat.pipeline.triage import TriageStats

    seen = []

    def triage(store, run_id):
        seen.append((run_id, store.count_items()))
        return TriageStats(triaged=2, main=1, rejected=1)

    sources = {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv"), _r("2511.00002", "arxiv")])]}
    with Store(tmp_path / "insight.db") as st:
        report = run_daily(st, sources, today=DAY, triage=triage)
        assert seen == [(report.run_id, 2)] and report.triage.main == 1
        stats = json.loads(st.last_run("daily")["stats_json"])
        assert stats["triage"]["triaged"] == 2


def test_triage_crash_fails_the_run_but_keeps_the_items(tmp_path):
    def triage(store, run_id):
        raise RuntimeError("embedder exploded")

    sources = {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv")])]}
    with Store(tmp_path / "insight.db") as st:
        report = run_daily(st, sources, today=DAY, triage=triage)
        assert not report.ok and "embedder exploded" in report.error and st.count_items() == 1


def test_on_start_gets_the_run_id_before_collection(tmp_path):
    seen = []

    class Watching(FakeSource):
        def safe_search(self, keyword, limit, on_error=None):
            seen.append(("search", keyword))
            return super().safe_search(keyword, limit, on_error)

    with Store(tmp_path / "insight.db") as st:
        report = run_daily(st, {"geral": [Watching("arxiv", [_r("2511.00001", "arxiv")])]}, today=DAY,
                           on_start=lambda run_id: seen.append(("start", run_id)))
    assert seen[0] == ("start", report.run_id) and seen[1][0] == "search"


def test_a_known_item_sent_by_hand_goes_back_to_the_triage(tmp_path):
    scanned = Result(id="C1", title="@medai.br: post", authors=[], date="2026-11-07", url="https://www.instagram.com/p/C1/",
                     abstract="machine learning", source="instagram",
                     extra={"canonical_id": "ig:C1", "kind": "instagram_post"})
    sent = Result(id="C1", title="@medai.br: post", authors=[], date="2026-11-07", url="https://www.instagram.com/p/C1/",
                  abstract="machine learning", source="manual:telegram",
                  extra={"canonical_id": "ig:C1", "kind": "instagram_post", "manual": True})
    with Store(tmp_path / "insight.db") as st:
        run_daily(st, {"geral": [FakeSource("instagram-ia", [scanned])]}, today=DAY)
        st.record_triage("ig:C1", 1, "reject")
        report = run_daily(st, {"medico": [FakeSource("manual-telegram", [sent])]}, today=DAY)
        assert report.new_items == [] and st.conn.execute("SELECT source FROM items").fetchone()[0] == "manual:telegram"
        assert [r["id"] for r in st.triage_candidates("2000-01-01")] == ["ig:C1"]
