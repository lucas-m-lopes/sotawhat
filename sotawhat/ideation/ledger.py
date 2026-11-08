# sotawhat/ideation/ledger.py
"""Read side of the idea ledger (SDD §8.3 stage 8, §8.5) and of the weekly intelligence, shared by the
weekly report, the interface (/api/ideas, /api/trends) and the MCP tools (list_ideas, trends, gaps)."""
import json

from sotawhat import taxonomy as tx
from sotawhat.graph import intelligence as intel
from sotawhat.graph.query import TYPE_LABELS

STATUSES = ("nova", "curtida", "testar", "engavetada", "construida", "rejeitada", "descartada")
REASONS = ("não interessa", "já existe", "inviável agora", "errado clinicamente", "fora do foco")   # SDD §8.3, 8


def _json(text, default):
    try:
        return json.loads(text) if text else default
    except ValueError:
        return default


def idea_card(row, neighbors_per_layer=3) -> dict:
    """Everything a reader needs about one idea, from its ledger row."""
    card = _json(row["card_json"], {})
    scores = _json(row["scores_json"], {})
    novelty = _json(row["novelty_json"], {})
    critique = _json(row["critique_json"], {})
    layers = novelty.get("camadas") or {}
    candidate = _json(row["candidate_json"], {})
    return {"id": row["id"], "version": row["version"], "parent_id": row["parent_id"], "run_id": row["run_id"],
            "created_at": row["created_at"], "title": row["title"], "lens": row["lens"], "persona": row["persona"],
            "niche": row["niche"], "status": row["status"], "selected": bool(row["selected"]),
            "score": row["score"] or 0.0, "discard_reason": row["discard_reason"], "draft": card.get("draft", {}),
            "sector_label": tx.label(card.get("draft", {}).get("setor", "")),
            "model": card.get("model"), "dossie": card.get("dossie"), "axes": scores.get("eixos", {}),
            "gates": scores.get("gates", []), "disputed_gates": scores.get("gates_em_disputa", []),
            "confidence": scores.get("confianca"),
            "justifications": scores.get("justificativas", []), "facets": novelty.get("facetas", {}),
            "novelty": novelty.get("nota"),
            "neighbors": {k: v[:neighbors_per_layer] for k, v in layers.items() if not k.startswith("_") and v},
            "unverified": layers.get("_nao_verificado", []), "critiques": critique.get("criticas", []),
            "pre_mortem": critique.get("pre_mortem"), "nasss": critique.get("nasss_complexos"),
            "kill": sorted({k for c in critique.get("criticas", []) for k in c.get("kill_criteria", [])})[:6],
            "candidate": {k: v for k, v in candidate.items() if k != "context"}}


def idea_detail(store, idea_id) -> dict | None:
    """The card with every prior-art neighbor, the graph facts the generator saw and the vote history."""
    row = store.get_idea(idea_id)
    if row is None:
        return None
    detail = idea_card(row, neighbors_per_layer=10)
    detail["context"] = (_json(row["candidate_json"], {}).get("context") or [])[:30]
    detail["votes"] = [dict(r) for r in store.conn.execute(
        "SELECT value, note, channel, created_at FROM feedback WHERE target_type = 'idea' AND target_id = ? "
        "ORDER BY id DESC", (str(idea_id),))]
    return detail


def list_ideas(store, status=None, finalists_only=True, limit=100) -> dict:
    """Newest batch first, best score first inside a batch; the counts per status cover the same scope."""
    where, args = ["1 = 1"], []
    if finalists_only:
        where.append("selected = 1")
    scope = " AND ".join(where)
    counts = dict(store.conn.execute(f"SELECT status, COUNT(*) FROM ideas WHERE {scope} GROUP BY status", args).fetchall())
    if status:
        where.append("status = ?")
        args.append(status)
    rows = store.conn.execute(f"SELECT * FROM ideas WHERE {' AND '.join(where)} "
                              "ORDER BY run_id DESC, COALESCE(score, 0) DESC, id DESC LIMIT ?", args + [limit]).fetchall()
    return {"ideas": [idea_card(r) for r in rows], "counts": counts, "total": sum(counts.values()),
            "reasons": list(REASONS)}


def _members(store, run_id, community, limit=8) -> list:
    return [{"entity_id": r["id"], "name": r["name"], "type": r["type"], "type_label": TYPE_LABELS.get(r["type"], r["type"]),
             "mentions": r["mention_count"]} for r in store.conn.execute(
        "SELECT e.id, e.name, e.type, e.mention_count FROM entity_communities ec JOIN entities e ON e.id = ec.entity_id "
        "WHERE ec.run_id = ? AND ec.community = ? ORDER BY e.mention_count DESC, e.name LIMIT ?",
        (run_id, community, limit))]


def gap_pair(gap) -> dict:
    keep = ("technique_id", "technique", "technique_type", "problem_id", "problem", "sampler", "score", "why_now")
    return {k: gap[k] for k in keep if k in gap}


def compact(card) -> dict:
    """A short card for the MCP tools (the model reads it): no prior-art lists, critiques or dossier text."""
    d = card["draft"]
    return {"id": card["id"], "title": card["title"], "status": card["status"], "score": card["score"],
            "finalist": card["selected"], "run_id": card["run_id"], "lens": card["lens"], "niche": card["niche"],
            "problem": d.get("problema_jtbd"), "owner": d.get("stakeholder_dono"), "mechanism": d.get("mecanismo"),
            "why_now": d.get("why_now"), "null_hypothesis": d.get("hipotese_nula"),
            "technique": card["candidate"].get("technique"), "target_problem": card["candidate"].get("problem"),
            "novelty_facets": {k: v.get("estado") for k, v in card["facets"].items()},
            "pilot_90d": (card["dossie"] or {}).get("piloto_90d"), "discard_reason": card["discard_reason"],
            "disputed_gates": card["disputed_gates"]}


def trends_view(store, now=None, gaps_limit=8) -> dict:
    """Live trends and gaps (cheap: NetworkX over the approved window) plus the communities, with their
    labels, stored by the last weekly run; without one, the live communities with their main names."""
    trends = [t | {"type_label": TYPE_LABELS.get(t["type"], t["type"])} for t in intel.trends(store, now=now)]
    graph = intel.build_graph(store, now=now)
    groups = intel.communities(store, now=now, graph=graph)
    found = intel.gaps(store, now=now, graph=graph, groups=groups, limit=gaps_limit)
    stored = store.latest_communities()
    if stored:
        communities = [{"community": r["community"], "label": r["label"], "summary": r["summary"], "size": r["size"],
                        "members": _members(store, r["run_id"], r["community"]), "run_id": r["run_id"]} for r in stored]
    else:
        communities = [{"community": g["community"], "label": " · ".join(n for _, n, _ in g["top"][:3]), "summary": "",
                        "size": g["size"], "run_id": None,
                        "members": [{"entity_id": i, "name": n, "type": t, "type_label": TYPE_LABELS.get(t, t)}
                                    for i, n, t in g["top"]]} for g in groups]
    weekly = store.latest_weekly_report(kind="weekly")
    return {"trends": trends, "communities": communities[:12],
            "gaps": {name: [gap_pair(g) for g in pairs] for name, pairs in found.items()},
            "weekly": {"day": weekly["day"], "run_id": weekly["run_id"], "stats": weekly["payload"].get("stats", {}),
                       "ideas": len(weekly["payload"].get("ideas", []))} if weekly else None,
            "rules": _json(store.meta_get("ideation_rules", "[]"), [])}
