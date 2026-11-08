# tests/test_mcp.py
"""MCP server `sotawhat-graph` (SDD §6.11, US5): tools over SQLite and read-only Cypher on the mirror."""
import asyncio

import pytest

from sotawhat import mcp_server as m
from sotawhat.cli import parse_args
from sotawhat.graph.neo4j_sync import Neo4jMirror
from sotawhat.items import Item
from sotawhat.store.db import Store


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "insight.db"
    with Store(path) as st:
        run = st.start_run("daily")
        st.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=title,
                              url=f"https://example.org/{n}", text="t", pmid=str(n))
                         for n, title in ((1, "MedGemma reads CT"), (2, "Ambient scribe RCT"))], run)
        st.record_triage("pmid:1", run, "main", total=4.2, summary_pt="Modelo aberto para TC.")
        st.record_triage("pmid:2", run, "frontier", total=3.9, summary_pt="Ensaio com escriba ambiente.")
        med = st.add_entity("model", "MedGemma 1.5", "medgemma 1 5")
        google = st.add_entity("organization", "Google", "google")
        st.add_alias("artifact", "medgemma", med, "MedGemma")
        st.add_mention("pmid:1", med, "main", "2026-11-08T10:00:00+00:00")
        st.add_mention("pmid:1", google, "mentioned", "2026-11-08T10:00:00+00:00")
    return path


class Record:
    def __init__(self, data):
        self._data = data

    def data(self):
        return self._data


class FakeDriver:
    def __init__(self, rows=3):
        self.rows, self.calls = rows, []

    def execute_query(self, query, parameters_=None, database_=None, routing_=None, **kwargs):
        self.calls.append((query, routing_))
        return [Record({"name": f"n{i}"}) for i in range(self.rows)], None, None

    def verify_connectivity(self):
        return None

    def close(self):
        pass


def test_server_registers_the_tools(db):
    tools = asyncio.run(m.build_server(db).list_tools())
    assert {t.name for t in tools} == {"search", "entity", "neighbors", "recent_items", "graph_stats", "cypher",
                                       "trends", "gaps", "list_ideas", "idea"}
    assert all(t.description for t in tools)


def test_tools_answer_from_sqlite(db):
    assert [e["name"] for e in m.search_tool(db, "medgemma")["entities"]] == ["MedGemma 1.5"]
    for key in ("medgemma 1.5", "MedGemma", "e1", "1"):
        assert m.entity_tool(db, key)["name"] == "MedGemma 1.5", key
    assert "error" in m.entity_tool(db, "nothing like this")
    assert [n["name"] for n in m.neighbors_tool(db, "Google")] == ["MedGemma 1.5"]
    assert [i["id"] for i in m.recent_items_tool(db, days=0, section="main")] == ["pmid:1"]
    assert [i["id"] for i in m.recent_items_tool(db, days=0, section="Fronteira de IA")] == ["pmid:2"]
    assert [i["id"] for i in m.recent_items_tool(db, days=0, topic="MedGemma")] == ["pmid:1"]
    assert [i["id"] for i in m.recent_items_tool(db, days=0, topic="escriba")] == ["pmid:2"]   # free text
    assert m.graph_stats_tool(db)["approved"] == 2


def test_cypher_is_read_only_and_limited(db):
    driver = FakeDriver(rows=5)
    factory = lambda: Neo4jMirror(driver)  # noqa: E731
    for bad in ("CREATE (n)", "MATCH (n) DETACH DELETE n", "MATCH (n) SET n.x = 1", "MERGE (n:X)",
                "LOAD CSV FROM 'file:///x' AS r RETURN r", "CALL dbms.security.listUsers()",
                "call apoc.periodic.iterate('a', 'b', {})", "MATCH (n) REMOVE n.x", "DROP CONSTRAINT x"):
        assert "error" in m.cypher_tool(db, bad, mirror_factory=factory), bad
    assert driver.calls == []
    out = m.cypher_tool(db, "MATCH (e:Entity) RETURN e.name AS name", limit=2, mirror_factory=factory)
    assert out == {"rows": [{"name": "n0"}, {"name": "n1"}], "truncated": True}
    from neo4j import RoutingControl
    assert driver.calls[0][1] == RoutingControl.READ
    assert "NEO4J_PASSWORD" in m.cypher_tool(db, "RETURN 1", mirror_factory=lambda: None)["error"]

    class Down(FakeDriver):
        def verify_connectivity(self):
            raise OSError("refused")

    assert "graph up" in m.cypher_tool(db, "RETURN 1", mirror_factory=lambda: Neo4jMirror(Down()))["error"]


def test_cli_serve_mcp():
    assert parse_args(["serve-mcp"]).command == "serve-mcp"


def test_intelligence_and_idea_tools(db):
    from tests.test_web import _seed_ideas

    first, liked, dropped = _seed_ideas(db)
    found = m.list_ideas_tool(db)
    assert [i["id"] for i in found["ideas"]] == [liked, first] and found["counts"] == {"nova": 1, "curtida": 1}
    short = found["ideas"][1]
    assert short["problem"] == "Altas atrasam 2 h." and short["novelty_facets"] == {"problema": "nao_encontrado"}
    assert short["pilot_90d"] == "1 unidade" and "critiques" not in short and "draft" not in short
    assert [i["id"] for i in m.list_ideas_tool(db, status="descartada", finalists_only=False)["ideas"]] == [dropped]
    assert "error" in m.list_ideas_tool(db, status="talvez")
    assert m.idea_tool(db, f"idea:{first}")["context"] and m.idea_tool(db, str(first))["id"] == first
    assert "error" in m.idea_tool(db, "abc") and "error" in m.idea_tool(db, "999")
    trends = m.trends_tool(db)
    assert set(trends) == {"trends", "communities", "last_weekly_report"} and trends["last_weekly_report"] is None
    assert set(m.gaps_tool(db, limit=5)) == {"recent_technique", "community_bridge", "serendipity"}
