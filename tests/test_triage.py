# tests/test_triage.py
import re
import threading
from datetime import datetime, timezone

import numpy as np

from sotawhat.configfiles import Mutes, Rubric
from sotawhat.items import Item
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure, StructuredResult
from sotawhat.llm.schemas import TriageOutput
from sotawhat.pipeline.triage import decide, item_message, run_triage, system_prompt
from sotawhat.store.db import Store
from sotawhat.store.vectors import HashEmbedder

NOW = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)
RUBRIC = Rubric(concurrency=3)


def out(**kw):
    base = dict(summary_pt="Resumo.", hard_exclusion="none", inclusion_rules=[4], frontier_ai=3,
                medical_applicability=3, actionability=3, domains=["A03"], problem_types=["B02"],
                techniques=["C05"], evidence_stage="D1", stakeholders=["medico"], br_applicability="F1",
                cfm_risk="medio", substance=2, audience=["clinico"], vendor_only=False, reason_pt="Motivo.",
                why_it_matters_pt="Importa para o hospital.")
    base.update(kw)
    return TriageOutput(**base)


class FakeGateway:
    """Answers by the first word of the title; raises for 'fail' and 'budget' titles."""

    def __init__(self, answers, budget_day=None):
        self.answers = answers
        self.budget_day = budget_day
        self.calls = []
        self._lock = threading.Lock()

    def structured_call(self, task, messages, output_model, models=None):
        title = re.search(r"^title: (.*)$", messages[1]["content"], re.M).group(1)
        with self._lock:
            self.calls.append(title)
        key = title.split()[0].lower()
        if key == "fail":
            raise LLMFailure("triage: every model failed")
        if key == "budget":
            raise BudgetExceeded("daily LLM budget of US$ 1.00 reached")
        return StructuredResult(output=self.answers.get(key, out()), model="deepseek/deepseek-v4.1-flash-1017",
                                provider="DeepInfra", cost_usd=0.0005, latency_ms=10, attempts=1,
                                first_try_valid=True)


def _item(n, title, profile="medico", source="pubmed", text=None):
    return Item(id=f"pmid:{n}", kind="paper", source=source, source_id=str(n), title=title,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", authors=["Ana", "Bia", "Caio", "Davi"],
                published_at="2026-11-07", text=text if text is not None else f"{title} abstract text",
                profile=profile)


def _store(tmp_path, items):
    st = Store(tmp_path / "insight.db")
    run = st.start_run("daily")
    st.upsert_items(items, run)
    return st, run


def test_decide_follows_the_rubric():
    assert decide(out(frontier_ai=4, medical_applicability=5, actionability=3), 4, RUBRIC, "pubmed") == ("main", 4.15)
    assert decide(out(frontier_ai=5, medical_applicability=0, hard_exclusion="generic_ai_no_bridge"), 5,
                  RUBRIC, "rss:x")[0] == "radar"
    assert decide(out(frontier_ai=3, medical_applicability=0, hard_exclusion="generic_ai_no_bridge"), 5,
                  RUBRIC, "rss:x")[0] == "reject"
    assert decide(out(frontier_ai=0, medical_applicability=5, hard_exclusion="clinical_without_ai"), 5,
                  RUBRIC, "pubmed")[0] == "reject"
    # B below min_b never reaches "main", whatever the total
    assert decide(out(frontier_ai=5, medical_applicability=1, actionability=5), 5,
                  Rubric(radar_min_a=6, frontier_min_a=6), "x") == ("reject", 3.6)
    weak = Rubric(weak_sources=("rss:*",))
    assert decide(out(vendor_only=True), 5, weak, "rss:vendor")[1] == round(3 * 0.9 + 0.5 - 1.0, 2)


def test_decide_sends_strong_frontier_ai_to_its_own_section():
    # frontier total = 0.6·A + 0.25·C + 0.15·D − penalties; needs A ≥ 4, substance ≥ 2 and total ≥ 3.6
    assert decide(out(frontier_ai=5, medical_applicability=1, actionability=4), 5, RUBRIC, "arxiv") == ("frontier", 4.75)
    assert decide(out(frontier_ai=4, medical_applicability=0, actionability=2), 5, RUBRIC, "hf_papers") == (
        "frontier", 3.65)
    # too little substance or a weak frontier total: the radar (no health link) or nothing (weak health link)
    assert decide(out(frontier_ai=5, medical_applicability=0, actionability=4, substance=1), 5, RUBRIC, "x")[0] == "radar"
    assert decide(out(frontier_ai=4, medical_applicability=0, actionability=0), 2, RUBRIC, "x") == ("radar", 2.7)
    assert decide(out(frontier_ai=4, medical_applicability=2, actionability=0), 0, RUBRIC, "x")[0] == "reject"
    # health first: an item that qualifies for both sections goes to "IA ∩ Saúde"
    assert decide(out(frontier_ai=5, medical_applicability=3, actionability=4), 5, RUBRIC, "x")[0] == "main"
    # AI news without substance (generic_ai_no_bridge) never reaches the frontier section
    assert decide(out(frontier_ai=5, medical_applicability=0, actionability=5, hard_exclusion="generic_ai_no_bridge"),
                  5, RUBRIC, "x")[0] == "radar"
    # penalties apply to the frontier total too
    assert decide(out(frontier_ai=4, medical_applicability=0, actionability=2, vendor_only=True), 5, RUBRIC, "x") == (
        "radar", 3.15)


def test_prompt_is_fully_rendered_and_item_message_is_bounded():
    prompt = system_prompt()
    assert "{{" not in prompt and "A03 radiologia/imagem" in prompt and "C19 modelos pequenos" in prompt
    msg = item_message(_item(1, "T", text="x" * 9000), max_chars=100)
    assert msg.split("<<<")[1].count("x") == 100 and "Ana, Bia, Caio et al." in msg and "pubmed.ncbi.nlm.nih.gov" in msg
    assert "(sem texto: só o título)" in item_message(_item(2, "T", text=""))


def test_run_triage_end_to_end(tmp_path):
    items = [_item(1, "Radiology foundation model validated in 12 hospitals"),
             _item(2, "Radiology foundation model validated in 12 hospitals.", source="crossref", text="short"),
             _item(3, "Frontier video model with long context", profile="geral", source="arxiv"),
             _item(4, "Asthma antibody phase III trial"),
             _item(5, "Webinar: AI in healthcare", source="rss:vendor"),
             _item(6, "Patient case report with identifiable data")]
    answers = {"radiology": out(frontier_ai=4, medical_applicability=5, actionability=3),
               "frontier": out(frontier_ai=5, medical_applicability=1, actionability=4),
               "asthma": out(frontier_ai=0, medical_applicability=1, hard_exclusion="clinical_without_ai"),
               "patient": out(hard_exclusion="identifiable_patient_data")}
    st, run = _store(tmp_path, items)
    gw = FakeGateway(answers)
    stats = run_triage(st, run, gw, RUBRIC, Mutes(title_terms=("webinar",)), HashEmbedder(64), now=NOW)
    assert (stats.candidates, stats.muted, stats.duplicates, stats.triaged) == (6, 1, 1, 4)
    assert (stats.main, stats.frontier, stats.radar, stats.rejected, stats.errors) == (1, 1, 0, 2, 0)
    assert abs(stats.cost_usd - 0.002) < 1e-9
    rows = {r["item_id"]: r for r in st.conn.execute("SELECT * FROM triage")}
    assert rows["pmid:5"]["decision"] == "muted" and "webinar" in rows["pmid:5"]["reason"]
    assert rows["pmid:2"]["decision"] == "duplicate" and st.cluster_sources("pmid:1") == ["crossref", "pubmed"]
    main = rows["pmid:1"]
    assert main["decision"] == "main" and main["prompt_version"] == "triage_v2" and main["model"].startswith("deepseek")
    assert main["why_it_matters_pt"] == "Importa para o hospital." and '"A03"' in main["tags_json"]
    assert rows["pmid:3"]["decision"] == "frontier" and '"S": 2' in rows["pmid:3"]["scores_json"]
    assert rows["pmid:4"]["why_it_matters_pt"] == ""            # excluded items carry no "why it matters"
    assert st.get_items(["pmid:6"])[0]["text"] is None            # patient data is not kept
    assert len(gw.calls) == 4 and st.embedded_ids("hash-64", ["pmid:1", "pmid:3"]) == {"pmid:1", "pmid:3"}
    assert run_triage(st, run, gw, RUBRIC, Mutes(), HashEmbedder(64), now=NOW).candidates == 0   # idempotent
    st.close()


def test_budget_cap_defers_items_to_the_next_run(tmp_path):
    st, run = _store(tmp_path, [_item(n, f"Paper number {n} on sepsis prediction") for n in range(1, 6)])
    for _ in range(3):
        st.record_llm_call(task="triage", requested_model="m", status="ok", cost_usd=0.10)   # avg US$ 0.10/item
    gw = FakeGateway({}, budget_day=1.0)       # 0.8 * 1.00 - 0.30 spent = 0.50 -> 5 items fit
    st.record_llm_call(task="other", requested_model="m", status="ok", cost_usd=0.30)   # now 0.20 -> 2 items
    stats = run_triage(st, run, gw, RUBRIC, Mutes(), None, now=datetime.now(timezone.utc))
    assert (stats.triaged, stats.deferred) == (2, 3) and "orçamento" in stats.stopped
    assert len(st.triage_candidates("2000-01-01")) == 3
    st.close()


def test_budget_stop_and_failures_do_not_break_the_run(tmp_path):
    items = [_item(1, "Budget breaker paper"), _item(2, "Fail paper"), _item(3, "Good paper on triage")]
    st, run = _store(tmp_path, items)
    stats = run_triage(st, run, FakeGateway({}), Rubric(concurrency=1), Mutes(), None, now=NOW)
    assert stats.stopped and "budget" in stats.stopped
    assert stats.errors + stats.triaged + stats.deferred == 3
    assert st.conn.execute("SELECT COUNT(*) FROM triage WHERE decision = 'error'").fetchone()[0] == stats.errors
    st.close()


def test_without_llm_everything_waits_and_gate_filters(tmp_path):
    items = [_item(n, f"Item {n} about sepsis models in intensive care", text=f"sepsis {'x' * n}") for n in range(1, 6)]
    st, run = _store(tmp_path, items)
    assert run_triage(st, run, None, RUBRIC, Mutes(), HashEmbedder(64), now=NOW).deferred == 5

    class Gate:
        version = "medico-test"

        def score(self, vectors):
            return np.linspace(0.9, 0.1, len(vectors))

    stats = run_triage(st, run, FakeGateway({}), Rubric(classifier_top_n=2), Mutes(), HashEmbedder(64),
                       gates={"medico": Gate()}, now=NOW)
    assert (stats.gated, stats.triaged) == (3, 2)
    gated = st.conn.execute("SELECT pre_score, classifier_version FROM triage WHERE decision='gated'").fetchall()
    assert len(gated) == 3 and all(r[1] == "medico-test" and r[0] < 0.9 for r in gated)
    st.close()


def test_triage_v2_explains_the_new_item_kinds():
    from sotawhat.items import Item

    system = system_prompt()
    assert "kind repo" in system and "mcp_server" in system and "{{" not in system
    repo = Item(id="url:https://github.com/o/r", kind="repo", source="github:ai", source_id="r", title="o/r — MCP server",
                url="https://github.com/o/r", text="GitHub repository · ★ 314")
    assert "kind: repo" in item_message(repo)
