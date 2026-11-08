# sotawhat/pipeline/triage.py
"""Two-stage triage (SDD §6.7).

Stage A, no LLM: mute filters, same-story dedup (near-identical titles), local embeddings, novelty (D)
and, once a profile has enough votes, the classifier gate. Stage B: the LLM rubric with strict JSON for
the survivors, concurrently, within 80% of what is left of the daily budget. Items that do not fit stay
undecided and are retried by the next runs for `backlog_days`.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import numpy as np

from sotawhat import taxonomy as tx
from sotawhat.items import from_row
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import TriageOutput
from sotawhat.pipeline.dedup import find_duplicates
from sotawhat.store.vectors import item_text, novelty_scores

PROMPT_VERSION = "triage_v1"
HARD_REJECT = {"clinical_without_ai", "marketing_no_substance", "identifiable_patient_data"}
DEFAULT_COST_PER_ITEM = 0.001   # US$, until the ledger has real triage calls (≈ 0.0005 expected)
log = logging.getLogger("sotawhat.triage")


@dataclass
class TriageStats:
    candidates: int = 0
    muted: int = 0
    duplicates: int = 0
    gated: int = 0
    deferred: int = 0      # left for the next run (budget cap, stop, no LLM)
    triaged: int = 0
    main: int = 0
    radar: int = 0
    rejected: int = 0
    errors: int = 0
    llm: bool = True
    stopped: str | None = None
    cost_usd: float = 0.0
    warnings: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def system_prompt() -> str:
    text = load_prompt(PROMPT_VERSION)
    for token, table in {"DOMAINS": tx.DOMAINS, "PROBLEMS": tx.PROBLEMS, "TECHNIQUES": tx.TECHNIQUES,
                         "EVIDENCE": tx.EVIDENCE, "STAKEHOLDERS": tx.STAKEHOLDERS, "BR": tx.BR_APPLICABILITY,
                         "CFM": tx.CFM_RISK, "AUDIENCE": tx.AUDIENCE}.items():
        text = text.replace("{{" + token + "}}", tx.render(table))
    return text


def item_message(item, max_chars=8000) -> str:
    text = (item.text or "").strip() or "(sem texto: só o título)"
    authors = ", ".join(item.authors[:3]) + (" et al." if len(item.authors) > 3 else "")
    return (f"Item to triage\ntitle: {item.title}\nsource: {item.source} (profile {item.profile or '?'})\n"
            f"published: {item.published_at or '?'}\nurl host: {urlsplit(item.url or '').netloc or '?'}\n"
            f"authors: {authors or '?'}\ntext:\n<<<\n{text[:max_chars]}\n>>>")


def messages_for(item, rubric, system=None) -> list:
    return [{"role": "system", "content": system or system_prompt()},
            {"role": "user", "content": item_message(item, rubric.max_text_chars)}]


def decide(out, novelty, rubric, source) -> tuple:
    """-> (decision, total). Score and thresholds from the rubric; hard exclusions first; frontier AI
    without a medical bridge (A ≥ radar_min_a, B ≤ radar_max_b) goes to the radar."""
    a, b, c = out.frontier_ai, out.medical_applicability, out.actionability
    w = rubric.weights
    total = w["A"] * a + w["B"] * b + w["C"] * c + w["D"] * novelty
    if out.vendor_only:
        total -= rubric.vendor_only_penalty
    if any(source == s or (s.endswith("*") and source.startswith(s[:-1])) for s in rubric.weak_sources):
        total -= rubric.weak_source_penalty
    total = round(max(total, 0.0), 2)
    radar = a >= rubric.radar_min_a and b <= rubric.radar_max_b
    if out.hard_exclusion in HARD_REJECT:
        return "reject", total
    if out.hard_exclusion == "generic_ai_no_bridge":
        return ("radar" if radar else "reject"), total
    if total >= rubric.min_total and b >= rubric.min_b:
        return "main", total
    return ("radar" if radar else "reject"), total


def _budget_cap(store, gateway, now):
    if store is None or gateway is None or gateway.budget_day is None:
        return None
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    room = 0.8 * gateway.budget_day - store.llm_cost_since(day_start)
    per_item = store.avg_llm_cost("triage") or DEFAULT_COST_PER_ITEM
    return max(0, int(room / per_item))


def _stage_a(store, run_id, items, rubric, mutes, embedder, gates, now, stats):
    survivors = []
    for it in items:
        reason = mutes.match(it)
        if reason:
            store.record_triage(it.id, run_id, "muted", reason=reason)
            stats.muted += 1
        else:
            survivors.append(it)

    window = (now - timedelta(days=rubric.novelty_window_days)).isoformat(timespec="seconds")
    pending = {it.id for it in survivors}
    known = [row for row in store.titles_since(window) if row["id"] not in pending]
    survivors.sort(key=lambda it: -len(it.text or ""))       # the richest copy represents the story
    dups = find_duplicates(survivors, known)
    for it in survivors:
        if it.id in dups:
            store.join_cluster(it.id, dups[it.id])
            store.record_triage(it.id, run_id, "duplicate", reason=f"mesma história que {dups[it.id]}")
            stats.duplicates += 1
    survivors = [it for it in survivors if it.id not in dups]

    novelty, vectors = {}, {}
    if embedder is not None and survivors:
        try:
            have = store.embedded_ids(embedder.name, [it.id for it in survivors])
            missing = [it for it in survivors if it.id not in have]
            if missing:
                texts = [item_text(it.title, it.text) for it in missing]
                store.save_embeddings(embedder.name, zip([it.id for it in missing], embedder.embed(texts)))
            ids, matrix = store.load_embeddings(embedder.name, ids=[it.id for it in survivors])
            _, reference = store.load_embeddings(embedder.name, since_iso=window, exclude=pending)
            novelty = dict(zip(ids, novelty_scores(matrix, reference, rubric.novelty_thresholds)))
            vectors = dict(zip(ids, matrix))
        except Exception as exc:  # noqa: BLE001 - e.g. the model download failed: triage still runs
            log.warning("embeddings: %s", exc)
            stats.warnings.append(f"embeddings indisponíveis ({type(exc).__name__}): D=5 e sem classificador hoje")

    pre, gated = {}, set()
    for profile, gate in (gates or {}).items():
        group = [it for it in survivors if it.profile == profile and it.id in vectors]
        if not group:
            continue
        probs = gate.score(np.stack([vectors[it.id] for it in group]))
        ranked = sorted(zip(group, probs.tolist()), key=lambda pair: -pair[1])
        for rank, (it, p) in enumerate(ranked):
            pre[it.id] = (p, gate.version)
            if rank >= rubric.classifier_top_n:
                store.record_triage(it.id, run_id, "gated", pre_score=p, classifier_version=gate.version,
                                    reason=f"classificador {gate.version}: p={p:.2f}, "
                                           f"fora do top {rubric.classifier_top_n}")
                gated.add(it.id)
                stats.gated += 1
    survivors = [it for it in survivors if it.id not in gated]
    return survivors, novelty, pre


def run_triage(store, run_id, gateway, rubric, mutes, embedder=None, gates=None, now=None) -> TriageStats:
    now = now or datetime.now(timezone.utc)
    stats = TriageStats(llm=gateway is not None)
    since = (now - timedelta(days=rubric.backlog_days)).isoformat(timespec="seconds")
    items = [from_row(row) for row in store.triage_candidates(since)][:rubric.max_items_per_run]
    stats.candidates = len(items)
    survivors, novelty, pre = _stage_a(store, run_id, items, rubric, mutes, embedder, gates, now, stats)
    if gateway is None:
        stats.deferred = len(survivors)
        return stats

    # medico first, then by classifier score, newest first
    survivors.sort(key=lambda it: (it.profile != "medico", -(pre.get(it.id, (0.5,))[0])))
    cap = _budget_cap(store, gateway, now)
    if cap is not None and cap < len(survivors):
        stats.deferred += len(survivors) - cap
        stats.stopped = f"orçamento: {cap} de {len(survivors)} itens triados neste run"
        survivors = survivors[:cap]

    system = system_prompt()
    with ThreadPoolExecutor(max_workers=max(1, rubric.concurrency)) as pool:
        futures = {pool.submit(gateway.structured_call, "triage", messages_for(it, rubric, system),
                               TriageOutput): it for it in survivors}
        for future in as_completed(futures):
            it = futures[future]
            if future.cancelled():
                stats.deferred += 1
                continue
            try:
                res = future.result()
            except (BudgetExceeded, InsufficientCredits) as exc:
                stats.stopped = str(exc)
                stats.deferred += 1
                for pending_future in futures:
                    pending_future.cancel()
                continue
            except LLMFailure as exc:
                store.record_triage(it.id, run_id, "error", reason=str(exc)[:300], prompt_version=PROMPT_VERSION)
                stats.errors += 1
                continue
            out = res.output
            decision, total = decide(out, novelty.get(it.id, 5), rubric, it.source)
            p, version = pre.get(it.id, (None, None))
            store.record_triage(
                it.id, run_id, decision, total=total, reason=out.reason_pt, summary_pt=out.summary_pt,
                why_it_matters_pt=out.why_it_matters_pt if decision != "reject" else "",
                scores={"A": out.frontier_ai, "B": out.medical_applicability, "C": out.actionability,
                        "D": novelty.get(it.id, 5)},
                tags=out.tags(), pre_score=p, classifier_version=version, model=res.model,
                prompt_version=PROMPT_VERSION, cost_usd=res.cost_usd)
            if out.hard_exclusion == "identifiable_patient_data":
                store.redact_item(it.id)
            stats.triaged += 1
            stats.cost_usd += res.cost_usd
            if decision == "main":
                stats.main += 1
            elif decision == "radar":
                stats.radar += 1
            else:
                stats.rejected += 1
    log.info("triage %s", stats.as_dict())
    return stats
