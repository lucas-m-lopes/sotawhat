# tests/test_repair.py
"""`sotawhat repair cjk` (P6): stored triage texts with CJK characters are rewritten, decisions kept."""
import numpy as np

from sotawhat.configfiles import Rubric
from sotawhat.doctor import check_cjk
from sotawhat.items import Item
from sotawhat.llm.gateway import LLMFailure, StructuredResult
from sotawhat.graph.resolve import normalize, split_acronym
from sotawhat.pipeline.repair import cjk_rows, names_v1, repair_cjk, repair_names
from sotawhat.store.db import Store
from tests.test_triage import out


class Gateway:
    def __init__(self, fail_on=()):
        self.calls, self.fail_on = [], set(fail_on)

    def structured_call(self, task, messages, model_cls, models=None):
        self.calls.append(task)
        if len(self.calls) in self.fail_on:
            raise LLMFailure("triage: every model failed")
        return StructuredResult(output=out(summary_pt="Resumo limpo.", why_it_matters_pt="Importa.", reason_pt="Motivo."),
                                model="deepseek/x", provider=None, cost_usd=0.0004, latency_ms=1, attempts=1,
                                first_try_valid=True)


def test_repair_rewrites_only_the_texts(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"T{n}", url="u",
                              text="texto") for n in range(3)], run)
        st.record_triage("pmid:0", run, "main", total=3.9, summary_pt="orientar和质量 improvement", why_it_matters_pt="ok")
        st.record_triage("pmid:1", run, "reject", total=1.0, summary_pt="limpo", reason="de随访")
        st.record_triage("pmid:2", run, "frontier", total=3.6, summary_pt="Resumo sem problema.")
        assert [r["item_id"] for r in cjk_rows(st)] == ["pmid:0", "pmid:1"] and check_cjk(st).status == "warn"
        result = repair_cjk(st, Gateway(), Rubric())
        assert result == {"found": 2, "fixed": 2, "failed": 0, "stopped": None} and check_cjk(st).status == "ok"
        main = st.conn.execute("SELECT * FROM triage WHERE item_id = 'pmid:0'").fetchone()
        assert (main["decision"], main["total"], main["summary_pt"], main["why_it_matters_pt"]) == \
            ("main", 3.9, "Resumo limpo.", "Importa.")
        rejected = st.conn.execute("SELECT * FROM triage WHERE item_id = 'pmid:1'").fetchone()
        assert rejected["decision"] == "reject" and rejected["why_it_matters_pt"] == "" and rejected["reason"] == "Motivo."
        assert rejected["prompt_version"].endswith("+repair")
        st.record_triage("pmid:2", run, "frontier", total=3.6, summary_pt="de随访")
        assert repair_cjk(st, Gateway(fail_on={1}), Rubric())["failed"] == 1


# --- names: what the singular rule before 2026-11-10 cut ------------------------------------------------------
class Embedder:
    name = "fake"

    def __init__(self):
        self.texts = []

    def embed(self, texts):
        self.texts += texts
        return [np.ones(4) for _ in texts]


def _old_graph(st):
    """The graph as the old rule wrote it, the raw names kept in the extractions; plus one entity that the new
    rule wrote since, which the repair must not take over."""
    run = st.start_run("daily")
    raw = {"pmid:1": [("AI bias", "problem"), ("picture archiving and communication system (PACS)", "technique")],
           "pmid:2": [("mixture-of-experts", "technique"), ("Harness-S", "technique")],
           "pmid:3": [("algorithmic bias", "problem")]}
    st.upsert_items([Item(id=i, kind="paper", source="pubmed", source_id=i, title=i, url="u", text="t") for i in raw], run)
    ids = {}
    for item_id, ents in raw.items():
        st.record_triage(item_id, run, "main")
        st.record_extraction(item_id, run, "ok", payload={"entities": [
            {"name": n, "type": t, "category": "none", "role": "main"} for n, t in ents], "relations": []})
        for name, type_ in ents:
            base, acronym = split_acronym(name)
            shown, key = names_v1(base, type_)
            ids[shown] = st.add_entity(type_, shown, key)
            st.add_alias(type_, key, ids[shown], shown)
            if acronym:
                st.add_alias(type_, names_v1(acronym, type_)[1], ids[shown], acronym)
            st.add_mention(item_id, ids[shown], "main", "2026-11-09T10:00:00+00:00")
    later = st.add_entity("problem", "algorithmic bias", "algorithmic bias")
    st.add_alias("problem", "algorithmic bias", later, "algorithmic bias")
    st.mark_graph_synced(list(raw), when="2026-11-09T11:00:00+00:00")
    return ids, later


def test_repair_names_moves_what_the_old_singular_rule_cut(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        ids, later = _old_graph(st)
        assert set(ids) == {"AI bia", "picture archiving and communication system", "mixture-of-expert", "Harness-",
                            "algorithmic bia"}
        entity = lambda eid: tuple(st.conn.execute("SELECT name, norm FROM entities WHERE id = ?", (eid,)).fetchone())  # noqa: E731
        preview = repair_names(st, dry_run=True)
        assert {r["name"] for r in preview["renamed"]} == {("AI bia", "AI bias"), ("Harness-", "Harness-S"),
                                                           ("mixture-of-expert", "mixture-of-experts")}
        assert entity(ids["AI bia"]) == ("AI bia", "ai bia") and st.graph_dirty_items() == []    # nothing written

        emb = Embedder()
        out = repair_names(st, embedder=emb)
        assert entity(ids["AI bia"]) == ("AI bias", "ai bias")
        assert entity(ids["mixture-of-expert"]) == ("mixture-of-experts", "mixture of experts")
        assert entity(ids["Harness-"]) == ("Harness-S", "harness s")
        pacs = ids["picture archiving and communication system"]
        assert entity(pacs) == ("picture archiving and communication system",) * 2               # only its acronym moved
        assert st.entity_by_alias("technique", normalize("PACS", "technique"))["id"] == pacs
        assert st.entity_by_alias("technique", "pac") is None and st.entity_by_alias("problem", "ai bia") is None
        # the next extraction of either form meets the repaired entity
        assert st.entity_by_alias("problem", normalize("AI biases", "problem"))["id"] == ids["AI bia"]
        assert st.entity_by_alias("technique", normalize("Mixture of Experts", "technique"))["id"] == ids["mixture-of-expert"]
        # a key that another entity owns is reported, not merged
        assert out["clashes"] == [("algorithmic bia", "algorithmic bias", later)]
        assert entity(ids["algorithmic bia"]) == ("algorithmic bia", "algorithmic bia")
        assert out["rekeyed"] == 3 and out["items"] == 2 and st.graph_dirty_items() == ["pmid:1", "pmid:2"]
        assert sorted(emb.texts) == ["problem: AI bias", "technique: Harness-S", "technique: mixture-of-experts"]
        assert ids["AI bia"] in st.load_entity_embeddings("fake", [ids["AI bia"]])

        again = repair_names(st, embedder=emb)
        assert again["renamed"] == [] and again["rekeyed"] == 0 and again["clashes"] == out["clashes"]
