# tests/test_intelligence.py
"""Weekly graph intelligence (SDD §6.9): trends, Louvain communities and gaps, on a synthetic graph."""
from datetime import datetime, timedelta, timezone

import pytest

from sotawhat.graph import intelligence as intel
from sotawhat.items import Item
from sotawhat.store.db import Store

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


def _day(days_ago):
    return (NOW - timedelta(days=days_ago)).isoformat(timespec="seconds")


@pytest.fixture
def g(tmp_path):
    """Two topics that never meet: a scribe cluster (ASR, LLM, documentation burden) and an imaging cluster
    (diffusion, segmentation, missed fractures); a new technique this week (agentic RAG); one rejected item."""
    st = Store(tmp_path / "insight.db")
    run = st.start_run("daily")
    plan = {  # item: (days ago, decision, [(name, type)])
        1: (2, "main", [("speech recognition", "technique"), ("large language model", "technique"), ("documentation burden", "problem")]),
        2: (3, "main", [("speech recognition", "technique"), ("documentation burden", "problem")]),
        3: (4, "main", [("large language model", "technique"), ("documentation burden", "problem")]),
        4: (20, "main", [("large language model", "technique"), ("documentation burden", "problem")]),
        5: (5, "main", [("diffusion model", "technique"), ("segmentation", "technique"), ("missed fracture", "problem")]),
        6: (25, "main", [("diffusion model", "technique"), ("missed fracture", "problem")]),
        7: (30, "main", [("segmentation", "technique"), ("missed fracture", "problem"), ("diffusion model", "technique")]),
        8: (1, "frontier", [("agentic RAG", "technique"), ("large language model", "technique")]),
        9: (1, "main", [("agentic RAG", "technique"), ("speech recognition", "technique")]),
        10: (1, "reject", [("agentic RAG", "technique"), ("missed fracture", "problem")]),
    }
    st.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"P{n}", url="u", text="t",
                          pmid=str(n)) for n in plan], run)
    ids = {}
    for n, (ago, decision, ents) in plan.items():
        st.conn.execute("UPDATE items SET fetched_at = ? WHERE id = ?", (_day(ago), f"pmid:{n}"))
        st.record_triage(f"pmid:{n}", run, decision)
        for name, type_ in ents:
            ids[name] = st.add_entity(type_, name, name.lower())
            st.add_mention(f"pmid:{n}", ids[name], "main", _day(ago))
    st.conn.commit()
    yield st, ids
    st.close()


def test_trends_rank_rising_and_new_entities(g):
    st, ids = g
    rising = intel.trends(st, now=NOW, min_recent=2)
    names = [t["name"] for t in rising]
    assert names[0] in ("speech recognition", "agentic RAG") and "agentic RAG" in names
    rag = next(t for t in rising if t["name"] == "agentic RAG")
    assert (rag["recent"], rag["baseline"], rag["new"]) == (2, 0, True)                 # the rejected item never counts
    llm = next(t for t in rising if t["name"] == "large language model")
    assert (llm["recent"], llm["baseline"]) == (3, 1) and llm["z"] < rag["z"] + 2
    assert "diffusion model" not in names                                               # 1 recent mention only


def test_communities_split_the_two_topics(g):
    st, ids = g
    groups = intel.communities(st, now=NOW, min_size=2)
    member_sets = [set(c["members"]) for c in groups]
    assert {ids["diffusion model"], ids["segmentation"], ids["missed fracture"]} in member_sets
    scribe = next(c for c in groups if ids["documentation burden"] in c["members"])
    assert ids["speech recognition"] in scribe["members"] and ids["diffusion model"] not in scribe["members"]
    assert [c["community"] for c in groups] == list(range(len(groups))) and groups[0]["importance"] >= groups[-1]["importance"]
    assert intel.communities(st, now=NOW - timedelta(days=400)) == []                   # empty window, no crash


def test_gaps_offer_why_now_pairs_bridges_and_serendipity(g):
    st, ids = g
    found = intel.gaps(st, now=NOW, recent_days=2, limit=10)
    recent = found["recent_technique"]
    assert recent and all(c["technique"] == "agentic RAG" for c in recent)
    assert {c["problem"] for c in recent} == {"documentation burden", "missed fracture"}  # never linked (reject ignored)
    assert "2026-11-07" in recent[0]["why_now"]
    bridges = found["community_bridge"]
    assert any(c["technique"] in ("diffusion model", "segmentation") and c["problem"] == "documentation burden"
               or c["problem"] == "missed fracture" and c["technique"] in ("speech recognition", "large language model")
               for c in bridges)
    assert all(c["sampler"] == "serendipity" for c in found["serendipity"])
