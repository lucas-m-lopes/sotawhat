# tests/test_store_v3.py
"""Schema 3 (P3): the entity graph lives in SQLite (SDD §6.4, D16)."""
import sqlite3

import numpy as np

from sotawhat.items import Item
from sotawhat.store import db as dbmod
from sotawhat.store.db import Store


def _item(n, fetched=None, profile="medico"):
    return Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"Paper {n}",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", authors=["Ana"], published_at="2026-11-07",
                text="machine learning for sepsis", pmid=str(n), profile=profile)


def _store_with(tmp_path, decisions):
    """decisions: {n: decision}; item n is fetched n minutes after 2026-11-08T10:00."""
    st = Store(tmp_path / "insight.db")
    run = st.start_run("daily")
    st.upsert_items([_item(n) for n in decisions], run)
    for n, decision in decisions.items():
        st.conn.execute("UPDATE items SET fetched_at = ? WHERE id = ?", (f"2026-11-08T10:{n:02d}:00+00:00", f"pmid:{n}"))
        st.record_triage(f"pmid:{n}", run, decision, tags={"domains": ["A06"]})
    st.conn.commit()
    return st, run


def test_schema_2_database_is_upgraded_in_place(tmp_path):
    path = tmp_path / "insight.db"
    con = sqlite3.connect(path)
    con.executescript(dbmod._SCHEMA)
    con.executescript(dbmod._SCHEMA_V2)
    con.execute("ALTER TABLE items ADD COLUMN cluster_id TEXT")
    con.execute("INSERT INTO meta VALUES('schema_version', '2')")
    con.execute("INSERT INTO items(id, kind, source, title, fetched_at) VALUES('pmid:1', 'paper', 'pubmed', 'Old', 'x')")
    con.commit()
    con.close()
    for _ in range(2):   # opening twice must not fail
        with Store(path) as st:
            names = {r[0] for r in st.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert {"extractions", "entities", "entity_aliases", "entity_mentions", "entity_relations",
                    "entity_merges", "entity_embeddings"} <= names
            assert st.meta_get("schema_version") == "3"
            row = st.conn.execute("SELECT title, graph_synced_at FROM items WHERE id = 'pmid:1'").fetchone()
            assert tuple(row) == ("Old", None)


def test_record_extraction_is_an_upsert_that_counts_attempts(tmp_path):
    st, run = _store_with(tmp_path, {1: "main"})
    st.record_extraction("pmid:1", run, "error", model="m/a", prompt_version="extract_v1", error="timeout",
                         cost_usd=0.001)
    st.record_extraction("pmid:1", run, "ok", model="m/b", prompt_version="extract_v1",
                         payload={"entities": [{"name": "MedGemma 1.5"}]}, cost_usd=0.002)
    row = st.get_extraction("pmid:1")
    assert (row["status"], row["model"], row["attempts"], row["error"]) == ("ok", "m/b", 2, None)
    assert '"MedGemma 1.5"' in row["payload_json"] and row["cost_usd"] == 0.002
    st.close()


def test_extraction_candidates_are_approved_items_without_a_good_extraction(tmp_path):
    st, run = _store_with(tmp_path, {1: "radar", 2: "main", 3: "frontier", 4: "main", 5: "reject",
                                     6: "duplicate", 7: "main", 8: "main"})
    st.record_extraction("pmid:7", run, "ok", payload={})
    for _ in range(3):
        st.record_extraction("pmid:8", run, "error", error="bad json")
    ids = [r["id"] for r in st.extraction_candidates()]
    assert ids == ["pmid:4", "pmid:2", "pmid:3", "pmid:1"]          # main newest first, then frontier, radar
    assert [r["id"] for r in st.extraction_candidates(max_attempts=4)][:3] == ["pmid:8", "pmid:4", "pmid:2"]
    assert [r["id"] for r in st.extraction_candidates(limit=2)] == ["pmid:4", "pmid:2"]
    first = st.extraction_candidates()[0]
    assert first["decision"] == "main" and '"A06"' in first["tags_json"]
    st.close()


def test_entities_are_unique_per_type_and_aliases_resolve_by_group(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        a = st.add_entity("model", "MedGemma 1.5", "medgemma 1 5", category="C04")
        assert st.add_entity("model", "MedGemma-1.5", "medgemma 1 5") == a          # same (type, norm)
        b = st.add_entity("product", "MedGemma 1.5", "medgemma 1 5")                # another type: another row
        assert b != a
        assert st.add_alias("artifact", "medgemma 1 5", a, "MedGemma 1.5") is True
        assert st.add_alias("artifact", "medgemma 1 5", b, "MedGemma 1.5") is False  # first one wins
        assert st.entity_by_alias("artifact", "medgemma 1 5")["id"] == a
        assert st.entity_by_alias("technique", "medgemma 1 5") is None
        assert [r["id"] for r in st.entities_of_types(["model", "product"])] == [a, b]
        assert st.get_entity(a)["category"] == "C04"


def test_mentions_count_once_per_item_promote_roles_and_mark_items_dirty(tmp_path):
    st, run = _store_with(tmp_path, {1: "main", 2: "main"})
    e = st.add_entity("technique", "large language model", "large language model")
    st.mark_graph_synced(["pmid:1", "pmid:2"])
    assert st.add_mention("pmid:1", e, "mentioned", "2026-11-08T10:01:00+00:00") is True
    assert st.add_mention("pmid:1", e, "main", "2026-11-08T10:01:00+00:00") is False   # same item: promoted
    assert st.add_mention("pmid:1", e, "used", "2026-11-08T10:01:00+00:00") is False   # never demoted
    st.add_mention("pmid:2", e, "used", "2026-11-08T10:02:00+00:00")
    row = st.get_entity(e)
    assert (row["mention_count"], row["first_seen"], row["last_seen"]) == (
        2, "2026-11-08T10:01:00+00:00", "2026-11-08T10:02:00+00:00")
    roles = dict(st.conn.execute("SELECT item_id, role FROM entity_mentions").fetchall())
    assert roles == {"pmid:1": "main", "pmid:2": "used"}
    assert st.graph_dirty_items() == ["pmid:1", "pmid:2"]
    st.close()


def test_relations_merges_and_entity_embeddings(tmp_path):
    st, run = _store_with(tmp_path, {1: "main"})
    m = st.add_entity("model", "MedGemma 1.5", "medgemma 1 5")
    o = st.add_entity("organization", "Google", "google")
    assert st.add_relation(m, "developed_by", o, "pmid:1") is True
    assert st.add_relation(m, "developed_by", o, "pmid:1") is False
    assert st.relations_of_item("pmid:1") == [(m, "developed_by", o)]
    st.record_merge(o, "Google LLC", "judge", score=0.91, item_id="pmid:1")
    merge = st.conn.execute("SELECT entity_id, name, method, score, item_id FROM entity_merges").fetchone()
    assert tuple(merge) == (o, "Google LLC", "judge", 0.91, "pmid:1")
    st.save_entity_embeddings("hash-4", [(m, np.array([1, 0, 0, 0], dtype=np.float32))])
    vectors = st.load_entity_embeddings("hash-4", [m, o])
    assert set(vectors) == {m} and vectors[m].tolist() == [1.0, 0.0, 0.0, 0.0]
    st.close()


def test_graph_watermark(tmp_path):
    st, run = _store_with(tmp_path, {1: "main", 2: "reject"})
    e = st.add_entity("technique", "federated learning", "federated learning")
    st.add_mention("pmid:1", e, "main", "2026-11-08T10:01:00+00:00")
    st.add_mention("pmid:2", e, "main", "2026-11-08T10:02:00+00:00")   # rejected items never reach the mirror
    assert st.graph_dirty_items() == ["pmid:1"]
    st.mark_graph_synced(["pmid:1"], when="2026-11-08T12:00:00+00:00")
    assert st.graph_dirty_items() == []
    other = st.add_entity("problem", "sepsis early detection", "sepsis early detection")
    st.add_mention("pmid:1", other, "used", "2026-11-08T10:01:00+00:00")
    assert st.graph_dirty_items() == ["pmid:1"]
    st.mark_all_graph_dirty()
    assert st.graph_dirty_items(limit=5) == ["pmid:1"]
    st.close()
