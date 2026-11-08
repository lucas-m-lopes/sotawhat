# tests/test_gateway.py
from datetime import datetime, timezone

import pytest
from pydantic import BaseModel

from sotawhat.config import Settings
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure, LLMGateway, extract_json, strict_schema
from sotawhat.llm.openrouter import Completion, InsufficientCredits, OpenRouterError
from sotawhat.llm.tasks import DEFAULT_TASKS, resolve
from sotawhat.store.db import Store


class Verdict(BaseModel):
    title: str
    score: int
    note: str | None = None


def _completion(content, model="deepseek/deepseek-v4.1-flash-1017", cost=0.001):
    return Completion(content=content, model=model, provider="DeepInfra", generation_id="gen-1",
                      input_tokens=100, output_tokens=20, reasoning_tokens=5, cached_tokens=0,
                      cost_usd=cost, latency_ms=50, finish_reason="stop")


class FakeClient:
    def __init__(self, *results):
        self.results = list(results)
        self.payloads = []

    def chat(self, payload):
        self.payloads.append(payload)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _settings(**kw):
    return Settings(_env_file=None, **kw)


def test_strict_schema_requires_every_field_and_keeps_title_property():
    schema = strict_schema(Verdict)
    assert schema["required"] == ["title", "score", "note"]
    assert schema["additionalProperties"] is False
    assert "title" in schema["properties"]
    assert "default" not in schema["properties"]["note"]


def test_extract_json_strips_fences_and_chatter():
    assert extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert extract_json('Sure! {"a": 1} hope it helps') == '{"a": 1}'


def test_structured_returns_model_and_records_real_cost(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        client = FakeClient(_completion('{"title": "x", "score": 4, "note": null}', cost=0.002))
        gw = LLMGateway(client, store=st, settings=_settings(), run_id=7)
        out = gw.structured("triage", [{"role": "user", "content": "rate"}], Verdict)
        assert out == Verdict(title="x", score=4)
        sent = client.payloads[0]
        assert sent["models"] == list(DEFAULT_TASKS["triage"].models)
        assert sent["response_format"]["json_schema"]["name"] == "verdict"
        assert sent["provider"]["zdr"] is True
        row = st.conn.execute("SELECT * FROM llm_calls").fetchone()
        assert (row["run_id"], row["task"], row["status"], row["provider"]) == (7, "triage", "ok", "DeepInfra")
        assert row["cost_usd"] == pytest.approx(0.002)


def test_structured_repairs_invalid_json_once(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        client = FakeClient(_completion('{"title": "x"}'), _completion('{"title": "x", "score": 3, "note": null}'))
        out = LLMGateway(client, store=st, settings=_settings()).structured("triage", [], Verdict)
        assert out.score == 3
        assert "did not validate" in client.payloads[1]["messages"][-1]["content"]
        statuses = [r[0] for r in st.conn.execute("SELECT status FROM llm_calls ORDER BY id")]
        assert statuses == ["invalid", "ok"]


def test_structured_moves_to_next_model_after_error():
    client = FakeClient(OpenRouterError("HTTP 400: no endpoint"),
                        _completion('{"title": "y", "score": 1, "note": "ok"}', model="xiaomi/mimo-v2.6-flash"))
    out = LLMGateway(client).structured("triage", [], Verdict)
    assert out.title == "y"
    assert client.payloads[1]["model"] == "xiaomi/mimo-v2.6-flash"


def test_structured_raises_after_all_models_fail():
    errors = [OpenRouterError("down")] * len(DEFAULT_TASKS["triage"].models)
    with pytest.raises(LLMFailure):
        LLMGateway(FakeClient(*errors)).structured("triage", [], Verdict)


def test_insufficient_credits_is_not_swallowed():
    with pytest.raises(InsufficientCredits):
        LLMGateway(FakeClient(InsufficientCredits("HTTP 402"))).structured("triage", [], Verdict)


def test_budget_blocks_call_before_spending(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        st.record_llm_call(task="triage", requested_model="m", status="ok", cost_usd=1.5)
        client = FakeClient()
        gw = LLMGateway(client, store=st, settings=_settings(), budget_day=1.0,
                        now=lambda: datetime.now(timezone.utc))
        with pytest.raises(BudgetExceeded):
            gw.structured("triage", [], Verdict)
        assert client.payloads == []


def test_env_override_puts_model_first():
    spec = resolve("triage", _settings(sotawhat_model_triage="z-ai/glm-5.3-flash"))
    assert spec.models[0] == "z-ai/glm-5.3-flash"
    assert spec.models.count("z-ai/glm-5.3-flash") == 1


def test_resolve_precedence_defaults_yaml_env():
    yaml_tasks = {"triage": {"models": ["a/x", "b/y"], "reasoning": "high", "max_tokens": 900}}
    spec = resolve("triage", None, yaml_tasks)
    assert (spec.models, spec.reasoning, spec.max_tokens) == (("a/x", "b/y"), "high", 900)
    spec = resolve("triage", _settings(sotawhat_model_triage="b/y"), yaml_tasks)
    assert spec.models == ("b/y", "a/x")                      # .env wins for the primary
    assert resolve("extract", None, yaml_tasks) == DEFAULT_TASKS["extract"]


def test_structured_call_reports_cost_attempts_and_validity(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        client = FakeClient(_completion('{"title": "x"}', cost=0.001),
                            _completion('{"title": "x", "score": 4, "note": null}', model="z-ai/glm-5.3-flash",
                                        cost=0.002))
        gw = LLMGateway(client, store=st, settings=_settings(), tasks={"triage": {"models": ["a/x"]}})
        res = gw.structured_call("triage", [{"role": "user", "content": "rate"}], Verdict)
        assert res.output.score == 4 and res.model == "z-ai/glm-5.3-flash" and res.provider == "DeepInfra"
        assert (res.attempts, res.first_try_valid) == (2, False) and abs(res.cost_usd - 0.003) < 1e-9
        assert client.payloads[0]["model"] == "a/x"           # config/llm.yaml chain was used
