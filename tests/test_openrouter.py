# tests/test_openrouter.py
import json

import httpx
import pytest

from sotawhat.llm.openrouter import (InsufficientCredits, OpenRouterClient, OpenRouterError, Privacy,
                                     build_payload)

OK = json.load(open("tests/fixtures/openrouter/chat_ok.json", encoding="utf-8"))
MESSAGES = [{"role": "user", "content": "ping"}]


def _client(handler, sleeps=None):
    return OpenRouterClient("sk-test", transport=httpx.MockTransport(handler),
                            sleep=(sleeps.append if sleeps is not None else (lambda s: None)))


def test_build_payload_enforces_privacy_schema_and_fallbacks():
    p = build_payload(["a/primary", "b/fallback"], MESSAGES, schema={"type": "object"},
                      schema_name="triage", reasoning="low", max_tokens=900)
    assert p["model"] == "a/primary" and p["models"] == ["a/primary", "b/fallback"]
    assert p["response_format"] == {"type": "json_schema", "json_schema": {
        "name": "triage", "strict": True, "schema": {"type": "object"}}}
    assert p["plugins"] == [{"id": "response-healing"}]
    assert p["reasoning"] == {"effort": "low", "exclude": True}
    assert p["max_tokens"] == 900
    assert p["provider"] == {"require_parameters": True, "allow_fallbacks": True, "data_collection": "deny",
                             "zdr": True, "quantizations": ["fp8", "bf16", "fp16", "fp32", "unknown"],
                             "sort": "price"}


def test_build_payload_single_model_and_reasoning_off():
    p = build_payload(["a/only"], MESSAGES, reasoning="none", privacy=Privacy(zdr=False, quantizations=[]))
    assert "models" not in p and "response_format" not in p
    assert p["reasoning"] == {"effort": "none"}
    assert "zdr" not in p["provider"] and "quantizations" not in p["provider"]


def test_chat_posts_and_parses_usage_cost_and_provider():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=OK)

    c = _client(handler).chat(build_payload(["deepseek/deepseek-v4.1-flash-1017"], MESSAGES))
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["provider"]["zdr"] is True
    assert json.loads(c.content) == {"ok": True, "lang": "pt-BR"}
    assert (c.model, c.provider, c.generation_id) == ("deepseek/deepseek-v4.1-flash-1017", "DeepInfra",
                                                      "gen-1762500000-abc123")
    assert (c.input_tokens, c.output_tokens, c.reasoning_tokens, c.cached_tokens) == (120, 30, 12, 64)
    assert c.cost_usd == pytest.approx(0.0000187)


def test_chat_retries_429_then_succeeds():
    responses = iter([httpx.Response(429, headers={"retry-after": "0"}, json={"error": {"message": "slow"}}),
                      httpx.Response(200, json=OK)])
    sleeps = []
    c = _client(lambda request: next(responses), sleeps).chat(build_payload(["m"], MESSAGES))
    assert c.cost_usd > 0 and sleeps == [0.0]


def test_chat_raises_on_402_without_retry():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(402, json={"error": {"message": "Insufficient credits"}})

    with pytest.raises(InsufficientCredits):
        _client(handler).chat(build_payload(["m"], MESSAGES))
    assert len(calls) == 1


def test_chat_does_not_retry_400_and_gives_up_after_max_retries():
    with pytest.raises(OpenRouterError) as bad:
        _client(lambda r: httpx.Response(400, json={"error": {"message": "bad schema"}})).chat({"model": "m"})
    assert bad.value.status == 400 and not bad.value.retryable
    sleeps = []
    with pytest.raises(OpenRouterError):
        _client(lambda r: httpx.Response(503, text="down"), sleeps).chat({"model": "m"})
    assert len(sleeps) == 3


def test_key_info_and_models():
    def handler(request):
        if request.url.path.endswith("/key"):
            return httpx.Response(200, json={"data": {"limit": 30, "usage": 1.5, "limit_remaining": 28.5}})
        return httpx.Response(200, json={"data": [{"id": "deepseek/deepseek-v4.1-flash-1017"}]})

    client = _client(handler)
    assert client.key_info()["limit_remaining"] == 28.5
    assert client.models()[0]["id"] == "deepseek/deepseek-v4.1-flash-1017"
