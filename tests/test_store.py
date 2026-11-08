# tests/test_store.py
import json
from types import SimpleNamespace

from sotawhat.store.db import Store


def _item(iid, concepts=("k1",)):
    return SimpleNamespace(
        id=iid, kind="paper", source="arxiv", source_id=iid.split(":")[-1], url=f"https://x/{iid}",
        doi=None, arxiv_id=None, pmid=None, title=f"T {iid}", authors=["A"], published_at="2026-11-07",
        text="abstract", content_hash="h", concepts=list(concepts), profile="geral")


def test_schema_created(tmp_path):
    with Store(tmp_path / "db" / "insight.db") as st:
        names = {r[0] for r in st.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"items", "runs", "source_state", "llm_calls", "meta"} <= names
        version = st.conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        assert version == "2"


def test_upsert_dedupes_and_merges_concepts(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        assert st.upsert_items([_item("arxiv:1"), _item("arxiv:2")], run) == ["arxiv:1", "arxiv:2"]
        assert st.upsert_items([_item("arxiv:1", concepts=("k2",))], run) == []
        assert st.count_items() == 2
        row = st.conn.execute("SELECT concepts_json FROM items WHERE id='arxiv:1'").fetchone()
        assert json.loads(row[0]) == ["k1", "k2"]


def test_run_lifecycle_sums_llm_cost(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        for cost in (0.01, 0.02):
            st.record_llm_call(run_id=run, task="triage", requested_model="m", status="ok", cost_usd=cost)
        st.finish_run(run, ok=True, stats={"collected": 3})
        last = st.last_run("daily")
        assert last["ok"] == 1
        assert abs(last["cost_usd"] - 0.03) < 1e-9
        assert json.loads(last["stats_json"]) == {"collected": 3}


def test_source_failures_count_and_reset(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        assert st.record_source_error("medical/nature", "HTML") == 1
        assert st.record_source_error("medical/nature", "HTML") == 2
        st.record_source_ok("medical/nature")
        assert st.source_states()[0]["consecutive_failures"] == 0


def test_llm_cost_since_and_unknown_field_guard(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        st.record_llm_call(task="smoke", requested_model="m", status="ok", cost_usd=0.5)
        assert st.llm_cost_since("2000-01-01T00:00:00+00:00") == 0.5
        assert st.llm_cost_since("2999-01-01T00:00:00+00:00") == 0
        try:
            st.record_llm_call(task="x", requested_model="m", status="ok", prompt="secret")
        except ValueError as exc:
            assert "prompt" in str(exc)
        else:
            raise AssertionError("unknown field accepted")
