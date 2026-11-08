# tests/test_graph_daily.py
"""Graph stage after the daily digest (P3): extraction, categories, Neo4j mirror, its own `graph` run."""
import json

from sotawhat.cli import parse_args
from sotawhat.configfiles import load_config
from sotawhat.graph.neo4j_sync import SyncStats
from sotawhat.graph.resolve import Resolver
from sotawhat.items import Item
from sotawhat.llm.gateway import StructuredResult
from sotawhat.pipeline.daily import render_graph_line, run_graph_stage
from sotawhat.store.db import Store

PAYLOAD = {"entities": [{"name": "MedGemma 1.5", "type": "model", "category": "C04", "role": "main"},
                        {"name": "Google", "type": "organization", "category": "none", "role": "mentioned"}],
           "relations": [{"source": "MedGemma 1.5", "relation": "developed_by", "target": "Google"}],
           "claims": [], "maturity": "research", "data_modalities": ["imaging"]}


class Gateway:
    def __init__(self):
        self.run_id, self.budget_day, self.runs_seen = None, None, []

    def structured_call(self, task, messages, output_model, models=None):
        self.runs_seen.append(self.run_id)
        return StructuredResult(output=output_model.model_validate(PAYLOAD), model="fake/x", provider=None,
                                cost_usd=0.001, latency_ms=1, attempts=1, first_try_valid=True)


class Mirror:
    def __init__(self, alive=True, boom=False):
        self.alive, self.boom, self.synced = alive, boom, 0

    def ping(self):
        return self.alive

    def sync(self, store):
        if self.boom:
            raise RuntimeError("bolt connection reset")
        self.synced += 1
        return SyncStats(items=len(store.graph_dirty_items()))


def _store(tmp_path):
    st = Store(tmp_path / "insight.db")
    run = st.start_run("daily")
    st.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"Paper {n}",
                          url=f"https://example.org/{n}", text="t", pmid=str(n)) for n in (1, 2, 3)], run)
    for n, decision in ((1, "main"), (2, "frontier"), (3, "reject")):
        st.record_triage(f"pmid:{n}", run, decision, tags={"domains": ["A03"], "techniques": ["C04"]})
    st.finish_run(run, ok=True, stats={})
    return st


def test_graph_stage_extracts_links_categories_and_syncs(tmp_path):
    st = _store(tmp_path)
    gateway, mirror = Gateway(), Mirror()
    report = run_graph_stage(st, gateway, Resolver(st), mirror)
    assert report.ok and report.extraction.extracted == 2 and report.categories == 0   # tags linked during resolve
    assert mirror.synced == 1 and report.mirror.items == 2 and report.mirror_note is None
    assert set(gateway.runs_seen) == {report.run_id}
    run = st.conn.execute("SELECT kind, ok, stats_json, cost_usd FROM runs WHERE id = ?", (report.run_id,)).fetchone()
    stats = json.loads(run["stats_json"])
    assert (run["kind"], run["ok"]) == ("graph", 1) and stats["extraction"]["extracted"] == 2
    assert stats["mirror"]["items"] == 2 and st.last_run("daily")["kind"] == "daily"
    names = {r[0] for r in st.conn.execute("SELECT name FROM entities")}
    assert {"MedGemma 1.5", "Google", "radiologia/imagem"} <= names


def test_categories_are_linked_even_without_the_llm(tmp_path):
    st = _store(tmp_path)
    report = run_graph_stage(st, None, Resolver(st), None)
    assert report.ok and report.extraction.deferred == 2 and report.categories == 4      # 2 items × (A03, C04)
    assert report.mirror_note.startswith("espelho Neo4j desligado")


def test_mirror_down_or_failing_is_a_note_not_a_failure(tmp_path):
    st = _store(tmp_path)
    down = run_graph_stage(st, Gateway(), Resolver(st), Mirror(alive=False))
    assert down.ok and "fora do ar" in down.mirror_note
    failing = run_graph_stage(st, Gateway(), Resolver(st), Mirror(boom=True))
    assert failing.ok and "bolt connection reset" in failing.mirror_note


def test_an_unexpected_error_closes_the_graph_run_as_failed(tmp_path):
    st = _store(tmp_path)

    class Broken(Resolver):
        def link_categories(self, item_id, tags, seen):
            raise RuntimeError("disk I/O error")

    report = run_graph_stage(st, None, Broken(st), None)
    assert not report.ok and "disk I/O error" in report.error
    row = st.conn.execute("SELECT ok, error FROM runs WHERE id = ?", (report.run_id,)).fetchone()
    assert row["ok"] == 0 and "disk I/O error" in row["error"]


def test_render_graph_line_and_cli(tmp_path):
    st = _store(tmp_path)
    line = render_graph_line(run_graph_stage(st, Gateway(), Resolver(st), Mirror()))
    assert line.startswith("grafo: 2 itens extraídos") and "Neo4j sincronizado" in line and "US$" in line
    assert "espelho Neo4j desligado" in render_graph_line(run_graph_stage(st, None, Resolver(st), None))
    assert parse_args(["graph", "extract", "--limit", "5"]).limit == 5


def test_repository_config_includes_the_aliases():
    assert "large language model" in load_config("config").aliases["technique"]
