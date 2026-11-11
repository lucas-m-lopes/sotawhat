# tests/test_neo4j_sync.py
"""Neo4j mirror (SDD §6.3, D16) with a fake driver, and `sotawhat graph up` with a fake docker."""
import subprocess

import pytest

from sotawhat.cli import parse_args
from sotawhat.config import Settings
from sotawhat.graph import docker
from sotawhat.graph.neo4j_sync import Neo4jMirror
from sotawhat.items import Item
from sotawhat.store.db import Store


class FakeDriver:
    def __init__(self, nodes_to_delete=7, alive=True):
        self.calls, self.left, self.alive, self.closed = [], nodes_to_delete, alive, False

    def execute_query(self, query, parameters_=None, database_=None, routing_=None, **kwargs):
        text = " ".join(query.split())
        self.calls.append((text, parameters_ or {}, database_))
        if "DETACH DELETE" in text:
            deleted, self.left = min(self.left, 5000), max(self.left - 5000, 0)
            return [{"n": deleted}], None, None
        if "count(" in text:
            return [{"n": 3}], None, None
        return [], None, None

    def verify_connectivity(self):
        if not self.alive:
            raise OSError("connection refused")

    def close(self):
        self.closed = True


def _queries(driver, needle):
    return [(q, p) for q, p, _ in driver.calls if needle in q]


@pytest.fixture
def st(tmp_path):
    store = Store(tmp_path / "insight.db")
    run = store.start_run("daily")
    store.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"Paper {n}",
                             url=f"https://example.org/{n}", text="t", pmid=str(n)) for n in (1, 2, 3)], run)
    for n, decision in ((1, "main"), (2, "frontier"), (3, "reject")):
        store.record_triage(f"pmid:{n}", run, decision, total=4.0, summary_pt=f"Resumo {n}")
    med = store.add_entity("model", "MedGemma 1.5", "medgemma 1 5", category="C04")
    google = store.add_entity("organization", "Google", "google")
    dom = store.add_entity("domain", "radiologia/imagem", "a03", category="A03")
    weird = store.add_entity("weird type", "Odd", "odd")
    for item, entity, role in (("pmid:1", med, "main"), ("pmid:1", google, "mentioned"), ("pmid:1", dom, "tag"),
                               ("pmid:2", med, "used"), ("pmid:2", weird, "main"), ("pmid:3", google, "main")):
        store.add_mention(item, entity, role, "2026-11-08T10:00:00+00:00")
    store.add_relation(med, "developed_by", google, "pmid:1")
    store.add_relation(med, "developed_by", google, "pmid:2")
    store.add_relation(med, "drops_tables", google, "pmid:2")      # unknown predicate: never sent
    yield store
    store.close()


def test_schema_and_sync_send_batches_and_mark_items(st):
    driver = FakeDriver()
    stats = Neo4jMirror(driver, database="neo4j").sync(st)
    assert {q for q, _ in _queries(driver, "CREATE CONSTRAINT")} == {
        "CREATE CONSTRAINT item_id IF NOT EXISTS FOR (i:Item) REQUIRE i.id IS UNIQUE",
        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE"}
    items = _queries(driver, "MERGE (i:Item {id: row.id})")[0][1]["rows"]
    assert sorted(r["id"] for r in items) == ["pmid:1", "pmid:2"]                     # the rejected one stays out
    first = next(r for r in items if r["id"] == "pmid:1")["props"]
    assert (first["section"], first["summary_pt"], first["title"]) == ("IA ∩ Saúde", "Resumo 1", "Paper 1")
    labels = {q.split("SET e += row.props, e:")[1].split()[0] for q, _ in _queries(driver, "MERGE (e:Entity")}
    assert labels == {"Model", "Organization", "Domain"}
    assert not any("weird" in q.lower() or "drops" in q.lower() for q, _, _ in driver.calls)
    mentions = _queries(driver, "MERGE (i)-[m:MENTIONS]->(e)")[0][1]["rows"]
    assert {(m["item"], m["role"]) for m in mentions} >= {("pmid:1", "main"), ("pmid:1", "tag"), ("pmid:2", "used")}
    assert _queries(driver, "-[m:MENTIONS]->() DELETE m")                            # stale mentions cleared first
    rel_query, rel_params = _queries(driver, "MERGE (s)-[r:DEVELOPED_BY]->(o)")[0]
    assert rel_params["rows"] == [{"s": 1, "o": 2, "items": ["pmid:1", "pmid:2"], "weight": 2}]
    assert all(db == "neo4j" for _, _, db in driver.calls)
    assert (stats.items, stats.entities, stats.relations) == (2, 3, 1)
    assert st.graph_dirty_items() == [] and st.meta_get("graph_synced_at")
    again = FakeDriver()
    assert Neo4jMirror(again).sync(st).items == 0 and not _queries(again, "MERGE (i:Item")


def test_rebuild_deletes_in_batches_and_resends_everything(st):
    Neo4jMirror(FakeDriver()).sync(st)
    driver = FakeDriver(nodes_to_delete=7000)
    stats = Neo4jMirror(driver).sync(st, rebuild=True)
    assert len(_queries(driver, "DETACH DELETE")) == 3 and stats.deleted == 7000 and stats.rebuilt
    assert sorted(r["id"] for r in _queries(driver, "MERGE (i:Item")[0][1]["rows"]) == ["pmid:1", "pmid:2"]


def test_from_settings_ping_and_counts():
    assert Neo4jMirror.from_settings(Settings(_env_file=None)) is None
    seen = {}

    def factory(uri, auth=None, **kwargs):
        seen.update(uri=uri, auth=auth)
        return FakeDriver()

    mirror = Neo4jMirror.from_settings(Settings(_env_file=None, neo4j_password="s3cret", neo4j_uri="bolt://localhost:7687"),
                                       driver_factory=factory)
    assert seen == {"uri": "bolt://localhost:7687", "auth": ("neo4j", "s3cret")} and mirror.ping()
    assert mirror.counts() == {"nodes": 3, "relationships": 3}
    assert Neo4jMirror(FakeDriver(alive=False)).ping() is False
    mirror.close()
    assert mirror.driver.closed


class FakeDocker:
    def __init__(self, ready_after=0, compose_rc=0):
        self.calls, self.ready_after, self.compose_rc, self.started = [], ready_after, compose_rc, []

    def run(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if cmd[:2] == ["docker", "info"]:
            self.ready_after -= 1
            return subprocess.CompletedProcess(cmd, 0 if self.ready_after < 0 else 1, "", "")
        return subprocess.CompletedProcess(cmd, self.compose_rc, "", "Error: port is already allocated")

    def popen(self, cmd, **kwargs):
        self.started.append(cmd)


def test_graph_up(tmp_path, monkeypatch):
    exe = tmp_path / "Docker Desktop.exe"
    exe.write_text("")
    monkeypatch.setattr(docker, "DOCKER_DESKTOP", exe)
    settings = Settings(_env_file=None, neo4j_password="s3cret", sotawhat_data_dir=tmp_path / "data")
    ok, message = docker.graph_up(Settings(_env_file=None), tmp_path)
    assert not ok and "NEO4J_PASSWORD" in message
    fake, answers = FakeDocker(ready_after=2), iter([False, True])
    ok, message = docker.graph_up(settings, tmp_path, run=fake.run, popen=fake.popen, sleep=lambda s: None,
                                  connect=lambda: next(answers))
    assert ok and "7474" in message and fake.started == [[str(exe)]]
    compose_cmd, kwargs = next((c, k) for c, k in fake.calls if c[:2] == ["docker", "compose"])
    assert compose_cmd[-3:] == ["up", "-d", "neo4j"] and "--env-file" in compose_cmd
    assert kwargs["env"]["NEO4J_PASSWORD"] == "s3cret" and kwargs["cwd"] == tmp_path
    ok, message = docker.graph_up(settings, tmp_path, run=FakeDocker(compose_rc=1).run, sleep=lambda s: None,
                                  connect=lambda: True)
    assert not ok and "port is already allocated" in message
    ok, message = docker.graph_up(settings, tmp_path, run=FakeDocker().run, sleep=lambda s: None,
                                  connect=lambda: False, wait_neo4j=10, step=5)
    assert not ok and "não respondeu" in message


def test_cli_graph_commands():
    assert parse_args(["graph", "up"]).graph_action == "up"
    ns = parse_args(["graph", "sync", "--rebuild"])
    assert (ns.command, ns.graph_action, ns.rebuild) == ("graph", "sync", True)
    assert parse_args(["graph", "status"]).rebuild is False
    assert parse_args(["graph", "export", "--out", "X"]).out == "X"


def test_a_pending_rebuild_runs_at_the_next_sync(st):
    """`repair entities` deletes entities; a plain sync would leave their nodes in the mirror."""
    Neo4jMirror(FakeDriver()).sync(st)
    st.meta_set("graph_rebuild", "1")
    driver = FakeDriver(nodes_to_delete=10)
    stats = Neo4jMirror(driver).sync(st)
    assert stats.rebuilt and _queries(driver, "DETACH DELETE") and st.meta_get("graph_rebuild") == ""
    assert sorted(r["id"] for r in _queries(driver, "MERGE (i:Item")[0][1]["rows"]) == ["pmid:1", "pmid:2"]
    assert not Neo4jMirror(FakeDriver()).sync(st).rebuilt
