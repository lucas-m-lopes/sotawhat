# sotawhat/evals/bakeoff.py
"""`sotawhat eval models` (SDD §6.6, §12, D15): the golden set through each candidate model, one model
at a time and without fallbacks, against your labels. Compares agreement (F1 of "incluir", accuracy over
the 3 labels), valid JSON on the first try, failures, latency and real cost; writes a report to
data/evals/ and, with --apply, puts the winner first in config/llm.yaml."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from sotawhat.evals.golden import as_item
from sotawhat.llm.gateway import LLMFailure
from sotawhat.llm.schemas import TriageOutput
from sotawhat.pipeline.triage import decide, messages_for, system_prompt

LABEL_PT = {"main": "incluir", "radar": "radar", "reject": "excluir"}


@dataclass
class Outcome:
    item_id: str
    label: str
    predicted: str | None      # in label space (main = incluir: "IA ∩ Saúde" or "Fronteira de IA"); None = failed
    first_try_valid: bool
    latency_ms: int
    summary: str = ""
    why: str = ""
    error: str | None = None
    decision: str | None = None                      # the triage decision itself: main | frontier | radar | reject
    scores: dict = field(default_factory=dict)       # A, B, C, S (substance), X (exclusion), V (vendor only)


def evaluate_model(gateway, golden, rubric, model, concurrency=4) -> list:
    system = system_prompt()

    def one(entry):
        item = as_item(entry)
        try:
            res = gateway.structured_call("triage", messages_for(item, rubric, system), TriageOutput, models=(model,))
        except LLMFailure as exc:
            return Outcome(entry["id"], entry["label"], None, False, 0, error=str(exc)[:200])
        out = res.output
        decision, _ = decide(out, 5, rubric, item.source)   # golden items are judged as new (D = 5)
        scores = {"A": out.frontier_ai, "B": out.medical_applicability, "C": out.actionability,
                  "S": out.substance, "X": out.hard_exclusion, "V": out.vendor_only}
        return Outcome(entry["id"], entry["label"], "main" if decision == "frontier" else decision,
                       res.first_try_valid, res.latency_ms, out.summary_pt, out.why_it_matters_pt,
                       decision=decision, scores=scores)

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        return list(pool.map(one, golden))


def metrics(outcomes) -> dict:
    n = len(outcomes) or 1
    tp = sum(o.predicted == "main" and o.label == "main" for o in outcomes)
    fp = sum(o.predicted == "main" and o.label != "main" for o in outcomes)
    fn = sum(o.predicted != "main" and o.label == "main" for o in outcomes)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    latencies = sorted(o.latency_ms for o in outcomes if o.predicted is not None)

    def pct(q):
        return latencies[min(len(latencies) - 1, int(q * len(latencies)))] if latencies else 0

    confusion = {}
    for o in outcomes:
        row = confusion.setdefault(o.label, {})
        row[o.predicted or "falha"] = row.get(o.predicted or "falha", 0) + 1
    return {"n": len(outcomes), "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "precision": precision, "recall": recall,
            "accuracy": sum(o.predicted == o.label for o in outcomes) / n,
            "valid_first_try": sum(o.first_try_valid for o in outcomes) / n,
            "failures": sum(o.predicted is None for o in outcomes),
            "p50_ms": pct(0.5), "p95_ms": pct(0.95), "confusion": confusion}


def model_costs(store, run_id) -> dict:
    rows = store.conn.execute("SELECT requested_model, COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE run_id = ?"
                              " GROUP BY requested_model", (run_id,)).fetchall()
    return {r[0]: r[1] for r in rows}


def pick_winner(results, min_valid=0.9, max_failure_rate=0.05):
    """Best F1 among models with enough valid JSON and few failures; ties broken by accuracy, then cost."""
    eligible = [(m, r) for m, r in results.items()
                if r["valid_first_try"] >= min_valid and r["failures"] <= max_failure_rate * r["n"]]
    if not eligible:
        return None
    return max(eligible, key=lambda mr: (round(mr[1]["f1"], 3), round(mr[1]["accuracy"], 3),
                                         -mr[1].get("cost_usd", 0.0)))[0]


def ranking(results, winner) -> list:
    rest = sorted((m for m in results if m != winner), key=lambda m: (-results[m]["f1"], results[m].get("cost_usd", 0)))
    return ([winner] if winner else []) + rest


def render_report(task, day, results, outcomes, golden, winner) -> str:
    def pct(x):
        return f"{100 * x:.0f}%"

    labels = {lab: sum(1 for g in golden if g["label"] == lab) for lab in LABEL_PT}
    out = [f"# Bake-off · {task} · {day}", "",
           f"Golden set: {len(golden)} itens rotulados (incluir {labels['main']} · radar {labels['radar']} · "
           f"excluir {labels['reject']}). Cada modelo roda sozinho, sem fallback, com o prompt e a rubrica atuais.",
           "", "| Modelo | F1 incluir | Precisão | Recall | Acurácia (3 rótulos) | JSON válido de 1ª | Falhas | "
               "Custo total | Custo/item | p50 | p95 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, r in sorted(results.items(), key=lambda mr: -mr[1]["f1"]):
        per_item = r.get("cost_usd", 0.0) / max(1, r["n"])
        out.append(f"| {'**' + m + '**' if m == winner else m} | {r['f1']:.2f} | {pct(r['precision'])} | "
                   f"{pct(r['recall'])} | {pct(r['accuracy'])} | {pct(r['valid_first_try'])} | {r['failures']} | "
                   f"US$ {r.get('cost_usd', 0.0):.4f} | US$ {per_item:.5f} | {r['p50_ms'] / 1000:.1f} s | "
                   f"{r['p95_ms'] / 1000:.1f} s |")
    out += ["", f"**Vencedor:** {winner or 'nenhum modelo passou nos critérios (JSON válido ≥ 90%, falhas ≤ 5%)'}.",
            "Critério: maior F1 de \"incluir\"; desempate por acurácia e depois custo.", ""]
    out += ["## Matrizes de confusão (linha = seu rótulo, coluna = decisão do modelo)", ""]
    for m, r in results.items():
        cols = ["main", "radar", "reject", "falha"]
        out += [f"**{m}**", "", "| | " + " | ".join(LABEL_PT.get(c, c) for c in cols) + " |",
                "|---|" + "---|" * len(cols)]
        for lab in ("main", "radar", "reject"):
            row = r["confusion"].get(lab, {})
            out.append(f"| {LABEL_PT[lab]} | " + " | ".join(str(row.get(c, 0)) for c in cols) + " |")
        out.append("")
    sample = [g for g in golden if g["label"] == "main"][:5] or golden[:5]
    out += ["## Português: amostra para você julgar", ""]
    for g in sample:
        out += [f"### {g['title']}", ""]
        for m, items in outcomes.items():
            o = next((x for x in items if x.item_id == g["id"]), None)
            if o and o.predicted:
                where = LABEL_PT[o.predicted] + (" · fronteira" if o.decision == "frontier" else "")
                out += [f"- **{m}** ({where}): {o.summary} — *{o.why}*"]
        out.append("")
    return "\n".join(out)


def apply_winner(path, task, models, reasoning, max_tokens) -> None:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = data or {}
    data.setdefault("tasks", {})[task] = {"models": list(models), "reasoning": reasoning, "max_tokens": max_tokens}
    header = ("# config/llm.yaml — modelos por etapa (SDD §6.6). Reescrito por `sotawhat eval models --apply`;\n"
              "# o relatório que justificou a ordem está em data/evals/. SOTAWHAT_MODEL_<ETAPA> ainda vence.\n")
    path.write_text(header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
