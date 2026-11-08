# sotawhat/pipeline/extract.py
"""Entity extraction (SDD §6.8). Approved items (main, frontier, radar) without a good extraction go
through the `extract` task with strict JSON, concurrently and within 80% of what is left of the daily
budget. Each result is resolved into the entity graph (graph/resolve.py) as soon as it arrives, in the
calling thread, so the graph writes never race. Failures stay in `extractions` and are retried by the
next runs, up to 3 attempts."""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlsplit

from sotawhat import taxonomy as tx
from sotawhat.items import from_row
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import Extraction

PROMPT_VERSION = "extract_v1"
DEFAULT_COST_PER_ITEM = 0.003   # US$, until the ledger has real extraction calls
OUTCOME_FIELDS = ("new_entities", "mentions", "relations", "dropped", "judge_calls", "merges")
log = logging.getLogger("sotawhat.extract")


@dataclass
class ExtractionStats:
    candidates: int = 0
    extracted: int = 0
    errors: int = 0
    deferred: int = 0          # left for the next run (budget cap, stop, no LLM)
    stopped: str | None = None
    cost_usd: float = 0.0
    new_entities: int = 0
    mentions: int = 0
    relations: int = 0
    dropped: int = 0           # names and relations the resolver threw away
    judge_calls: int = 0
    merges: int = 0
    warnings: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def system_prompt() -> str:
    return (load_prompt(PROMPT_VERSION).replace("{{TECHNIQUES}}", tx.render(tx.TECHNIQUES))
            .replace("{{PROBLEMS}}", tx.render(tx.PROBLEMS)))


def item_message(item, tags, max_chars=6000) -> str:
    keys = (tags.get("domains") or []) + (tags.get("problem_types") or []) + (tags.get("techniques") or [])
    labels = ", ".join(f"{k} {tx.label(k)}" for k in keys) or "none"
    text = (item.text or "").strip() or "(no text: title only)"
    return (f"Item to extract\ntitle: {item.title}\nsource: {item.source}\npublished: {item.published_at or '?'}\n"
            f"url host: {urlsplit(item.url or '').netloc or '?'}\ntriage categories: {labels}\n"
            f"text:\n<<<\n{text[:max_chars]}\n>>>")


def messages_for(item, tags, system=None, max_chars=6000) -> list:
    return [{"role": "system", "content": system or system_prompt()},
            {"role": "user", "content": item_message(item, tags, max_chars)}]


def _budget_cap(store, gateway, now):
    if store is None or gateway is None or getattr(gateway, "budget_day", None) is None:
        return None
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    room = 0.8 * gateway.budget_day - store.llm_cost_since(day_start)
    per_item = store.avg_llm_cost("extract") or DEFAULT_COST_PER_ITEM
    return max(0, int(room / per_item))


def run_extraction(store, run_id, gateway, resolver, limit=None, concurrency=4, now=None,
                   max_chars=6000) -> ExtractionStats:
    now = now or datetime.now(timezone.utc)
    stats = ExtractionStats()
    rows = store.extraction_candidates(limit=limit)
    stats.candidates = len(rows)
    if gateway is None or not rows:
        stats.deferred = len(rows)
        return stats
    cap = _budget_cap(store, gateway, now)
    if cap is not None and cap < len(rows):
        stats.deferred += len(rows) - cap
        stats.stopped = f"orçamento: {cap} de {len(rows)} itens extraídos neste run"
        rows = rows[:cap]

    system = system_prompt()
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = {}
        for row in rows:
            item, tags = from_row(row), json.loads(row["tags_json"] or "{}")
            futures[pool.submit(gateway.structured_call, "extract", messages_for(item, tags, system, max_chars),
                                Extraction)] = row
        for future in as_completed(futures):
            row = futures[future]
            if future.cancelled():
                stats.deferred += 1
                continue
            try:
                res = future.result()
            except (BudgetExceeded, InsufficientCredits) as exc:
                stats.stopped = str(exc)
                stats.deferred += 1
                for pending in futures:
                    pending.cancel()
                continue
            except LLMFailure as exc:
                store.record_extraction(row["id"], run_id, "error", prompt_version=PROMPT_VERSION, error=str(exc)[:300])
                stats.errors += 1
                continue
            stats.cost_usd += res.cost_usd
            payload = res.output.model_dump()
            try:
                outcome = resolver.apply(row, res.output) if resolver is not None else None
            except Exception as exc:  # noqa: BLE001 - one item must not stop the others; retried next run
                log.exception("resolve %s", row["id"])
                store.record_extraction(row["id"], run_id, "error", model=res.model, prompt_version=PROMPT_VERSION,
                                        payload=payload, error=f"resolve: {exc}"[:300], cost_usd=res.cost_usd)
                stats.errors += 1
                continue
            store.record_extraction(row["id"], run_id, "ok", model=res.model, prompt_version=PROMPT_VERSION,
                                    payload=payload, cost_usd=res.cost_usd)
            stats.extracted += 1
            for name in OUTCOME_FIELDS:
                setattr(stats, name, getattr(stats, name) + getattr(outcome, name, 0))
    log.info("extract %s", stats.as_dict())
    return stats
