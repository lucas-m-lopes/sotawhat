# sotawhat/evals/calibrate.py
"""`sotawhat calibrate [--apply]` (P6, SDD §6.7, §8.4, G2 and G4): proposals from your decisions. Nothing
changes without --apply, and nothing is proposed without enough data.

- Triage cut-offs (needs 100 item votes): for "IA ∩ Saúde" and "Fronteira de IA", the lowest total at
  which the delivered items reach 80% precision by your votes (👍/🧪 relevant, 👎 noise). Only delivered
  items have votes, so a cut-off can only go up; lowering one needs the golden set (`sotawhat eval models`).
- Idea rubric weights (needs 30 decided finalists): each axis weighs by how much it separates the ideas you
  marked 👍 explorar, 🧪 testar or 🛠️ construí from the ones you rejected or archived (correlation, negatives
  at zero), blended half and half with the current weights."""
import json
import re
from datetime import date
from pathlib import Path

from sotawhat.configfiles import read_yaml
from sotawhat.evals.metrics import IDEA_DECIDED, IDEA_POSITIVE, NEGATIVE, POSITIVE, latest_item_votes

MIN_ITEM_VOTES = 100
MIN_IDEA_DECISIONS = 30
GOAL = 0.80


def cutoff(pairs, current, goal=GOAL, min_n=10) -> dict:
    """pairs: [(total, relevant)] of delivered items -> {"current", "proposed", "precision", "n"}."""
    def at(t):
        above = [ok for total, ok in pairs if total >= t]
        return (sum(above) / len(above), len(above)) if above else (None, 0)

    now_precision, n = at(current)
    out = {"current": current, "proposed": current, "precision": now_precision, "n": n}
    if now_precision is None or now_precision >= goal:
        return out
    for t in sorted({total for total, _ in pairs if total > current}):
        value, count = at(t)
        if count < min_n:
            break
        if value >= goal:
            return {**out, "proposed": round(t, 2), "precision_proposed": round(value, 3), "n_proposed": count}
    return out


def triage_proposal(store, rubric) -> dict:
    votes = latest_item_votes(store)
    useful = {k: v for k, v in votes.items() if v in POSITIVE + NEGATIVE}
    if len(useful) < MIN_ITEM_VOTES:
        return {"ok": False, "votes": len(useful), "missing": MIN_ITEM_VOTES - len(useful)}
    rows = store.conn.execute(f"SELECT item_id, decision, total FROM triage WHERE total IS NOT NULL AND item_id IN "
                              f"({','.join('?' * len(useful))})", list(useful)).fetchall()
    pairs = {s: [(r["total"], useful[r["item_id"]] in POSITIVE) for r in rows if r["decision"] == s]
             for s in ("main", "frontier")}
    return {"ok": True, "votes": len(useful), "main": cutoff(pairs["main"], rubric.min_total),
            "frontier": cutoff(pairs["frontier"], rubric.frontier_min_total)}


def _corr(xs, ys) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    return 0.0 if not sx or not sy else sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def weights_proposal(store, current) -> dict:
    rows = store.conn.execute(f"SELECT status, scores_json FROM ideas WHERE selected = 1 AND scores_json IS NOT NULL "
                              f"AND status IN ({','.join('?' * len(IDEA_DECIDED))})", list(IDEA_DECIDED)).fetchall()
    if len(rows) < MIN_IDEA_DECISIONS:
        return {"ok": False, "decisions": len(rows), "missing": MIN_IDEA_DECISIONS - len(rows)}
    labels = [1.0 if r["status"] in IDEA_POSITIVE else 0.0 for r in rows]
    axes = [json.loads(r["scores_json"]).get("eixos", {}) for r in rows]
    signal = {axis: max(0.0, _corr([float(a.get(axis, 0)) for a in axes], labels)) for axis in current}
    if not sum(signal.values()):
        return {"ok": True, "decisions": len(rows), "signal": signal, "proposed": dict(current)}
    blended = {k: 0.5 * current[k] + 0.5 * signal[k] / sum(signal.values()) for k in current}
    proposed = {k: round(v, 2) for k, v in blended.items()}
    top = max(proposed, key=proposed.get)                    # the rounding drift goes to the largest weight
    proposed[top] = round(proposed[top] + 1.0 - sum(proposed.values()), 2)
    return {"ok": True, "decisions": len(rows), "signal": {k: round(v, 3) for k, v in signal.items()}, "proposed": proposed}


def render(triage, weights, day) -> str:
    lines = [f"# sotawhat · proposta de calibração · {day}", ""]
    if not triage["ok"]:
        lines += [f"- **Triagem:** {triage['votes']} votos úteis; faltam {triage['missing']} para propor cortes.", ""]
    else:
        for section, title in (("main", "IA ∩ Saúde"), ("frontier", "Fronteira de IA")):
            c = triage[section]
            now = "—" if c["precision"] is None else f"{c['precision'] * 100:.0f}% em {c['n']} itens"
            change = (f"subir para {c['proposed']} ({c['precision_proposed'] * 100:.0f}% em {c['n_proposed']} itens)"
                      if c["proposed"] != c["current"] else "manter")
            lines.append(f"- **{title}:** corte atual {c['current']} (precisão {now}) → {change}")
        lines.append("")
    if not weights["ok"]:
        lines += [f"- **Pesos das ideias:** {weights['decisions']} finalistas decididas; faltam {weights['missing']}."]
    else:
        lines += ["- **Pesos das ideias** (sinal = correlação com 👍/🧪/🛠️):"]
        lines += [f"  - {k}: {weights['proposed'][k]:.2f} (sinal {weights['signal'][k]:.2f})" for k in weights["proposed"]]
    return "\n".join(lines) + "\n"


def apply_triage(path, triage, day) -> list:
    """Rewrites min_total and frontier_min_total in config/rubric.yaml, keeping every comment."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    changed = []
    for key, section in (("min_total", "main"), ("frontier_min_total", "frontier")):
        c = triage[section]
        if c["proposed"] == c["current"]:
            continue
        pattern = re.compile(rf"^{key}:\s*[0-9.]+.*$", re.M)
        line = f"{key}: {c['proposed']}   # calibrado em {day} com {triage['votes']} votos"
        text = pattern.sub(line, text, count=1) if pattern.search(text) else text.rstrip("\n") + f"\n{line}\n"
        changed.append(key)
    path.write_text(text, encoding="utf-8")
    return changed


def apply_weights(path, weights, day) -> None:
    """Writes `weights` in config/ideation.yaml (created if missing), keeping the other keys."""
    path = Path(path)
    data = read_yaml(path) if path.exists() else {}
    data["weights"] = weights["proposed"]
    body = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in data.items())
    path.write_text(f"# config/ideation.yaml — motor de ideias (SDD §8.4); pesos calibrados em {day} com "
                    f"{weights['decisions']} finalistas decididas.\n{body}\n", encoding="utf-8")


def main_calibrate(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.configfiles import ConfigError, load_config
    from sotawhat.ideation.config import load_ideation
    from sotawhat.store.db import Store

    settings = load_settings()
    try:
        config = load_config(settings.sotawhat_config_dir)
        ideation = load_ideation(settings.sotawhat_config_dir / "ideation.yaml")
    except ConfigError as exc:
        print(f"[config] {exc}")
        return 2
    day = date.today().isoformat()
    with Store(settings.db_path) as store:
        triage = triage_proposal(store, config.rubric)
        weights = weights_proposal(store, ideation.weights)
    text = render(triage, weights, day)
    out = settings.sotawhat_data_dir / "calibration" / f"{day}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text + f"\n[proposta] {out}")
    if not ns.apply:
        print("nada foi alterado: rode com --apply para gravar o que a proposta muda")
        return 0
    if triage["ok"]:
        changed = apply_triage(settings.sotawhat_config_dir / "rubric.yaml", triage, day)
        print(f"[rubric.yaml] {', '.join(changed) or 'sem mudança'}")
    if weights["ok"]:
        apply_weights(settings.sotawhat_config_dir / "ideation.yaml", weights, day)
        load_ideation(settings.sotawhat_config_dir / "ideation.yaml")      # fails loudly if the file became invalid
        print("[ideation.yaml] pesos gravados")
    return 0
