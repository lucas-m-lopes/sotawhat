# sotawhat/llm/gateway.py
"""Task-level LLM gateway (SDD §6.6): strict JSON output, repair + fallback, budget, cost ledger."""
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ValidationError

from sotawhat.llm.openrouter import InsufficientCredits, OpenRouterError, Privacy, build_payload
from sotawhat.llm.tasks import resolve

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class BudgetExceeded(Exception):
    pass


class LLMFailure(Exception):
    pass


@dataclass
class StructuredResult:
    output: object
    model: str               # effective model reported by OpenRouter
    provider: str | None
    cost_usd: float          # every call made for this result, invalid attempts included
    latency_ms: int          # the successful call
    attempts: int            # calls made, including invalid JSON and errors
    first_try_valid: bool    # valid on the very first call


def _strictify(node):
    if isinstance(node, list):
        for sub in node:
            _strictify(sub)
        return
    if not isinstance(node, dict):
        return
    node.pop("default", None)
    node.pop("title", None)
    props = node.get("properties")
    if isinstance(props, dict):
        node["required"] = list(props)
        node["additionalProperties"] = False
        for sub in props.values():
            _strictify(sub)
    for key in ("items", "anyOf", "allOf", "oneOf", "prefixItems"):
        if key in node:
            _strictify(node[key])
    for sub in (node.get("$defs") or {}).values():
        _strictify(sub)


def strict_schema(model_cls) -> dict:
    """Pydantic JSON Schema -> strict structured-output schema (all keys required, no extras)."""
    schema = model_cls.model_json_schema()
    _strictify(schema)
    return schema


def extract_json(content: str) -> str:
    text = _FENCE.sub("", content.strip())
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


def _period_starts(now):
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return day.isoformat(timespec="seconds"), day.replace(day=1).isoformat(timespec="seconds")


class LLMGateway:
    def __init__(self, client, store=None, settings=None, run_id=None, budget_day=None,
                 budget_month=None, now=lambda: datetime.now(timezone.utc), tasks=None):
        self.client = client
        self.store = store
        self.settings = settings
        self.run_id = run_id
        self.tasks = tasks or {}   # config/llm.yaml `tasks`
        self._now = now
        if settings is not None:
            self.privacy = Privacy(zdr=settings.openrouter_zdr, data_collection=settings.openrouter_data_collection,
                                   quantizations=settings.quantizations)
            budget_day = settings.sotawhat_llm_budget_usd_day if budget_day is None else budget_day
            budget_month = settings.sotawhat_llm_budget_usd_month if budget_month is None else budget_month
        else:
            self.privacy = Privacy()
        self.budget_day = budget_day
        self.budget_month = budget_month

    def _check_budget(self):
        if self.store is None:
            return
        day_start, month_start = _period_starts(self._now())
        if self.budget_day is not None and self.store.llm_cost_since(day_start) >= self.budget_day:
            raise BudgetExceeded(f"daily LLM budget of US$ {self.budget_day:.2f} reached")
        if self.budget_month is not None and self.store.llm_cost_since(month_start) >= self.budget_month:
            raise BudgetExceeded(f"monthly LLM budget of US$ {self.budget_month:.2f} reached")

    def _record(self, task, requested, completion=None, status="ok", error=None):
        if self.store is None:
            return
        fields = dict(run_id=self.run_id, task=task, requested_model=requested, status=status,
                      error=(error or "")[:500] or None)
        if completion is not None:
            fields.update(model=completion.model, provider=completion.provider,
                          generation_id=completion.generation_id, input_tokens=completion.input_tokens,
                          output_tokens=completion.output_tokens, reasoning_tokens=completion.reasoning_tokens,
                          cached_tokens=completion.cached_tokens, cost_usd=completion.cost_usd,
                          latency_ms=completion.latency_ms)
        self.store.record_llm_call(**fields)

    def structured(self, task, messages, output_model, models=None):
        """Return a validated `output_model` (see `structured_call`)."""
        return self.structured_call(task, messages, output_model, models).output

    def structured_call(self, task, messages, output_model, models=None) -> StructuredResult:
        """Tries each model (with the remaining ones as server-side fallbacks); one repair round per
        model when the JSON does not validate. Returns the output plus what it took to get it."""
        spec = resolve(task, self.settings, self.tasks)
        chain = tuple(models) if models else spec.models
        schema = strict_schema(output_model)
        name = re.sub(r"[^a-z0-9_]+", "_", output_model.__name__.lower())
        last_error = None
        attempts, cost = 0, 0.0
        for i, model in enumerate(chain):
            convo = list(messages)
            for _attempt in range(2):
                self._check_budget()
                payload = build_payload(chain[i:], convo, schema=schema, schema_name=name,
                                        reasoning=spec.reasoning, max_tokens=spec.max_tokens,
                                        privacy=self.privacy)
                attempts += 1
                try:
                    completion = self.client.chat(payload)
                except InsufficientCredits as exc:
                    self._record(task, model, status="error", error=str(exc))
                    raise
                except OpenRouterError as exc:
                    self._record(task, model, status="error", error=str(exc))
                    last_error = exc
                    break
                cost += completion.cost_usd
                try:
                    result = output_model.model_validate_json(extract_json(completion.content))
                except ValidationError as exc:
                    self._record(task, model, completion, status="invalid", error=str(exc))
                    last_error = exc
                    problems = json.dumps(exc.errors(include_url=False)[:3], default=str)
                    convo = list(messages) + [
                        {"role": "assistant", "content": completion.content},
                        {"role": "user", "content": "The previous answer did not validate against the JSON "
                                                    f"schema: {problems}. Reply again with only valid JSON."}]
                    continue
                self._record(task, model, completion)
                return StructuredResult(output=result, model=completion.model or model,
                                        provider=completion.provider, cost_usd=cost,
                                        latency_ms=completion.latency_ms, attempts=attempts,
                                        first_try_valid=attempts == 1)
        raise LLMFailure(f"{task}: every model failed; last error: {last_error}")
