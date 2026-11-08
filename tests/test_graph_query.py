# tests/test_graph_query.py
"""Graph queries for the interface and the MCP server (SDD §6.11): windows, filters, details, search."""
import csv
import json
from datetime import datetime, timezone

import pytest

from sotawhat.graph import query as q
from sotawhat.items import Item
from sotawhat.store.db import Store

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
ITEMS = {   # n: (decision, fetched_at, title, summary)
    1: ("main", "2026-11-07T09:00:00+00:00", "MedGemma reads CT volumes", "Resumo sobre o MedGemma em TC."),
    2: ("frontier", "2026-11-05T09:00:00+00:00", "Open diffusion language model", "Modelo de difusão aberto."),
    3: ("radar", "2026-10-19T09:00:00+00:00", "Old radiology news", "Notícia antiga de radiologia."),
    4: ("reject", "2026-11-07T10:00:00+00:00", "Rejected diffusion item", "Nada."),
}


@pytest.fixture
def g(tmp_path):
    st = Store(tmp_path / "insight.db")
    run = st.start_run("daily")
    st.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=t,
                          url=f"https://example.org/{n}", text="text", pmid=str(n), profile="medico")
                     for n, (_, _, t, _) in ITEMS.items()], run)
    for n, (decision, fetched, _, summary) in ITEMS.items():
        st.conn.execute("UPDATE items SET fetched_at = ? WHERE id = ?", (fetched, f"pmid:{n}"))
        st.record_triage(f"pmid:{n}", run, decision, total=4.0, summary_pt=summary, why_it_matters_pt=f"Por que {n}",
                         scores={"A": 4, "B": 5, "C": 3, "D": 5}, tags={"domains": ["A03"], "evidence_stage": "D1"})
    st.conn.commit()
    ids = {
        "med": st.add_entity("model", "MedGemma 1.5", "medgemma 1 5", category="C04"),
        "google": st.add_entity("organization", "Google", "google"),
        "fract": st.add_entity("problem", "missed fracture", "missed fracture"),
        "diff": st.add_entity("technique", "diffusion model", "diffusion model"),
        "dom": st.add_entity("domain", "radiologia/imagem", "a03", category="A03"),
    }
    st.add_alias("artifact", "medgemma", ids["med"], "MedGemma")
    st.add_alias("artifact", "medgemma 1 5", ids["med"], "MedGemma 1.5")
    for n, key, role in [(1, "med", "main"), (3, "med", "mentioned"), (1, "google", "mentioned"), (2, "google", "used"),
                         (1, "fract", "used"), (2, "diff", "main"), (4, "diff", "main"), (1, "dom", "tag"),
                         (3, "dom", "tag")]:
        st.add_mention(f"pmid:{n}", ids[key], role, ITEMS[n][1])
    st.add_relation(ids["med"], "developed_by", ids["google"], "pmid:1")
    st.add_relation(ids["med"], "addresses", ids["fract"], "pmid:1")
    st.record_extraction("pmid:1", run, "ok", payload={
        "entities": [], "relations": [], "maturity": "research", "data_modalities": ["imaging"],
        "claims": [{"text_pt": "Acurácia de 78% no RadQA.", "metric": "accuracy", "value": "78%"}]})
    st.add_feedback("item", "pmid:1", "up", "telegram")
    yield st, ids
    st.close()


def _labels(view):
    return {n["label"]: n["count"] for n in view["nodes"]}


def _pairs(view):
    by_id = {n["id"]: n["label"] for n in view["nodes"]}
    return {(by_id[e["source"]], by_id[e["target"]]): (e["kind"], e["weight"]) for e in view["edges"]}


def test_graph_view_window_types_and_edges(g):
    st, ids = g
    week = q.graph_view(st, days=7, now=NOW)
    assert _labels(week) == {"MedGemma 1.5": 1, "Google": 2, "missed fracture": 1, "diffusion model": 1}
    assert _pairs(week) == {("MedGemma 1.5", "Google"): ("developed_by", 1),
                            ("MedGemma 1.5", "missed fracture"): ("addresses", 1),
                            ("Google", "missed fracture"): ("co", 1), ("Google", "diffusion model"): ("co", 1)}
    edge = next(e for e in week["edges"] if e["kind"] == "developed_by")
    assert edge["label"] == "desenvolvido por" and edge["directed"] is True
    node = next(n for n in week["nodes"] if n["label"] == "MedGemma 1.5")
    assert (node["type_label"], node["category"], node["category_label"], node["mentions"]) == (
        "modelo", "C04", "modelos de fundação multimodais", 2)
    assert _labels(q.graph_view(st, days=30, now=NOW))["MedGemma 1.5"] == 2
    assert _labels(q.graph_view(st, days=None, now=NOW))["diffusion model"] == 1   # the rejected item never counts


def test_graph_view_filters_limit_categories_and_focus(g):
    st, ids = g
    assert _labels(q.graph_view(st, days=30, types=["organization"], now=NOW)) == {"Google": 2}
    assert _labels(q.graph_view(st, days=30, min_mentions=2, now=NOW)) == {"MedGemma 1.5": 2, "Google": 2}
    top = q.graph_view(st, days=30, limit=1, now=NOW)
    assert len(top["nodes"]) == 1 and top["truncated"] is True
    with_categories = q.graph_view(st, days=30, types=list(q.ENTITY_TYPES) + ["domain"], now=NOW)
    assert _labels(with_categories)["radiologia/imagem"] == 2
    focus = q.graph_view(st, days=30, focus=ids["diff"], now=NOW)
    assert _labels(focus) == {"diffusion model": 1, "Google": 2}           # counts stay the window's counts
    assert focus["focus"] == f"e{ids['diff']}"


def test_entity_detail(g):
    st, ids = g
    d = q.entity_detail(st, ids["med"])
    assert (d["name"], d["type_label"], d["category_label"], d["mention_count"]) == (
        "MedGemma 1.5", "modelo", "modelos de fundação multimodais", 2)
    assert d["aliases"] == ["MedGemma"]
    assert [(i["id"], i["section"], i["vote"]) for i in d["items"]] == [("pmid:1", "IA ∩ Saúde", "up"),
                                                                       ("pmid:3", "Radar", None)]
    assert d["items"][0]["summary_pt"] == "Resumo sobre o MedGemma em TC." and d["items"][0]["role"] == "main"
    assert {(n["name"], n["shared"]) for n in d["neighbors"]} >= {("Google", 1), ("missed fracture", 1)}
    assert {(r["direction"], r["label"], r["other"]["name"]) for r in d["relations"]} == {
        ("out", "desenvolvido por", "Google"), ("out", "aborda", "missed fracture")}
    assert d["claims"] == [{"text_pt": "Acurácia de 78% no RadQA.", "metric": "accuracy", "value": "78%",
                            "item_id": "pmid:1"}]
    google = q.entity_detail(st, ids["google"])
    assert {(r["direction"], r["relation"]) for r in google["relations"]} == {("in", "developed_by")}
    assert q.entity_detail(st, 9999) is None


def test_item_detail(g):
    st, ids = g
    d = q.item_detail(st, "pmid:1")
    assert (d["title"], d["section"], d["vote"], d["why_it_matters_pt"]) == (
        "MedGemma reads CT volumes", "IA ∩ Saúde", "up", "Por que 1")
    assert d["tags"]["domains"] == [{"key": "A03", "label": "radiologia/imagem"}]
    assert d["tags"]["evidence_stage"] == {"key": "D1", "label": "pesquisa de fronteira"}
    assert [(e["name"], e["role"]) for e in d["entities"]][:3] == [("MedGemma 1.5", "main"), ("missed fracture", "used"),
                                                                    ("Google", "mentioned")]
    assert d["extraction"]["maturity"] == "research" and d["extraction"]["claims"][0]["value"] == "78%"
    assert q.item_detail(st, "pmid:2")["extraction"] is None and q.item_detail(st, "nope") is None


def test_search_recent_and_neighbors(g):
    st, ids = g
    assert [e["name"] for e in q.search(st, "medgemma")["entities"]] == ["MedGemma 1.5"]
    assert [i["id"] for i in q.search(st, "RESUMO")["items"]] == ["pmid:1"]
    assert [i["id"] for i in q.search(st, "radiology")["items"]] == ["pmid:3"]
    assert [i["id"] for i in q.search(st, "rejected")["items"]] == []          # only approved items
    assert q.search(st, "m") == {"entities": [], "items": []}
    assert [i["id"] for i in q.recent_items(st, days=7, now=NOW)] == ["pmid:1", "pmid:2"]
    assert [i["id"] for i in q.recent_items(st, days=30, section="radar", now=NOW)] == ["pmid:3"]
    assert [i["id"] for i in q.recent_items(st, days=30, entity_id=ids["diff"], now=NOW)] == ["pmid:2"]
    assert [n["name"] for n in q.neighbors(st, ids["google"])][:1] in (["MedGemma 1.5"], ["missed fracture"],
                                                                        ["diffusion model"])


def test_stats_and_export(g, tmp_path):
    st, ids = g
    s = q.stats(st)
    assert (s["items"], s["approved"], s["extracted"], s["pending_extraction"]) == (4, 3, 1, 2)
    assert s["entities"]["model"] == 1 and s["entities"]["domain"] == 1 and s["relations"] == 2
    json_path, nodes_csv, edges_csv = q.export(st, tmp_path / "exports", day="2026-11-08")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert json_path.name == "graph-2026-11-08.json" and len(data["nodes"]) == 5 and len(data["items"]) == 3
    with nodes_csv.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert {r["label"] for r in rows} >= {"MedGemma 1.5", "radiologia/imagem"} and "type" in rows[0]
    with edges_csv.open(encoding="utf-8") as fh:
        assert {r["kind"] for r in csv.DictReader(fh)} >= {"developed_by", "co"}
