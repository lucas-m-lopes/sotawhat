# sotawhat/evals/metrics.py
"""The SDD goals measured from the store (P6, §2.1 G1–G4, §12), with no LLM call.

- G1 · runs: share of daily runs that finished, sources failing 3 runs or more in a row;
- G2 · noise: digest sizes (from the Telegram deliveries) and precision by your votes: an item you marked
  👍 or 🧪 counts as relevant, 👎 as noise; only the latest vote of an item counts;
- G3 · graph: extraction precision from the annotated sample (`sotawhat eval extract`) and query latency;
- G4 · ideas: finalists per run and the share you marked 👍 explorar, 🧪 testar or 🛠️ construí, by lens,
  sampler and generator family.
Every rate comes with its count, so a 100% out of 2 votes is never mistaken for a result."""
import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sotawhat.store.db import APPROVED

POSITIVE, NEGATIVE = ("up", "test"), ("down",)
IDEA_POSITIVE = ("curtida", "testar", "construida")
IDEA_DECIDED = IDEA_POSITIVE + ("rejeitada", "engavetada")
GOALS = {"G1": 0.95, "G2": 0.80, "G3": 0.85, "G4": 0.30}


def _since(now, days) -> str:
    return ((now or datetime.now(timezone.utc)) - timedelta(days=days)).isoformat(timespec="seconds")


def rate(hits, total):
    return round(hits / total, 3) if total else None


def run_health(store, now=None, days=30) -> dict:
    rows = store.conn.execute("SELECT ok FROM runs WHERE kind = 'daily' AND started_at >= ? AND finished_at IS NOT NULL",
                              (_since(now, days),)).fetchall()
    failing = [dict(name=r["source"], failures=r["consecutive_failures"], error=(r["last_error"] or "")[:120])
               for r in store.source_states() if (r["consecutive_failures"] or 0) >= 3]
    ok = sum(1 for r in rows if r["ok"])
    return {"runs": len(rows), "ok": ok, "rate": rate(ok, len(rows)), "failing_sources": failing}


def latest_item_votes(store) -> dict:
    """item id -> its latest vote."""
    return dict(store.conn.execute(
        "SELECT f.target_id, f.value FROM feedback f JOIN (SELECT target_id, MAX(id) AS id FROM feedback "
        "WHERE target_type = 'item' GROUP BY target_id) last ON last.id = f.id").fetchall())


def triage_by_votes(store) -> dict:
    """-> {"table": {decision: {vote: n}}, "precision": {section: (rate, n)}, "votes": n, "delivered": (rate, n)}."""
    votes = latest_item_votes(store)
    decisions = dict(store.conn.execute(
        f"SELECT item_id, decision FROM triage WHERE item_id IN ({','.join('?' * len(votes))})", list(votes)).fetchall()) \
        if votes else {}
    table = defaultdict(Counter)
    for item_id, vote in votes.items():
        table[decisions.get(item_id, "sem triagem")][vote] += 1
    precision, empty = {}, Counter()        # .get(): reading a defaultdict would add rows of zeros to the table
    for section in APPROVED:
        counts = table.get(section, empty)
        good, bad = sum(counts[v] for v in POSITIVE), sum(counts[v] for v in NEGATIVE)
        precision[section] = (rate(good, good + bad), good + bad)
    good = sum(table.get(s, empty)[v] for s in ("main", "frontier") for v in POSITIVE)
    bad = sum(table.get(s, empty)[v] for s in ("main", "frontier") for v in NEGATIVE)
    return {"table": {k: dict(v) for k, v in table.items()}, "precision": precision, "votes": len(votes),
            "delivered": (rate(good, good + bad), good + bad)}


def digest_sizes(store, now=None, days=30) -> dict:
    """Items per digest and section, from what was actually delivered on Telegram."""
    per_day = defaultdict(Counter)
    for day, section, n in store.conn.execute(
            "SELECT day, section, COUNT(*) FROM deliveries WHERE section IN ('main', 'frontier', 'radar') AND day >= ? "
            "GROUP BY day, section", (_since(now, days)[:10],)):
        per_day[day][section] = n
    return {"digests": len(per_day), **{f"max_{s}": max((c[s] for c in per_day.values()), default=0)
                                        for s in ("main", "frontier", "radar")},
            **{f"avg_{s}": round(sum(c[s] for c in per_day.values()) / len(per_day), 1) if per_day else 0.0
               for s in ("main", "frontier", "radar")}}


def query_latency(store) -> dict:
    """Milliseconds of the two queries the interface and the MCP make most."""
    from sotawhat.graph import query as q

    out = {}
    for name, call in (("grafo 30 dias", lambda: q.graph_view(store, days=30, limit=250)),
                       ("busca", lambda: q.search(store, "model"))):
        start = time.perf_counter()
        call()
        out[name] = round((time.perf_counter() - start) * 1000)
    return out


def ideas_metrics(store, now=None, days=90) -> dict:
    rows = store.conn.execute(
        "SELECT i.*, r.kind FROM ideas i JOIN runs r ON r.id = i.run_id WHERE i.selected = 1 AND i.created_at >= ?",
        (_since(now, days),)).fetchall()
    runs = Counter(r["run_id"] for r in rows)
    weekly = [n for run, n in runs.items() if any(r["run_id"] == run and r["kind"] == "weekly" for r in rows)]
    decided = [r for r in rows if r["status"] in IDEA_DECIDED]
    positive = [r for r in decided if r["status"] in IDEA_POSITIVE]

    def by(key):
        groups = defaultdict(lambda: [0, 0])
        for r in decided:
            groups[key(r)][1] += 1
            groups[key(r)][0] += r["status"] in IDEA_POSITIVE
        return {k: (rate(good, total), total) for k, (good, total) in sorted(groups.items())}

    def family(r):
        return ((json.loads(r["card_json"]).get("model") or "?").split("/")[0])

    def sampler(r):
        return json.loads(r["candidate_json"] or "{}").get("sampler", "?")

    return {"finalists": len(rows), "runs": len(runs), "weekly_runs": len(weekly),
            "per_weekly_run": round(sum(weekly) / len(weekly), 1) if weekly else None,
            "decided": len(decided), "explore": (rate(len(positive), len(decided)), len(decided)),
            "status": dict(Counter(r["status"] for r in rows)),
            "by_lens": by(lambda r: r["lens"] or "?"), "by_sampler": by(sampler), "by_family": by(family)}


def extraction_precision(path) -> dict | None:
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def month_costs(store, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    rows = store.conn.execute("SELECT task, COUNT(*), COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE created_at >= ? "
                              "GROUP BY task ORDER BY 3 DESC", (start,)).fetchall()
    return {"total": round(sum(r[2] for r in rows), 4), "by_task": {r[0]: (r[1], round(r[2], 4)) for r in rows}}


def goals(store, now=None, extract_summary=None) -> dict:
    return {"day": (now or datetime.now(timezone.utc)).date().isoformat(), "g1": run_health(store, now),
            "g2": {**triage_by_votes(store), "sizes": digest_sizes(store, now)},
            "g3": {"extraction": extraction_precision(extract_summary) if extract_summary else None,
                   "latency_ms": query_latency(store)},
            "g4": ideas_metrics(store, now), "costs": month_costs(store, now)}


def _pct(value) -> str:
    return "—" if value is None else f"{value * 100:.0f}%".replace(".", ",")


def _status(value, goal, n, minimum) -> str:
    if value is None or n < minimum:
        return f"⏳ poucos dados (n={n})"
    return "✅" if value >= goal else "⚠️"


def render_goals(g) -> str:
    g1, g2, g3, g4 = g["g1"], g["g2"], g["g3"], g["g4"]
    sizes = g2["sizes"]
    precision, n_votes = g2["delivered"]
    extraction = g3["extraction"]
    ext_value = extraction["entities"]["precision"] if extraction else None
    ext_n = extraction["entities"]["total"] if extraction else 0
    explore, n_ideas = g4["explore"]
    lines = [f"# sotawhat · metas do SDD · {g['day']}", "",
             "| Meta | Critério | Medido | Situação |", "|---|---|---|---|",
             f"| G1 · ingestão | ≥ 95% dos runs diários concluem | {_pct(g1['rate'])} de {g1['runs']} runs (30 dias) | "
             f"{_status(g1['rate'], GOALS['G1'], g1['runs'], 7)} |",
             f"| G2 · ruído | ≤ 10 + 5 itens e ≤ 10 no radar; precisão ≥ 80% pelos votos | máx. {sizes['max_main']} + "
             f"{sizes['max_frontier']} e {sizes['max_radar']} no radar; precisão {_pct(precision)} em {n_votes} votos | "
             f"{_status(precision, GOALS['G2'], n_votes, 30)} |",
             f"| G3 · grafo | entidades com precisão ≥ 85%; consultas < 2 s | "
             f"{_pct(ext_value)} em {ext_n} entidades anotadas; "
             + ", ".join(f"{k} {v} ms" for k, v in g3["latency_ms"].items())
             + f" | {_status(ext_value, GOALS['G3'], ext_n, 40) if extraction else '⏳ falta anotar (sotawhat eval extract)'} |",
             f"| G4 · ideias | 5–10 por semana; ≥ 30% \"vale explorar\" | {g4['per_weekly_run'] or '—'} por run semanal; "
             f"{_pct(explore)} de {n_ideas} decididas | {_status(explore, GOALS['G4'], n_ideas, 10)} |", ""]
    if g1["failing_sources"]:
        lines += ["## Fontes falhando há 3 runs ou mais", ""] + [
            f"- {s['name']}: {s['failures']} seguidas · {s['error']}" for s in g1["failing_sources"]] + [""]
    lines += ["## Votos × decisão da triagem", "", "| Decisão | 👍 | 🧪 | 👎 | precisão |", "|---|---|---|---|---|"]
    for decision, counts in sorted(g2["table"].items()):
        value, n = g2["precision"].get(decision, (None, 0))
        lines.append(f"| {decision} | {counts.get('up', 0)} | {counts.get('test', 0)} | {counts.get('down', 0)} | "
                     f"{_pct(value) if decision in APPROVED else '—'} |")
    if g4["decided"]:
        lines += ["", "## Ideias decididas, por lente, amostrador e família do gerador", ""]
        for title, key in (("Lente", "by_lens"), ("Amostrador", "by_sampler"), ("Família", "by_family")):
            lines.append(f"- **{title}:** " + "; ".join(f"{k} {_pct(v)} de {n}" for k, (v, n) in g4[key].items()))
    costs = g["costs"]
    lines += ["", f"## Custo de LLM no mês: US$ {costs['total']:.4f}".replace(".", ","), ""]
    lines += [f"- {task}: {n} chamadas, US$ {cost:.4f}".replace(".", ",") for task, (n, cost) in costs["by_task"].items()]
    return "\n".join(lines) + "\n"
