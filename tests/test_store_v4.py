# tests/test_store_v4.py
"""Schema 4 (P4): idea ledger, communities and weekly reports (SDD §8.3 stage 8, §6.9)."""
import numpy as np

from sotawhat.store.db import Store


def test_schema_4_tables_and_version(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        names = {r[0] for r in st.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"ideas", "communities", "entity_communities", "weekly_reports"} <= names
        assert st.meta_get("schema_version") == "6"


def test_idea_ledger_versions_status_and_votes(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("weekly")
        first = st.add_idea(run, "Escriba de alta para o PS", card={"problema": "alta lenta"}, lens="jtbd", persona="enfermeira",
                            niche="A06|C01|produto", candidate={"technique": "ASR"}, embedding=np.ones(4, dtype=np.float32))
        st.update_idea(first, score=7.4, scores={"valor": 8}, critique=[{"papel": "clinico"}], novelty={"problema": "parcial"},
                       selected=True)
        row = st.get_idea(first)
        assert (row["status"], row["version"], row["selected"], row["score"]) == ("nova", 1, 1, 7.4)
        assert st.idea_embedding(first).tolist() == [1.0, 1.0, 1.0, 1.0]
        child = st.add_idea(run, "Escriba de alta v2", card={}, parent_id=first)
        assert st.get_idea(child)["version"] == 2
        assert st.vote_idea(first, "up", "telegram") == "curtida"
        assert st.vote_idea(first, "archive", "web", note="não agora") == "engavetada"
        assert st.get_idea(first)["status"] == "engavetada"
        assert [r["id"] for r in st.list_ideas(selected=True)] == [first]
        assert [r["id"] for r in st.list_ideas(status="nova")] == [child]
        votes = st.conn.execute("SELECT target_type, target_id, value, note FROM feedback ORDER BY id").fetchall()
        assert [tuple(v) for v in votes] == [("idea", str(first), "up", None), ("idea", str(first), "archive", "não agora")]


def test_communities_and_weekly_report(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("weekly")
        st.save_communities(run, {10: 0, 11: 0, 12: 1}, {0: ("IA generativa clínica", "resumo 0", 2, 10),
                                                        1: ("Imagem", "resumo 1", 1, 12)})
        assert st.entity_community(11) == 0 and st.entity_community(99) is None
        assert [tuple(r)[:3] for r in st.latest_communities()] == [(run, 0, "IA generativa clínica"), (run, 1, "Imagem")]
        st.save_weekly_report(run, "2026-11-08", {"ideas": [1, 2]})
        assert st.latest_weekly_report()["payload"] == {"ideas": [1, 2]}
        on_demand = st.start_run("ideate")
        st.save_weekly_report(on_demand, "2026-11-09", {"ideas": [3]})
        assert st.latest_weekly_report()["run_id"] == on_demand
        assert st.latest_weekly_report(kind="weekly")["run_id"] == run and st.latest_weekly_report(kind="daily") is None
