# tests/test_store_v2.py
import sqlite3
import threading

import numpy as np

from sotawhat.items import Item, from_row
from sotawhat.store.db import Store


def _item(n, title=None, profile="medico", source="pubmed", text="machine learning for sepsis"):
    return Item(id=f"pmid:{n}", kind="paper", source=source, source_id=str(n), title=title or f"Paper {n}",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", authors=["Ana"], published_at="2026-11-07",
                text=text, pmid=str(n), profile=profile)


def test_v1_database_is_migrated_in_place(tmp_path):
    path = tmp_path / "insight.db"
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO meta VALUES('schema_version', '1');
        CREATE TABLE items(id TEXT PRIMARY KEY, kind TEXT NOT NULL, source TEXT NOT NULL, source_id TEXT,
            canonical_url TEXT, doi TEXT, arxiv_id TEXT, pmid TEXT, title TEXT NOT NULL,
            authors_json TEXT NOT NULL DEFAULT '[]', published_at TEXT, fetched_at TEXT NOT NULL, text TEXT,
            content_hash TEXT, concepts_json TEXT NOT NULL DEFAULT '[]', profile TEXT,
            status TEXT NOT NULL DEFAULT 'new', first_run_id INTEGER);
        INSERT INTO items(id, kind, source, title, fetched_at) VALUES('pmid:1', 'paper', 'pubmed', 'Old', '2026-11-07');
    """)
    con.commit()
    con.close()
    with Store(path) as st:
        names = {r[0] for r in st.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"triage", "embeddings", "clusters", "feedback", "deliveries", "classifier_models", "inbox"} <= names
        assert st.meta_get("schema_version") == "3"
        row = st.conn.execute("SELECT title, cluster_id FROM items WHERE id = 'pmid:1'").fetchone()
        assert tuple(row) == ("Old", None)


def test_triage_candidates_and_error_retries(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([_item(1), _item(2), _item(3)], run)
        st.record_triage("pmid:1", run, "main", total=4.1, scores={"A": 4}, tags={"domains": ["A03"]})
        st.record_triage("pmid:2", run, "error", reason="timeout")
        since = "2000-01-01T00:00:00+00:00"
        assert {r["id"] for r in st.triage_candidates(since)} == {"pmid:2", "pmid:3"}
        st.record_triage("pmid:2", run, "error", reason="timeout")
        st.record_triage("pmid:2", run, "error", reason="timeout")
        assert {r["id"] for r in st.triage_candidates(since)} == {"pmid:3"}     # 3 attempts: gave up
        rows = st.triage_rows(run)
        assert [r["item_id"] for r in rows] == ["pmid:1"] and rows[0]["title"] == "Paper 1"
        assert st.triage_counts(run) == {"main": 1, "error": 1}


def test_embeddings_round_trip_with_filters(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([_item(1), _item(2)], run)
        st.save_embeddings("m", [("pmid:1", np.array([1, 0], dtype=np.float32)),
                                 ("pmid:2", np.array([0, 1], dtype=np.float32))])
        ids, matrix = st.load_embeddings("m", exclude={"pmid:2"})
        assert ids == ["pmid:1"] and matrix.tolist() == [[1.0, 0.0]]
        assert st.embedded_ids("m", ["pmid:1", "pmid:9"]) == {"pmid:1"}
        assert st.load_embeddings("other")[0] == []
        assert st.load_embeddings("m", since_iso="2999-01-01")[0] == []


def test_latest_vote_wins_and_profile_filter(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([_item(1), _item(2, profile="geral")], run)
        st.add_feedback("item", "pmid:1", "up", "telegram")
        st.add_feedback("item", "pmid:1", "down", "telegram")
        st.add_feedback("item", "pmid:2", "test", "telegram")
        assert st.item_votes() == {"pmid:1": "down", "pmid:2": "test"}
        assert st.item_votes(profile="geral") == {"pmid:2": "test"}
        assert st.item_votes(ids=["pmid:1"]) == {"pmid:1": "down"}


def test_deliveries_by_key_and_message(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        a = st.record_delivery(1, "2026-11-08", "pmid:1", "k1", "radar", 1)
        b = st.record_delivery(1, "2026-11-08", "pmid:2", "k2", "radar", 2)
        st.mark_delivered([a, b], 42, 1001)
        assert st.delivery_by_key("k2")["item_id"] == "pmid:2"
        assert [r["key"] for r in st.deliveries_for_message("42", 1001)] == ["k1", "k2"]


def test_clusters_sources_and_redaction(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([_item(1), _item(2, source="crossref")], run)
        st.join_cluster("pmid:2", "pmid:1")
        assert st.cluster_sources("pmid:1") == ["crossref", "pubmed"]
        st.save_embeddings("m", [("pmid:1", np.array([1, 0], dtype=np.float32))])
        st.redact_item("pmid:1")
        item = from_row(st.get_items(["pmid:1"])[0])
        assert item.text == "" and "removido" in item.title and st.load_embeddings("m")[0] == []


def test_ledger_writes_from_threads(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        def work():
            for _ in range(25):
                st.record_llm_call(task="triage", requested_model="m", status="ok", cost_usd=0.001)
                st.llm_cost_since("2000-01-01")
        threads = [threading.Thread(target=work) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert st.conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0] == 100
        assert abs(st.avg_llm_cost("triage") - 0.001) < 1e-9
