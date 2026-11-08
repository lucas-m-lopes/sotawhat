# tests/test_measures.py
"""P6: the SDD goals measured from the store, the extraction sample and the calibration proposals."""
import json
from datetime import datetime, timezone

from sotawhat.configfiles import Rubric
from sotawhat.evals import calibrate, extract_eval, metrics
from sotawhat.ideation.config import WEIGHTS
from sotawhat.items import Item
from sotawhat.store.db import Store

NOW = datetime(2026, 11, 8, 21, 0, tzinfo=timezone.utc)


def _store(tmp_path, votes=(), decisions=()):
    st = Store(tmp_path / "insight.db")
    run = st.start_run("daily")
    st.finish_run(run, ok=True, stats={})
    failed = st.start_run("daily")
    st.finish_run(failed, ok=False, stats={}, error="boom")
    ids = [f"pmid:{n}" for n in range(len(decisions))]
    st.upsert_items([Item(id=i, kind="paper", source="pubmed", source_id=i, title=f"T {i}", url="u") for i in ids], run)
    for item_id, (decision, total) in zip(ids, decisions):
        st.record_triage(item_id, run, decision, total=total, summary_pt="Resumo.")
    for item_id, value in zip(ids, votes):
        if value:
            st.add_feedback("item", item_id, "down" if value == "flip" else value, "telegram")
            if value == "flip":
                st.add_feedback("item", item_id, "up", "web")                # the latest vote counts
    return st, run, ids


def test_triage_by_votes_and_run_health(tmp_path):
    st, run, ids = _store(tmp_path, votes=["up", "down", "test", "flip", None, "up"],
                          decisions=[("main", 3.5), ("main", 2.9), ("frontier", 3.6), ("main", 3.0), ("reject", 1.0),
                                     ("radar", 2.0)])
    g2 = metrics.triage_by_votes(st)
    assert g2["votes"] == 5 and g2["table"]["main"] == {"up": 2, "down": 1}
    assert g2["precision"]["main"] == (0.667, 3) and g2["delivered"] == (0.75, 4)
    g1 = metrics.run_health(st, now=NOW)
    assert (g1["runs"], g1["ok"], g1["rate"]) == (2, 1, 0.5)
    st.record_source_error("rss:x", "timeout")
    for _ in range(2):
        st.record_source_error("rss:x", "timeout")
    assert metrics.run_health(st, now=NOW)["failing_sources"][0]["name"] == "rss:x"
    st.record_delivery(run, "2026-11-08", ids[0], "k0", "main", 1)
    st.record_delivery(run, "2026-11-08", ids[1], "k1", "main", 2)
    st.record_delivery(run, "2026-11-08", ids[5], "k5", "radar", 1)
    sizes = metrics.digest_sizes(st, now=NOW)
    assert (sizes["digests"], sizes["max_main"], sizes["max_radar"]) == (1, 2, 1)
    st.close()


def test_ideas_metrics_and_goals_report(tmp_path):
    st, run, ids = _store(tmp_path)
    weekly = st.start_run("weekly")
    for n, (status, lens) in enumerate([("curtida", "jtbd"), ("rejeitada", "triz"), ("nova", "jtbd"), ("testar", "triz")]):
        idea = st.add_idea(weekly, f"Ideia {n}", card={"draft": {}, "model": "deepseek/x" if n % 2 else "z-ai/y"},
                           lens=lens, candidate={"sampler": "serendipity"}, status=status)
        st.update_idea(idea, selected=True)
    g4 = metrics.ideas_metrics(st, now=datetime.now(timezone.utc))
    assert (g4["finalists"], g4["weekly_runs"], g4["per_weekly_run"], g4["decided"]) == (4, 1, 4.0, 3)
    assert g4["explore"] == (0.667, 3) and g4["by_lens"]["triz"] == (0.5, 2) and g4["by_family"]["z-ai"] == (1.0, 1)
    summary = tmp_path / "extract_v1.json"
    summary.write_text(json.dumps({"items": 2, "entities": {"right": 9, "total": 10, "precision": 0.9},
                                   "relations": {"right": 1, "total": 2, "precision": 0.5}, "by_type": {}}))
    g = metrics.goals(st, now=datetime.now(timezone.utc), extract_summary=summary)
    text = metrics.render_goals(g)
    assert "| G1 · ingestão |" in text and "50% de 2 runs" in text and "⏳ poucos dados (n=2)" in text
    assert "90% em 10 entidades" in text and "busca" in text and "| main | 0 | 0 | 0 | —" not in text
    assert "67% de 3 decididas" in text
    st.close()


def test_extraction_draft_and_import(tmp_path):
    st, run, ids = _store(tmp_path, decisions=[("main", 3.5), ("frontier", 3.6), ("reject", 1.0)])
    llm = st.add_entity("technique", "large language model", "large language model")
    burden = st.add_entity("problem", "documentation burden", "documentation burden")
    for item_id in ids:
        st.record_extraction(item_id, run, "ok", payload={})
        st.add_mention(item_id, llm, "main", "2026-11-08")
        st.add_mention(item_id, burden, "mentioned", "2026-11-08")
        st.add_relation(llm, "addresses", burden, item_id)
    path = extract_eval.write_draft(st, folder=tmp_path / "extract", n=10)
    text = path.read_text(encoding="utf-8")
    assert text.count("## ") == 2 and "`pmid:2`" not in text                   # the rejected item stays out
    assert "- [x] E · technique · large language model (técnica, main)" in text
    assert "- [x] R · addresses · large language model —aborda→ documentation burden" in text
    edited = text.replace("- [x] E · problem", "- [ ] E · problem", 1)
    path.write_text(edited, encoding="utf-8")
    result = extract_eval.import_labels(tmp_path / "extract")
    assert result["items"] == 2 and result["entities"] == {"right": 3, "total": 4, "precision": 0.75}
    assert result["relations"]["precision"] == 1.0 and result["by_type"]["problem"]["precision"] == 0.5
    assert json.loads((tmp_path / "extract" / "extract_v1.json").read_text(encoding="utf-8"))["items"] == 2
    try:
        extract_eval.write_draft(st, folder=tmp_path / "extract")
        raise AssertionError("must refuse to overwrite the annotations")
    except FileExistsError:
        pass
    st.close()


def test_cutoff_only_goes_up_and_needs_enough_items():
    pairs = [(2.9, False)] * 6 + [(3.1, False)] * 2 + [(3.4, True)] * 12 + [(3.6, True)] * 4
    proposal = calibrate.cutoff(pairs, current=2.8)
    assert proposal["proposed"] == 3.1 and proposal["precision_proposed"] == 0.889 and proposal["n_proposed"] == 18
    assert calibrate.cutoff([(3.0, True)] * 20, current=2.8)["proposed"] == 2.8          # already above the goal
    assert calibrate.cutoff([(3.0, False)] * 5 + [(3.5, True)] * 3, current=2.8)["proposed"] == 2.8   # too few items


def test_proposals_wait_for_data_and_apply_keeps_the_comments(tmp_path):
    st, run, ids = _store(tmp_path, votes=["up"] * 3, decisions=[("main", 3.0)] * 3)
    assert calibrate.triage_proposal(st, Rubric()) == {"ok": False, "votes": 3, "missing": 97}
    assert calibrate.weights_proposal(st, WEIGHTS)["missing"] == 30
    weekly = st.start_run("weekly")
    for n in range(30):
        good = n % 2 == 0
        axes = {k: 5.0 for k in WEIGHTS} | {"valor": 9.0 if good else 3.0}
        idea = st.add_idea(weekly, f"I{n}", card={"draft": {}}, status="curtida" if good else "rejeitada")
        st.update_idea(idea, selected=True, scores={"eixos": axes})
    weights = calibrate.weights_proposal(st, WEIGHTS)
    assert weights["ok"] and weights["signal"]["valor"] == 1.0 and abs(sum(weights["proposed"].values()) - 1) < 1e-9
    assert weights["proposed"]["valor"] == 0.61 and weights["proposed"]["fit"] == 0.05     # 0.60 + rounding drift
    rubric = tmp_path / "rubric.yaml"
    rubric.write_text("# comentário\nmin_total: 2.8\nmin_b: 3\nfrontier_min_total: 3.3\n", encoding="utf-8")
    triage = {"ok": True, "votes": 120, "main": {"current": 2.8, "proposed": 3.4},
              "frontier": {"current": 3.3, "proposed": 3.3}}
    assert calibrate.apply_triage(rubric, triage, "2026-12-06") == ["min_total"]
    text = rubric.read_text(encoding="utf-8")
    assert text.startswith("# comentário") and "min_total: 3.4   # calibrado em 2026-12-06 com 120 votos" in text
    assert "frontier_min_total: 3.3\n" in text
    ideation = tmp_path / "ideation.yaml"
    calibrate.apply_weights(ideation, weights, "2026-12-06")
    from sotawhat.ideation.config import load_ideation

    assert load_ideation(ideation).weights == weights["proposed"]
    assert "Pesos das ideias" in calibrate.render({"ok": False, "votes": 3, "missing": 97}, weights, "2026-12-06")
    st.close()


def test_cli_measures():
    from sotawhat.cli import parse_args

    assert parse_args(["eval", "report", "--send"]).send is True
    ns = parse_args(["eval", "extract", "draft", "--n", "20"])
    assert (ns.eval_command, ns.action, ns.n, ns.force) == ("extract", "draft", 20, False)
    assert parse_args(["calibrate"]).apply is False and parse_args(["eval", "triage"]).eval_command == "triage"
