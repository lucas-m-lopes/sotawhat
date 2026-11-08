# tests/test_extract.py
"""Entity extraction (SDD §6.8): strict JSON per approved item, budget cap, parallel calls, resolver hook."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from sotawhat.items import Item, from_row
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure, StructuredResult, strict_schema
from sotawhat.llm.schemas import Extraction, SameEntity
from sotawhat.pipeline.extract import PROMPT_VERSION, item_message, messages_for, run_extraction
from sotawhat.store.db import Store

NOW = datetime(2026, 11, 8, 15, 0, tzinfo=timezone.utc)
SAMPLE = {
    "entities": [
        {"name": "MedGemma 1.5", "type": "model", "category": "C04", "role": "main"},
        {"name": "Google", "type": "organization", "category": "none", "role": "mentioned"},
        {"name": "RadQA", "type": "dataset", "category": "none", "role": "used"},
    ],
    "relations": [{"source": "MedGemma 1.5", "relation": "developed_by", "target": "Google"},
                  {"source": "MedGemma 1.5", "relation": "evaluated_on", "target": "RadQA"}],
    "claims": [{"text_pt": "O MedGemma 1.5 atinge 78% de acurácia no RadQA.", "metric": "accuracy", "value": "78%"}],
    "maturity": "research",
    "data_modalities": ["imaging"],
}


def _item(n, title=None):
    return Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=title or f"Paper {n}",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", authors=["Ana"], published_at="2026-11-07",
                text="An open multimodal model for CT. " * 10, pmid=str(n), profile="medico")


def _store(tmp_path, decisions, titles=None):
    st = Store(tmp_path / "insight.db")
    run = st.start_run("daily")
    titles = titles or {}
    st.upsert_items([_item(n, titles.get(n)) for n in decisions], run)
    for n, decision in decisions.items():
        st.conn.execute("UPDATE items SET fetched_at = ? WHERE id = ?", (f"2026-11-08T10:{n:02d}:00+00:00", f"pmid:{n}"))
        st.record_triage(f"pmid:{n}", run, decision, tags={"domains": ["A03"], "techniques": ["C04"]})
    st.conn.commit()
    return st, run


class FakeGateway:
    def __init__(self, fail_on=(), stop_on=(), budget_day=None):
        self.fail_on, self.stop_on, self.budget_day = set(fail_on), set(stop_on), budget_day
        self.calls = []

    def structured_call(self, task, messages, output_model, models=None):
        title = messages[1]["content"].split("\n")[1]
        self.calls.append((task, title))
        if any(word in title for word in self.stop_on):
            raise BudgetExceeded("daily LLM budget of US$ 1.00 reached")
        if any(word in title for word in self.fail_on):
            raise LLMFailure("extract: every model failed; last error: bad json")
        return StructuredResult(output=output_model.model_validate(SAMPLE), model="fake/extractor", provider="p",
                                cost_usd=0.002, latency_ms=5, attempts=1, first_try_valid=True)


class FakeResolver:
    def __init__(self, boom_on=()):
        self.rows, self.boom_on = [], set(boom_on)

    def apply(self, row, extraction):
        if row["id"] in self.boom_on:
            raise RuntimeError("database is locked")
        self.rows.append((row["id"], len(extraction.entities)))
        return SimpleNamespace(new_entities=2, mentions=3, relations=2, dropped=1, judge_calls=1, merges=1)


def test_extraction_schema_is_strict_and_guards_portuguese_claims():
    out = Extraction.model_validate(SAMPLE)
    assert out.entities[0].name == "MedGemma 1.5" and out.relations[1].relation == "evaluated_on"
    schema = strict_schema(Extraction)
    assert set(schema["required"]) == {"entities", "relations", "claims", "maturity", "data_modalities"}
    entity = schema["$defs"]["ExtractedEntity"]
    assert entity["additionalProperties"] is False and set(entity["required"]) == {"name", "type", "category", "role"}
    with pytest.raises(ValidationError):
        Extraction.model_validate({**SAMPLE, "entities": [{**SAMPLE["entities"][0], "category": "X99"}]})
    with pytest.raises(ValidationError, match="Portuguese"):
        Extraction.model_validate({**SAMPLE, "claims": [{"text_pt": "准确率 78%", "metric": "accuracy", "value": "78%"}]})
    assert SameEntity.model_validate({"same": True, "reason": "short and long form"}).same is True


def test_prompt_and_item_message():
    system = messages_for(_item(1), {}, max_chars=100)[0]["content"]
    assert "C04" in system and "B03" in system and "{{" not in system
    text = item_message(_item(1, "MedGemma 1.5 reads CT volumes"), {"domains": ["A03"], "techniques": ["C04"]},
                        max_chars=40)
    assert "title: MedGemma 1.5 reads CT volumes" in text and "url host: pubmed.ncbi.nlm.nih.gov" in text
    assert "A03 radiologia/imagem" in text and "C04 modelos de fundação multimodais" in text
    assert "An open multimodal model for CT. An op" in text and "CT. An open multimodal model for CT. An open" not in text


def test_run_extraction_records_results_and_resolves_them(tmp_path):
    st, run = _store(tmp_path, {1: "main", 2: "frontier", 3: "radar", 4: "reject"}, titles={2: "bad json paper"})
    gateway, resolver = FakeGateway(fail_on={"bad json"}), FakeResolver()
    stats = run_extraction(st, run, gateway, resolver, now=NOW)
    assert (stats.candidates, stats.extracted, stats.errors) == (3, 2, 1)
    assert sorted(r for r, _ in resolver.rows) == ["pmid:1", "pmid:3"] and all(n == 3 for _, n in resolver.rows)
    assert (stats.new_entities, stats.mentions, stats.relations, stats.dropped) == (4, 6, 4, 2)
    assert round(stats.cost_usd, 4) == 0.004 and {task for task, _ in gateway.calls} == {"extract"}
    ok = st.get_extraction("pmid:1")
    assert (ok["status"], ok["model"], ok["prompt_version"]) == ("ok", "fake/extractor", PROMPT_VERSION)
    assert st.get_extraction("pmid:2")["status"] == "error" and st.get_extraction("pmid:4") is None
    again = run_extraction(st, run, FakeGateway(), FakeResolver(), now=NOW)
    assert again.candidates == 1 and again.extracted == 1          # only the errored one is retried
    st.close()


def test_run_extraction_stops_on_budget_and_respects_limit(tmp_path):
    st, run = _store(tmp_path, {1: "main", 2: "main", 3: "main"}, titles={2: "stop here"})
    limited = run_extraction(st, run, FakeGateway(), FakeResolver(), limit=1, now=NOW)
    assert (limited.candidates, limited.extracted) == (1, 1)
    stats = run_extraction(st, run, FakeGateway(stop_on={"stop here"}), FakeResolver(), concurrency=1, now=NOW)
    assert stats.stopped and "budget" in stats.stopped and stats.deferred >= 1
    assert st.get_extraction("pmid:2") is None
    st.close()


def test_budget_cap_uses_the_average_extraction_cost(tmp_path):
    st, run = _store(tmp_path, {n: "main" for n in range(1, 6)})
    st.record_llm_call(run_id=run, task="extract", requested_model="m", status="ok", cost_usd=0.002)
    stats = run_extraction(st, run, FakeGateway(budget_day=0.01), FakeResolver(), now=datetime.now(timezone.utc))
    assert (stats.extracted, stats.deferred) == (3, 2) and "orçamento" in stats.stopped   # 0.8·0.01 − 0.002 = 0.006
    st.close()


def test_a_resolver_failure_is_recorded_and_retried_later(tmp_path):
    st, run = _store(tmp_path, {1: "main", 2: "main"})
    stats = run_extraction(st, run, FakeGateway(), FakeResolver(boom_on={"pmid:2"}), now=NOW)
    assert (stats.extracted, stats.errors) == (1, 1)
    failed = st.get_extraction("pmid:2")
    assert failed["status"] == "error" and failed["error"].startswith("resolve: ") and failed["payload_json"]
    assert [r["id"] for r in st.extraction_candidates()] == ["pmid:2"]
    assert from_row(st.extraction_candidates()[0]).title == "Paper 2"
    st.close()
