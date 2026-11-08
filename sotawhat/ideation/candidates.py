# sotawhat/ideation/candidates.py
"""Stage 1 of the idea engine (SDD §8.3): technique × problem candidates from three samplers with quotas
(why-now pairs, community bridges, serendipity), a theme filter for `ideate --tema`, ~10% control candidates
without graph context, and a compact dated subgraph (20–50 facts) for every other candidate. Pairs already
used in the last `recent_pair_days` days go to the end of their queue, so every week brings new pairs while
the graph has them."""
import json
import math
import random
from dataclasses import replace
from datetime import timedelta

from sotawhat.graph import intelligence as intel
from sotawhat.store.db import APPROVED

_IN = ",".join("?" * len(APPROVED))


def _matches(candidate, theme) -> bool:
    theme = (theme or "").lower().strip()
    return not theme or theme in candidate["technique"].lower() or theme in candidate["problem"].lower() \
        or theme in candidate.get("context_text", "").lower()


def context(store, technique_id, problem_id, limit=30) -> list:
    """Dated facts about both ends: typed relations and the approved items that mention them."""
    facts = []
    for entity_id in (technique_id, problem_id):
        for row in store.conn.execute(
                "SELECT s.name, r.predicate, o.name, i.title, i.fetched_at FROM entity_relations r "
                "JOIN entities s ON s.id = r.subject_id JOIN entities o ON o.id = r.object_id "
                "JOIN items i ON i.id = r.item_id WHERE (r.subject_id = ? OR r.object_id = ?) "
                "AND r.predicate != 'in_category' ORDER BY i.fetched_at DESC LIMIT ?",
                (entity_id, entity_id, limit)):
            facts.append(f"{row[4][:10]} · {row[0]} —{row[1]}→ {row[2]} (item: {row[3][:120]})")
        for row in store.conn.execute(
                "SELECT i.title, i.fetched_at, t.summary_pt FROM entity_mentions m JOIN items i ON i.id = m.item_id "
                f"JOIN triage t ON t.item_id = i.id WHERE m.entity_id = ? AND t.decision IN ({_IN}) "
                "ORDER BY i.fetched_at DESC LIMIT ?", [entity_id] + list(APPROVED) + [max(3, limit // 4)]):
            facts.append(f"{row[1][:10]} · item: {row[0][:140]} — {(row[2] or '')[:200]}")
    seen, unique = set(), []
    for fact in facts:
        if fact not in seen:
            seen.add(fact)
            unique.append(fact)
    return unique[:limit]


def recent_pairs(store, now, days) -> set:
    """(technique_id, problem_id) of the candidates behind every idea of the last `days` days."""
    if days <= 0:
        return set()
    since = (intel._now(now) - timedelta(days=days)).isoformat(timespec="seconds")
    pairs = set()
    for (text,) in store.conn.execute("SELECT candidate_json FROM ideas WHERE created_at >= ?", (since,)):
        candidate = json.loads(text or "{}")
        if candidate.get("technique_id") is not None:
            pairs.add((candidate["technique_id"], candidate.get("problem_id")))
    return pairs


def _key(candidate) -> tuple:
    return candidate["technique_id"], candidate["problem_id"]


def _pick(found, config, taken) -> list:
    """Each sampler's quota first, then the leftovers in order, up to `config.candidates`; `taken` grows."""
    chosen = []
    for sampler, share in config.quotas.items():
        quota = math.ceil(config.candidates * share)
        for candidate in found.get(sampler, []):
            if quota <= 0:
                break
            if _key(candidate) not in taken:
                taken.add(_key(candidate))
                chosen.append(candidate)
                quota -= 1
    for candidate in (c for pool in found.values() for c in pool):
        if len(chosen) >= config.candidates:
            break
        if _key(candidate) not in taken:
            taken.add(_key(candidate))
            chosen.append(candidate)
    return chosen[:config.candidates]


def sample_candidates(store, config, theme=None, now=None, seed=7) -> list:
    """-> [{technique_id, technique, problem_id, problem, sampler, score, why_now, control, context}]."""
    found = intel.gaps(store, now=now, limit=max(30, config.candidates * 3), seed=seed)
    lately = recent_pairs(store, now, config.recent_pair_days)
    rng = random.Random(seed)
    for pool in found.values():
        for candidate in pool:
            candidate["context"] = context(store, candidate["technique_id"], candidate["problem_id"], config.context_triples)
            candidate["context_text"] = " ".join(candidate["context"])
    if theme:
        found = {name: [c for c in pool if _matches(c, theme)] for name, pool in found.items()}
    taken = set()       # fresh pairs fill the batch first; pairs used lately only complete it
    chosen = _pick({name: [c for c in pool if _key(c) not in lately] for name, pool in found.items()}, config, taken)
    if len(chosen) < config.candidates and lately:
        chosen += _pick({name: [c for c in pool if _key(c) in lately] for name, pool in found.items()},
                        replace(config, candidates=config.candidates - len(chosen)), taken)
    controls = max(1, round(len(chosen) * config.control_share)) if chosen else 0
    for candidate in rng.sample(chosen, controls) if controls else []:
        candidate["control"] = True
        candidate["context"] = []
    for candidate in chosen:
        candidate.setdefault("control", False)
        candidate.pop("context_text", None)
    return chosen
