# sotawhat/graph/query.py
"""Read side of the entity graph (SDD §6.11, D16): what the web interface and the MCP server show.

Only approved items (main, frontier, radar) count. Time windows use `items.fetched_at`, the moment an
item reached the engine (published dates vary in format from source to source). Every query is
parameterized; the IN (...) lists are built from placeholders."""
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sotawhat import taxonomy as tx
from sotawhat.graph.resolve import normalize
from sotawhat.store.db import APPROVED, ROLE_RANK

ENTITY_TYPES = ("technique", "model", "dataset", "organization", "product", "problem", "regulation")
CATEGORY_TYPES = ("domain", "problem_type", "technique_family")
TYPE_LABELS = {"technique": "técnica", "model": "modelo", "dataset": "dataset", "organization": "organização",
               "product": "produto", "problem": "problema", "regulation": "regulação", "domain": "domínio",
               "problem_type": "tipo de problema", "technique_family": "família de técnica"}
RELATION_LABELS = {"uses": "usa", "addresses": "aborda", "developed_by": "desenvolvido por",
                   "evaluated_on": "avaliado em", "compared_with": "comparado com", "builds_on": "baseado em",
                   "regulated_by": "regulado por", "in_category": "na categoria", "co": "aparecem juntos"}
SECTIONS = {"main": "IA ∩ Saúde", "frontier": "Fronteira de IA", "radar": "Radar"}
_APPROVED_SQL = ",".join("?" * len(APPROVED))


def _in(values) -> str:
    return ",".join("?" * len(values))


def _since(days, now=None):
    if not days:
        return None
    return ((now or datetime.now(timezone.utc)) - timedelta(days=int(days))).isoformat(timespec="seconds")


def _category_label(key):
    return tx.label(key) if key else None


def _node(row, count) -> dict:
    return {"id": f"e{row['id']}", "entity_id": row["id"], "label": row["name"], "type": row["type"],
            "type_label": TYPE_LABELS.get(row["type"], row["type"]), "count": count, "mentions": row["mention_count"],
            "first_seen": row["first_seen"], "last_seen": row["last_seen"], "category": row["category"],
            "category_label": _category_label(row["category"])}


def _window_counts(store, types, since):
    sql = ("SELECT e.*, COUNT(DISTINCT m.item_id) AS n FROM entities e JOIN entity_mentions m ON m.entity_id = e.id"
           " JOIN items i ON i.id = m.item_id JOIN triage t ON t.item_id = i.id"
           f" WHERE t.decision IN ({_APPROVED_SQL}) AND e.type IN ({_in(types)})")
    args = list(APPROVED) + list(types)
    if since:
        sql += " AND i.fetched_at >= ?"
        args.append(since)
    sql += " GROUP BY e.id ORDER BY n DESC, e.mention_count DESC, e.name"
    return store.conn.execute(sql, args).fetchall()


def _cooccurrence(store, ids, since, anchor=None):
    """{(a, b): shared items} for pairs inside `ids` (a < b), or the neighbors of `anchor`."""
    sql = ("SELECT a.entity_id, b.entity_id, COUNT(DISTINCT a.item_id) FROM entity_mentions a"
           " JOIN entity_mentions b ON b.item_id = a.item_id AND a.entity_id < b.entity_id"
           " JOIN items i ON i.id = a.item_id JOIN triage t ON t.item_id = a.item_id"
           f" WHERE t.decision IN ({_APPROVED_SQL})")
    args = list(APPROVED)
    if anchor is not None:
        sql += " AND (a.entity_id = ? OR b.entity_id = ?)"
        args += [anchor, anchor]
    else:
        sql += f" AND a.entity_id IN ({_in(ids)}) AND b.entity_id IN ({_in(ids)})"
        args += list(ids) + list(ids)
    if since:
        sql += " AND i.fetched_at >= ?"
        args.append(since)
    sql += " GROUP BY a.entity_id, b.entity_id"
    return {(r[0], r[1]): r[2] for r in store.conn.execute(sql, args).fetchall()}


def _typed(store, ids, since):
    sql = ("SELECT r.subject_id, r.predicate, r.object_id, COUNT(DISTINCT r.item_id) FROM entity_relations r"
           " JOIN items i ON i.id = r.item_id JOIN triage t ON t.item_id = r.item_id"
           f" WHERE t.decision IN ({_APPROVED_SQL}) AND r.subject_id IN ({_in(ids)}) AND r.object_id IN ({_in(ids)})")
    args = list(APPROVED) + list(ids) + list(ids)
    if since:
        sql += " AND i.fetched_at >= ?"
        args.append(since)
    sql += " GROUP BY r.subject_id, r.predicate, r.object_id"
    return store.conn.execute(sql, args).fetchall()


def _edges(store, ids, since, max_edges=None) -> list:
    if not ids:
        return []
    typed = {}
    for subject, predicate, obj, n in _typed(store, ids, since):
        key = frozenset((subject, obj))
        best = typed.get(key)
        if best is None or n > best[3]:
            typed[key] = (subject, predicate, obj, n)
    edges = []
    for (a, b), shared in _cooccurrence(store, ids, since).items():
        rel = typed.pop(frozenset((a, b)), None)
        if rel is not None:
            subject, predicate, obj, n = rel
            edges.append(_edge(subject, obj, predicate, max(shared, n)))
        else:
            edges.append(_edge(a, b, "co", shared))
    for subject, predicate, obj, n in typed.values():     # no co-occurrence: in_category to an untagged category
        edges.append(_edge(subject, obj, predicate, n))
    edges.sort(key=lambda e: (e["kind"] == "co", -e["weight"]))
    if max_edges is not None and len(edges) > max_edges:
        edges = [e for e in edges if e["kind"] != "co"] + [e for e in edges if e["kind"] == "co"]
        edges = edges[:max_edges]
    return edges


def _edge(source, target, kind, weight) -> dict:
    return {"id": f"e{source}-{kind}-e{target}", "source": f"e{source}", "target": f"e{target}", "kind": kind,
            "label": RELATION_LABELS.get(kind, kind), "weight": weight, "directed": kind != "co"}


def graph_view(store, days=30, types=None, min_mentions=1, limit=250, focus=None, now=None) -> dict:
    """Nodes = entities with ≥ `min_mentions` approved items in the window, the `limit` most mentioned;
    with `focus`, that entity and its neighbors. Edges = typed relations, else co-occurrence."""
    types = [t for t in (types or ENTITY_TYPES) if t in TYPE_LABELS] or list(ENTITY_TYPES)
    since = _since(days, now)
    rows = [r for r in _window_counts(store, types, since) if r["n"] >= max(1, int(min_mentions or 1))]
    by_id = {r["id"]: r for r in rows}
    if focus is not None:
        focus = int(str(focus).lstrip("e"))
        pairs = _cooccurrence(store, None, since, anchor=focus)
        shared = sorted(((b if a == focus else a), n) for (a, b), n in pairs.items())
        neighbors = [i for i, _ in sorted(shared, key=lambda p: -p[1]) if i in by_id]
        keep = ([focus] if focus in by_id else []) + neighbors
        if focus not in by_id:
            row = store.get_entity(focus)
            if row is not None:
                by_id[focus] = dict(row) | {"n": 0}
                keep = [focus] + neighbors
        rows = [by_id[i] for i in keep]
    truncated = bool(limit) and len(rows) > int(limit)
    if limit:
        rows = rows[:int(limit)]
    nodes = [_node(r, r["n"]) for r in rows]
    ids = [r["id"] for r in rows]
    return {"nodes": nodes, "edges": _edges(store, ids, since, max_edges=max(300, 6 * len(ids))),
            "window": {"days": days, "since": since}, "types": types, "truncated": truncated,
            "focus": f"e{focus}" if focus is not None else None}


def _items_payload(store, rows) -> list:
    votes = store.item_votes(ids=[r["id"] for r in rows])
    return [{"id": r["id"], "title": r["title"], "url": r["canonical_url"], "source": r["source"],
             "fetched_at": r["fetched_at"], "published_at": r["published_at"], "decision": r["decision"],
             "section": SECTIONS.get(r["decision"], r["decision"]), "total": r["total"],
             "summary_pt": r["summary_pt"], "why_it_matters_pt": r["why_it_matters_pt"],
             "role": r["role"] if "role" in r.keys() else None, "vote": votes.get(r["id"])} for r in rows]


def neighbors(store, entity_id, limit=20, since=None) -> list:
    pairs = _cooccurrence(store, None, since, anchor=int(entity_id))
    shared = {(b if a == int(entity_id) else a): n for (a, b), n in pairs.items()}
    if not shared:
        return []
    rows = store.conn.execute(f"SELECT * FROM entities WHERE id IN ({_in(shared)})", list(shared)).fetchall()
    rows = sorted(rows, key=lambda r: (-shared[r["id"]], -r["mention_count"], r["name"]))[:limit]
    return [{"id": f"e{r['id']}", "entity_id": r["id"], "name": r["name"], "type": r["type"],
             "type_label": TYPE_LABELS.get(r["type"], r["type"]), "shared": shared[r["id"]]} for r in rows]


def entity_detail(store, entity_id, items_limit=40) -> dict | None:
    try:
        entity_id = int(str(entity_id).lstrip("e"))
    except ValueError:
        return None
    row = store.get_entity(entity_id)
    if row is None:
        return None
    aliases = sorted({r[0] for r in store.conn.execute("SELECT alias FROM entity_aliases WHERE entity_id = ?",
                                                       (entity_id,))} - {row["name"]})
    items = store.conn.execute(
        "SELECT i.*, t.decision, t.total, t.summary_pt, t.why_it_matters_pt, m.role FROM entity_mentions m"
        " JOIN items i ON i.id = m.item_id JOIN triage t ON t.item_id = i.id"
        f" WHERE m.entity_id = ? AND t.decision IN ({_APPROVED_SQL}) ORDER BY i.fetched_at DESC LIMIT ?",
        [entity_id] + list(APPROVED) + [items_limit]).fetchall()
    relations = []
    for r in store.conn.execute(
            "SELECT r.predicate, r.subject_id, r.object_id, COUNT(DISTINCT r.item_id) AS n FROM entity_relations r"
            " WHERE (r.subject_id = ? OR r.object_id = ?) AND r.predicate != 'in_category'"
            " GROUP BY r.predicate, r.subject_id, r.object_id ORDER BY n DESC", (entity_id, entity_id)):
        out = r["subject_id"] == entity_id
        other = store.get_entity(r["object_id"] if out else r["subject_id"])
        relations.append({"direction": "out" if out else "in", "relation": r["predicate"],
                          "label": RELATION_LABELS.get(r["predicate"], r["predicate"]), "items": r["n"],
                          "other": {"id": f"e{other['id']}", "entity_id": other["id"], "name": other["name"],
                                    "type": other["type"]}})
    claims, seen_claims = [], set()
    for item in items:
        if item["role"] != "main":
            continue
        extraction = store.get_extraction(item["id"])
        if extraction is None or extraction["status"] != "ok" or not extraction["payload_json"]:
            continue
        for claim in json.loads(extraction["payload_json"]).get("claims", []):
            if claim.get("text_pt") not in seen_claims:
                seen_claims.add(claim.get("text_pt"))
                claims.append({**claim, "item_id": item["id"]})
    return {"id": f"e{row['id']}", "entity_id": row["id"], "name": row["name"], "type": row["type"],
            "type_label": TYPE_LABELS.get(row["type"], row["type"]), "category": row["category"],
            "category_label": _category_label(row["category"]), "mention_count": row["mention_count"],
            "first_seen": row["first_seen"], "last_seen": row["last_seen"], "aliases": aliases,
            "items": _items_payload(store, items), "neighbors": neighbors(store, entity_id, limit=15),
            "relations": relations, "claims": claims[:10]}


def _labeled_tags(tags) -> dict:
    out = {axis: [{"key": k, "label": tx.label(k)} for k in tags.get(axis) or []]
           for axis in ("domains", "problem_types", "techniques")}
    stage = tags.get("evidence_stage")
    out["evidence_stage"] = {"key": stage, "label": tx.EVIDENCE.get(stage, stage)} if stage else None
    out["stakeholders"] = [tx.STAKEHOLDERS.get(s, s) for s in tags.get("stakeholders") or []]
    for key in ("br_applicability", "cfm_risk", "substance", "audience"):
        out[key] = tags.get(key)
    return out


def item_detail(store, item_id) -> dict | None:
    rows = store.get_items([item_id])
    if not rows:
        return None
    item = rows[0]
    triage = store.conn.execute("SELECT * FROM triage WHERE item_id = ?", (item_id,)).fetchone()
    entities = store.conn.execute(
        "SELECT e.*, m.role FROM entity_mentions m JOIN entities e ON e.id = m.entity_id WHERE m.item_id = ?",
        (item_id,)).fetchall()
    entities = sorted(entities, key=lambda r: (-ROLE_RANK.get(r["role"], 0), r["name"].lower()))
    extraction = store.get_extraction(item_id)
    payload = json.loads(extraction["payload_json"]) if extraction is not None and extraction["status"] == "ok" \
        and extraction["payload_json"] else None
    decision = triage["decision"] if triage else None
    return {"id": item["id"], "title": item["title"], "url": item["canonical_url"], "source": item["source"],
            "sources": store.cluster_sources(item_id), "authors": json.loads(item["authors_json"] or "[]"),
            "published_at": item["published_at"], "fetched_at": item["fetched_at"], "decision": decision,
            "section": SECTIONS.get(decision, decision), "total": triage["total"] if triage else None,
            "scores": json.loads(triage["scores_json"] or "{}") if triage else {},
            "summary_pt": triage["summary_pt"] if triage else None,
            "why_it_matters_pt": triage["why_it_matters_pt"] if triage else None,
            "tags": _labeled_tags(json.loads(triage["tags_json"] or "{}")) if triage else {},
            "entities": [{"id": f"e{e['id']}", "entity_id": e["id"], "name": e["name"], "type": e["type"],
                          "type_label": TYPE_LABELS.get(e["type"], e["type"]), "role": e["role"]} for e in entities],
            "extraction": ({"maturity": payload.get("maturity"), "data_modalities": payload.get("data_modalities", []),
                            "claims": payload.get("claims", [])} if payload else None),
            "vote": store.item_votes(ids=[item_id]).get(item_id)}


def search(store, text, limit=20) -> dict:
    text = (text or "").strip()
    if len(text) < 2:
        return {"entities": [], "items": []}
    like, like_norm = f"%{text.lower()}%", f"%{normalize(text)}%"
    entities = store.conn.execute(
        "SELECT DISTINCT e.* FROM entities e LEFT JOIN entity_aliases a ON a.entity_id = e.id"
        " WHERE lower(e.name) LIKE ? OR a.alias_norm LIKE ? OR lower(a.alias) LIKE ?"
        " ORDER BY e.mention_count DESC, e.name LIMIT ?", (like, like_norm, like, limit)).fetchall()
    items = store.conn.execute(
        "SELECT i.*, t.decision, t.total, t.summary_pt, t.why_it_matters_pt FROM items i"
        f" JOIN triage t ON t.item_id = i.id WHERE t.decision IN ({_APPROVED_SQL})"
        " AND (lower(i.title) LIKE ? OR lower(t.summary_pt) LIKE ?) ORDER BY i.fetched_at DESC LIMIT ?",
        list(APPROVED) + [like, like, limit]).fetchall()
    return {"entities": [{"id": f"e{r['id']}", "entity_id": r["id"], "name": r["name"], "type": r["type"],
                          "type_label": TYPE_LABELS.get(r["type"], r["type"]), "mentions": r["mention_count"]}
                         for r in entities],
            "items": _items_payload(store, items)}


def recent_items(store, days=7, section=None, entity_id=None, text=None, limit=20, now=None) -> list:
    sql = ("SELECT i.*, t.decision, t.total, t.summary_pt, t.why_it_matters_pt FROM items i"
           f" JOIN triage t ON t.item_id = i.id WHERE t.decision IN ({_APPROVED_SQL})")
    args = list(APPROVED)
    since = _since(days, now)
    if since:
        sql += " AND i.fetched_at >= ?"
        args.append(since)
    if section:
        sql += " AND t.decision = ?"
        args.append({v: k for k, v in SECTIONS.items()}.get(section, section))
    if entity_id is not None:
        sql += " AND EXISTS (SELECT 1 FROM entity_mentions m WHERE m.item_id = i.id AND m.entity_id = ?)"
        args.append(int(str(entity_id).lstrip("e")))
    if text:
        sql += " AND (lower(i.title) LIKE ? OR lower(t.summary_pt) LIKE ?)"
        args += [f"%{text.lower()}%"] * 2
    sql += " ORDER BY i.fetched_at DESC LIMIT ?"
    args.append(limit)
    return _items_payload(store, store.conn.execute(sql, args).fetchall())


def stats(store) -> dict:
    count = lambda sql, args=(): store.conn.execute(sql, args).fetchone()[0]  # noqa: E731
    by_type = dict(store.conn.execute("SELECT type, COUNT(*) FROM entities GROUP BY type").fetchall())
    last = store.last_run("daily")
    return {"items": count("SELECT COUNT(*) FROM items"),
            "approved": count(f"SELECT COUNT(*) FROM triage WHERE decision IN ({_APPROVED_SQL})", APPROVED),
            "extracted": count("SELECT COUNT(*) FROM extractions WHERE status = 'ok'"),
            "pending_extraction": len(store.extraction_candidates()),
            "entities": {t: by_type.get(t, 0) for t in TYPE_LABELS},
            "mentions": count("SELECT COUNT(*) FROM entity_mentions"),
            "relations": count("SELECT COUNT(*) FROM entity_relations WHERE predicate != 'in_category'"),
            "merges": count("SELECT COUNT(*) FROM entity_merges"),
            "last_daily_run": last["finished_at"] if last else None,
            "graph_synced_at": store.meta_get("graph_synced_at"),
            "pending_sync": len(store.graph_dirty_items())}


def export(store, out_dir, day=None) -> tuple:
    """The whole graph (every type, all time) and the approved items: JSON + nodes/edges CSV."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    day = day or datetime.now(timezone.utc).date().isoformat()
    view = graph_view(store, days=None, types=list(TYPE_LABELS), limit=None)
    view["edges"] = _edges(store, [n["entity_id"] for n in view["nodes"]], None)
    items = recent_items(store, days=None, limit=1_000_000)
    json_path = out_dir / f"graph-{day}.json"
    json_path.write_text(json.dumps({"day": day, "nodes": view["nodes"], "edges": view["edges"], "items": items},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
    nodes_csv, edges_csv = out_dir / f"graph-{day}-nodes.csv", out_dir / f"graph-{day}-edges.csv"
    with nodes_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["id", "label", "type", "category", "count", "mentions",
                                                "first_seen", "last_seen"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(view["nodes"])
    with edges_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["source", "target", "kind", "weight"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(view["edges"])
    return json_path, nodes_csv, edges_csv
