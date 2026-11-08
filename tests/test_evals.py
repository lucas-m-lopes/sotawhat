# tests/test_evals.py
import json

import yaml

from sotawhat.configfiles import Rubric, load_llm_config
from sotawhat.evals.bakeoff import (Outcome, apply_winner, evaluate_model, metrics, pick_winner, ranking,
                                    render_report)
from sotawhat.evals.golden import as_item, import_labels, load_golden, read_vault, sample, write_draft
from sotawhat.llm.gateway import LLMFailure, StructuredResult
from sotawhat.llm.schemas import TriageOutput

NOTE = """---
title: {title}
authors: ["Ana Lima", "Bo Chen"]
date: "2026-06-03"
source: {source}
url: "{url}"
keywords: ["radiology"]
tags: ["medical-ai", "source/{source}"]
added: "2026-06-14"
---

# {raw_title}

{body}

**Conceitos:** [[radiology]]

[Source]({raw_url})
"""


def _note(folder, name, title, source, url, body):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.md").write_text(NOTE.format(title=json.dumps(title), raw_title=title, source=source,
                                                   url=url, raw_url=url, body=body), encoding="utf-8")


def _entry(n, profile, source, label=None, text="t" * 400):
    return {"id": f"{source}:{n}", "profile": profile, "source": source, "title": f"T{n}", "url": "",
            "published_at": "", "authors": [], "text": text, "origin": "store", "label": label, "note": ""}


def test_read_vault_builds_canonical_items(tmp_path):
    _note(tmp_path / "medico" / "arxiv", "a", "BreastGPT: a multimodal LLM", "arxiv",
          "https://arxiv.org/abs/2606.04911v1", "Breast cancer abstract " * 20)
    _note(tmp_path / "medico" / "pubmed", "b", "Sepsis model", "pubmed",
          "https://pubmed.ncbi.nlm.nih.gov/41234567/", "Sepsis abstract " * 20)
    _note(tmp_path / "geral" / "hf_papers", "c", "Agents paper", "hf_papers",
          "https://huggingface.co/papers/2606.00001", "Agents abstract " * 20)
    by_id = {e["id"]: e for e in read_vault(tmp_path)}
    assert set(by_id) == {"arxiv:2606.04911", "pmid:41234567", "arxiv:2606.00001"}
    e = by_id["arxiv:2606.04911"]
    assert e["profile"] == "medico" and e["authors"] == ["Ana Lima", "Bo Chen"] and e["origin"] == "vault"
    assert e["text"].startswith("Breast cancer abstract") and "Conceitos" not in e["text"] and "Source" not in e["text"]


def test_sample_is_stratified_deduplicated_and_reproducible():
    pool = [_entry(n, "medico", "pubmed") for n in range(30)] + [_entry(n, "medico", "crossref") for n in range(3)]
    pool += [_entry(n, "geral", "arxiv") for n in range(30)] + [_entry(99, "geral", "arxiv", text="short")]
    pool += [_entry(1, "medico", "pubmed")]                                   # duplicate id
    picks = sample(pool, n=20, seed=7)
    assert len(picks) == 20 and len({p["id"] for p in picks}) == 20
    assert sum(p["profile"] == "medico" for p in picks) == 10
    assert sum(p["source"] == "crossref" for p in picks) == 3              # round-robin reaches small sources
    assert all(p["id"] != "arxiv:99" for p in picks)                         # too short to judge
    assert [p["id"] for p in sample(pool, n=20, seed=7)] == [p["id"] for p in picks]


def test_draft_and_import_round_trip(tmp_path):
    entries = [_entry(n, "medico", "pubmed") for n in range(4)]
    md, jsonl = write_draft(entries, tmp_path, "g")
    text = md.read_text(encoding="utf-8")
    assert text.count("\nRótulo: \n") == 4 and "`id: pubmed:0`" in text and "**incluir**" in text
    text = text.replace("`id: pubmed:0`\nRótulo: ", "`id: pubmed:0`\nRótulo: incluir")
    text = text.replace("`id: pubmed:1`\nRótulo: ", "`id: pubmed:1`\nRótulo: Excluir — só epidemiologia")
    text = text.replace("`id: pubmed:2`\nRótulo: ", "`id: pubmed:2`\nRótulo: talvez")
    md.write_text(text, encoding="utf-8")
    report = import_labels(tmp_path, "g")
    assert report["labeled"] == 2 and report["unlabeled"] == 1 and report["invalid"] == ["pubmed:2: 'talvez'"]
    golden = load_golden(jsonl)
    assert [(g["id"], g["label"], g["note"]) for g in golden] == [("pubmed:0", "main", ""),
                                                                  ("pubmed:1", "reject", "só epidemiologia")]
    assert as_item(golden[0]).profile == "medico"


def _out(**kw):
    base = dict(summary_pt="Resumo.", hard_exclusion="none", inclusion_rules=[], frontier_ai=4,
                medical_applicability=4, actionability=3, domains=[], problem_types=[], techniques=[],
                evidence_stage="D1", stakeholders=[], br_applicability="F1", cfm_risk="medio", substance=2,
                audience=[], vendor_only=False, reason_pt="Motivo.", why_it_matters_pt="Importa.")
    base.update(kw)
    return TriageOutput(**base)


class FakeGateway:
    def structured_call(self, task, messages, output_model, models=None):
        assert models and len(models) == 1                                    # one model, no fallback
        if "T2" in messages[1]["content"]:
            raise LLMFailure("triage: every model failed")
        low = "T1" in messages[1]["content"]
        return StructuredResult(output=_out(frontier_ai=1 if low else 4, medical_applicability=0 if low else 4), model=models[0],
                                provider="X", cost_usd=0.001, latency_ms=900 if low else 1100, attempts=1,
                                first_try_valid=not low)


def test_evaluate_model_and_metrics():
    golden = [_entry(0, "medico", "pubmed", "main"), _entry(1, "medico", "pubmed", "reject"),
              _entry(2, "medico", "pubmed", "main")]
    outcomes = evaluate_model(FakeGateway(), golden, Rubric(), "a/model", concurrency=2)
    assert [o.predicted for o in outcomes] == ["main", "reject", None]
    m = metrics(outcomes)
    assert (m["precision"], m["recall"], m["failures"]) == (1.0, 0.5, 1)
    assert round(m["f1"], 3) == 0.667 and round(m["accuracy"], 3) == 0.667 and round(m["valid_first_try"], 3) == 0.333
    assert m["confusion"] == {"main": {"main": 1, "falha": 1}, "reject": {"reject": 1}}


def test_winner_report_and_apply(tmp_path):
    results = {"a/x": {"n": 50, "f1": 0.80, "accuracy": 0.7, "valid_first_try": 1.0, "failures": 0, "cost_usd": 0.03,
                       "precision": 0.8, "recall": 0.8, "p50_ms": 1000, "p95_ms": 3000, "confusion": {}},
               "b/y": {"n": 50, "f1": 0.85, "accuracy": 0.7, "valid_first_try": 0.80, "failures": 0, "cost_usd": 0.01,
                       "precision": 0.9, "recall": 0.8, "p50_ms": 1000, "p95_ms": 3000, "confusion": {}},
               "c/z": {"n": 50, "f1": 0.80, "accuracy": 0.7, "valid_first_try": 0.95, "failures": 1, "cost_usd": 0.02,
                       "precision": 0.8, "recall": 0.8, "p50_ms": 1000, "p95_ms": 3000, "confusion": {}}}
    assert pick_winner(results) == "c/z"           # b/y: too much invalid JSON; tie a/x vs c/z -> cheaper
    assert ranking(results, "c/z") == ["c/z", "b/y", "a/x"]
    golden = [_entry(0, "medico", "pubmed", "main")]
    outcomes = {"c/z": [Outcome("pubmed:0", "main", "main", True, 900, "Resumo pt.", "Importa.")]}
    report = render_report("triage", "2026-11-08", results, outcomes, golden, "c/z")
    assert "| **c/z** | 0.80 |" in report and "Resumo pt." in report and "incluir 1" in report
    path = tmp_path / "llm.yaml"
    path.write_text("bakeoff:\n  triage: [a/x, b/y, c/z]\n", encoding="utf-8")
    apply_winner(path, "triage", ["c/z", "b/y", "a/x"], "low", 1500)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["tasks"]["triage"] == {"models": ["c/z", "b/y", "a/x"], "reasoning": "low", "max_tokens": 1500}
    assert data["bakeoff"]["triage"] == ["a/x", "b/y", "c/z"] and load_llm_config(path)["tasks"]["triage"]


def test_frontier_counts_as_incluir_and_outcomes_keep_the_scores():
    class Frontier:
        def structured_call(self, task, messages, output_model, models=None):
            return StructuredResult(output=_out(frontier_ai=5, medical_applicability=0, actionability=4),
                                    model=models[0], provider="X", cost_usd=0.001, latency_ms=800, attempts=1,
                                    first_try_valid=True)

    [o] = evaluate_model(Frontier(), [_entry(0, "geral", "arxiv", "main")], Rubric(), "a/model")
    assert (o.predicted, o.decision) == ("main", "frontier") and (o.scores["A"], o.scores["S"]) == (5, 2)
    assert metrics([o])["f1"] == 1.0
    report = render_report("triage", "2026-11-08", {"a/model": metrics([o])}, {"a/model": [o]},
                           [_entry(0, "geral", "arxiv", "main")], "a/model")
    assert "(incluir · fronteira)" in report
