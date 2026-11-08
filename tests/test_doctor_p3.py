# tests/test_doctor_p3.py
"""`sotawhat doctor` checks added in P3: the Neo4j mirror, the graph backlog and the interface."""
from sotawhat.config import Settings
from sotawhat.doctor import TASKS, check_graph, check_neo4j, check_web, model_requirements
from sotawhat.items import Item
from sotawhat.store.db import Store


class Mirror:
    def __init__(self, alive=True):
        self.alive, self.closed = alive, False

    def ping(self):
        return self.alive

    def counts(self):
        return {"nodes": 120, "relationships": 340}

    def close(self):
        self.closed = True


def test_check_neo4j(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        off = check_neo4j(Settings(_env_file=None), st)
        assert off.status == "warn" and "desligado" in off.detail and "interface funciona" in off.detail
        settings = Settings(_env_file=None, neo4j_password="x")
        mirror = Mirror()
        st.meta_set("graph_synced_at", "2026-11-08T10:00:00+00:00")
        ok = check_neo4j(settings, st, factory=lambda s: mirror)
        assert ok.status == "ok" and "120 nós" in ok.detail and "340 relações" in ok.detail and mirror.closed
        down = check_neo4j(settings, st, factory=lambda s: Mirror(alive=False))
        assert down.status == "fail" and "sotawhat graph up" in down.detail


def test_check_graph(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        assert check_graph(st).status == "warn" and "sotawhat graph extract" in check_graph(st).detail
        run = st.start_run("daily")
        st.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"P{n}",
                              url="u", text="t", pmid=str(n)) for n in range(60)], run)
        for n in range(60):
            st.record_triage(f"pmid:{n}", run, "main")
        st.add_mention("pmid:0", st.add_entity("model", "MedGemma 1.5", "medgemma 1 5"), "main", "2026-11-08")
        backlog = check_graph(st)
        assert backlog.status == "warn" and "60 aprovados sem extração" in backlog.detail and "1 entidades" in backlog.detail
        for n in range(60):
            st.record_extraction(f"pmid:{n}", run, "ok", payload={})
        assert check_graph(st).status == "ok"


def test_check_web():
    class Socket:
        def close(self):
            pass

    def refuse(address, timeout=None):
        raise OSError("refused")

    up = check_web(8765, connect=lambda address, timeout=None: Socket())
    assert up.status == "ok" and "http://127.0.0.1:8765" in up.detail
    down = check_web(8765, connect=refuse)
    assert down.status == "warn" and "sotawhat serve" in down.detail


def test_resolve_task_models_are_checked():
    assert "resolve" in TASKS
    assert "z-ai/glm-5.3-flash" in model_requirements()
