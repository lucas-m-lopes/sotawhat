# sotawhat/llm/openrouter.py
"""Thin OpenRouter Chat Completions client over httpx (SDD §6.6). No third-party SDK.

Every request carries the privacy policy: ZDR endpoints only, no data collection,
quantization >= fp8 and only providers that honour all request parameters.
"""
import time
from dataclasses import dataclass, field

import httpx

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_RETRYABLE = {408, 429, 500, 502, 503, 504}


class OpenRouterError(Exception):
    def __init__(self, message, status=None, retryable=False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class InsufficientCredits(OpenRouterError):
    """HTTP 402 — buy credits or raise the key limit; never retried."""


@dataclass
class Privacy:
    zdr: bool = True
    data_collection: str = "deny"
    quantizations: list = field(default_factory=lambda: ["fp8", "bf16", "fp16", "fp32", "unknown"])
    sort: str | None = "price"
    max_price: dict | None = None     # {"prompt": US$/M, "completion": US$/M}: endpoints above it are never used

    def provider_prefs(self) -> dict:
        prefs = {"require_parameters": True, "allow_fallbacks": True,
                 "data_collection": self.data_collection}
        if self.zdr:
            prefs["zdr"] = True
        if self.quantizations:
            prefs["quantizations"] = list(self.quantizations)
        if self.sort:
            prefs["sort"] = self.sort
        if self.max_price:
            prefs["max_price"] = dict(self.max_price)
        return prefs


@dataclass
class Completion:
    content: str
    model: str
    provider: str | None
    generation_id: str | None
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cached_tokens: int
    cost_usd: float
    latency_ms: int
    finish_reason: str | None


def build_payload(models, messages, schema=None, schema_name="output", reasoning=None,
                  max_tokens=None, privacy=None, healing=True) -> dict:
    """models: primary first, then fallbacks. reasoning: None | "none" | "minimal" | "low" | "medium" | "high"."""
    models = list(models)
    payload = {"model": models[0], "messages": messages}
    if len(models) > 1:
        payload["models"] = models
    if schema is not None:
        payload["response_format"] = {"type": "json_schema",
                                      "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
        if healing:
            payload["plugins"] = [{"id": "response-healing"}]
    if reasoning:
        payload["reasoning"] = {"effort": reasoning} if reasoning == "none" else {"effort": reasoning, "exclude": True}
    if max_tokens:
        payload["max_tokens"] = max_tokens
    payload["provider"] = (privacy or Privacy()).provider_prefs()
    return payload


def _provider_of(data):
    if data.get("provider"):
        return data["provider"]
    meta = data.get("openrouter_metadata") or {}
    for ep in (meta.get("endpoints") or {}).get("available", []):
        if ep.get("selected"):
            return ep.get("provider")
    return None


def parse_response(data, latency_ms) -> Completion:
    if data.get("error"):
        err = data["error"]
        raise OpenRouterError(f"upstream error: {err.get('message', err)}", status=err.get("code"))
    choice = (data.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    usage = data.get("usage") or {}
    return Completion(
        content=content, model=data.get("model", ""), provider=_provider_of(data),
        generation_id=data.get("id"),
        input_tokens=usage.get("prompt_tokens") or 0, output_tokens=usage.get("completion_tokens") or 0,
        reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0,
        cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
        cost_usd=float(usage.get("cost") or 0.0), latency_ms=latency_ms,
        finish_reason=choice.get("finish_reason"))


def _error_from(response) -> OpenRouterError:
    try:
        message = (response.json().get("error") or {}).get("message") or response.text[:200]
    except ValueError:
        message = response.text[:200]
    status = response.status_code
    if status == 402:
        return InsufficientCredits(f"HTTP 402: {message}", status=status)
    return OpenRouterError(f"HTTP {status}: {message}", status=status, retryable=status in _RETRYABLE)


class OpenRouterClient:
    def __init__(self, api_key, base_url=DEFAULT_BASE_URL, app_title="", timeout=120.0,
                 max_retries=3, backoff_s=2.0, transport=None, sleep=time.sleep):
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}   # catalog endpoints are public
        if app_title:
            headers["X-Title"] = app_title
        self._http = httpx.Client(base_url=base_url, headers=headers, timeout=timeout, transport=transport)
        self.max_retries = max_retries
        self.backoff_s = backoff_s
        self._sleep = sleep

    def close(self):
        self._http.close()

    def _delay(self, response, attempt):
        retry_after = response.headers.get("retry-after") if response is not None else None
        if retry_after:
            try:
                return min(float(retry_after), 60.0)
            except ValueError:
                pass
        return min(self.backoff_s * (2 ** attempt), 60.0)

    def chat(self, payload) -> Completion:
        attempt = 0
        while True:
            started = time.monotonic()
            response = None
            try:
                response = self._http.post("/chat/completions", json=payload)
            except httpx.TransportError as exc:
                error = OpenRouterError(f"transport error: {type(exc).__name__}", retryable=True)
            else:
                if response.status_code == 200:
                    return parse_response(response.json(), int((time.monotonic() - started) * 1000))
                error = _error_from(response)
            if not error.retryable or attempt >= self.max_retries:
                raise error
            self._sleep(self._delay(response, attempt))
            attempt += 1

    def _get(self, path, **params):
        response = self._http.get(path, params=params or None)
        if response.status_code != 200:
            raise _error_from(response)
        return response.json().get("data")

    def key_info(self) -> dict:
        return self._get("/key")

    def models(self) -> list:
        return self._get("/models")

    def zdr_endpoints(self) -> list:
        return self._get("/endpoints/zdr")
