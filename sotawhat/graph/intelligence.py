# sotawhat/graph/intelligence.py
"""Weekly graph intelligence (SDD §6.9) over the entity graph kept in SQLite (D16), with NetworkX.

- trends: entities whose mentions in the last `recent_days` rose against the previous `baseline_days`
  (Poisson-style z = (recent − expected) / √(expected + 1)), plus entities that are new this week;
- communities: Louvain (weighted, fixed seed) over entity co-occurrence and typed relations;
- gaps, the raw material of ideation (§8.3, stage 1):
  - recent techniques never linked to frequent problems ("why now");
  - bridges between technique-heavy and problem-heavy communities that barely touch;
  - serendipity, random technique × problem pairs from distant communities.
Only approved items count; windows use `items.fetched_at`."""
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import networkx as nx

from sotawhat.store.db import APPROVED

TECHNIQUE_TYPES = ("technique", "model")
PROBLEM_TYPES = ("problem",)
GRAPH_TYPES = ("technique", "model", "dataset", "organization", "product", "problem", "regulation")
_IN = ",".join("?" * len(APPROVED))


def _iso(moment) -> str:
    return moment.isoformat(timespec="seconds")


def _now(now):
    return now or datetime.now(timezone.utc)


def _counts(store, start, end=None, end_inclusive=True) -> Counter:
    sql = ("SELECT m.entity_id, COUNT(DISTINCT m.item_id) FROM entity_mentions m JOIN items i ON i.id = m.item_id "
           f"JOIN triage t ON t.item_id = m.item_id WHERE t.decision IN ({_IN}) AND i.fetched_at >= ?")
    args = list(APPROVED) + [_iso(start)]
    if end is not None:
        sql += " AND i.fetched_at <= ?" if end_inclusive else " AND i.fetched_at < ?"
        args.append(_iso(end))
    return Counter(dict(store.conn.execute(sql + " GROUP BY m.entity_id", args).fetchall()))


def _entities(store, ids) -> dict:
    ids = list(ids)
    if not ids:
        return {}
    rows = store.conn.execute(f"SELECT * FROM entities WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall()
    return {r["id"]: r for r in rows}


def trends(store, now=None, recent_days=7, baseline_days=28, min_recent=2, limit=20) -> list:
    now = _now(now)
    recent_start = now - timedelta(days=recent_days)
    recent = _counts(store, recent_start, now)
    base = _counts(store, recent_start - timedelta(days=baseline_days), recent_start, end_inclusive=False)
    rows = _entities(store, recent)
    out = []
    for entity_id, count in recent.items():
        row = rows.get(entity_id)
        if row is None or count < min_recent or row["type"] not in GRAPH_TYPES:
            continue
        expected = base.get(entity_id, 0) * recent_days / baseline_days
        z = (count - expected) / math.sqrt(expected + 1)
        out.append({"entity_id": entity_id, "name": row["name"], "type": row["type"], "recent": count,
                    "baseline": base.get(entity_id, 0), "z": round(z, 2),
                    "new": base.get(entity_id, 0) == 0 and (row["first_seen"] or "") >= _iso(recent_start)})
    out.sort(key=lambda t: (-t["z"], -t["recent"], t["name"]))
    return out[:limit]


def build_graph(store, now=None, days=90, types=GRAPH_TYPES) -> nx.Graph:
    now = _now(now)
    since = _iso(now - timedelta(days=days))
    counts = _counts(store, now - timedelta(days=days), now)
    rows = {k: v for k, v in _entities(store, counts).items() if v["type"] in types}
    graph = nx.Graph()
    for entity_id, row in rows.items():
        graph.add_node(entity_id, name=row["name"], type=row["type"], count=counts[entity_id],
                       first_seen=row["first_seen"] or "")
    pairs = store.conn.execute(
        "SELECT a.entity_id, b.entity_id, COUNT(DISTINCT a.item_id) FROM entity_mentions a "
        "JOIN entity_mentions b ON b.item_id = a.item_id AND a.entity_id < b.entity_id "
        f"JOIN items i ON i.id = a.item_id JOIN triage t ON t.item_id = a.item_id WHERE t.decision IN ({_IN}) "
        "AND i.fetched_at >= ? AND i.fetched_at <= ? GROUP BY a.entity_id, b.entity_id",
        list(APPROVED) + [since, _iso(now)]).fetchall()
    for a, b, weight in pairs:
        if a in rows and b in rows:
            graph.add_edge(a, b, weight=float(weight))
    for subject, obj, n in store.conn.execute(
            "SELECT r.subject_id, r.object_id, COUNT(DISTINCT r.item_id) FROM entity_relations r "
            "JOIN items i ON i.id = r.item_id WHERE r.predicate != 'in_category' AND i.fetched_at >= ? "
            "AND i.fetched_at <= ? GROUP BY r.subject_id, r.object_id", (since, _iso(now))).fetchall():
        if subject in rows and obj in rows and subject != obj:
            current = graph.get_edge_data(subject, obj, {}).get("weight", 0.0)
            graph.add_edge(subject, obj, weight=current + float(n))     # explicit relations count double
    return graph


def communities(store, now=None, days=90, seed=7, min_size=3, graph=None) -> list:
    graph = graph if graph is not None else build_graph(store, now, days)
    if graph.number_of_edges() == 0:
        return []
    groups = nx.community.louvain_communities(graph, weight="weight", seed=seed)
    out = []
    for members in groups:
        if len(members) < min_size:
            continue
        degree = {n: graph.degree(n, weight="weight") for n in members}
        ranked = sorted(members, key=lambda n: (-graph.nodes[n]["count"], -degree[n], graph.nodes[n]["name"]))
        out.append({"members": ranked, "size": len(members),
                    "importance": sum(graph.nodes[n]["count"] for n in members),
                    "types": dict(Counter(graph.nodes[n]["type"] for n in members)),
                    "top": [(n, graph.nodes[n]["name"], graph.nodes[n]["type"]) for n in ranked[:8]]})
    out.sort(key=lambda c: (-c["importance"], -c["size"]))
    for number, community in enumerate(out):
        community["community"] = number
    return out


def _pair(graph, technique, problem, sampler, score) -> dict:
    t, p = graph.nodes[technique], graph.nodes[problem]
    return {"technique_id": technique, "technique": t["name"], "technique_type": t["type"], "problem_id": problem,
            "problem": p["name"], "sampler": sampler, "score": round(float(score), 3),
            "why_now": f"{t['name']} apareceu pela primeira vez em {t['first_seen'][:10] or '?'}"}


def gaps(store, now=None, days=90, recent_days=60, limit=30, seed=7, graph=None, groups=None) -> dict:
    now = _now(now)
    graph = graph if graph is not None else build_graph(store, now, days)
    groups = groups if groups is not None else communities(store, now, days, seed=seed, graph=graph)
    techniques = [n for n, d in graph.nodes(data=True) if d["type"] in TECHNIQUE_TYPES]
    problems = [n for n, d in graph.nodes(data=True) if d["type"] in PROBLEM_TYPES]
    recent_cut = _iso(now - timedelta(days=recent_days))
    recent = [t for t in techniques if graph.nodes[t]["first_seen"] >= recent_cut]
    frequent = sorted(problems, key=lambda p: -graph.nodes[p]["count"])[:max(10, limit)]
    unlinked = [_pair(graph, t, p, "recent_technique", graph.nodes[t]["count"] * graph.nodes[p]["count"])
                for t in recent for p in frequent if not graph.has_edge(t, p)]
    unlinked.sort(key=lambda c: (-c["score"], c["technique"], c["problem"]))

    member_of = {n: g["community"] for g in groups for n in g["members"]}
    weights = defaultdict(float)
    for a, b, data in graph.edges(data=True):
        if a in member_of and b in member_of and member_of[a] != member_of[b]:
            weights[tuple(sorted((member_of[a], member_of[b])))] += data["weight"]
    bridges = []
    for g1 in groups:
        for g2 in groups:
            if g1["community"] == g2["community"]:
                continue
            tech = next((n for n in g1["members"] if graph.nodes[n]["type"] in TECHNIQUE_TYPES), None)
            prob = next((n for n in g2["members"] if graph.nodes[n]["type"] in PROBLEM_TYPES), None)
            if tech is None or prob is None or graph.has_edge(tech, prob):
                continue
            link = weights.get(tuple(sorted((g1["community"], g2["community"]))), 0.0)
            score = math.sqrt(g1["importance"] * g2["importance"]) / (1.0 + link)
            bridges.append(_pair(graph, tech, prob, "community_bridge", score) | {
                "communities": [g1["community"], g2["community"]]})
    bridges.sort(key=lambda c: (-c["score"], c["technique"], c["problem"]))

    rng = random.Random(seed)
    serendipity, tries = [], 0
    while techniques and problems and len(serendipity) < limit and tries < limit * 20:
        tries += 1
        t, p = rng.choice(techniques), rng.choice(problems)
        if graph.has_edge(t, p) or member_of.get(t) == member_of.get(p) is not None:
            continue
        try:
            distance = nx.shortest_path_length(graph, t, p)
        except nx.NetworkXNoPath:
            distance = 99
        if distance >= 3 and all((t, p) != (c["technique_id"], c["problem_id"]) for c in serendipity):
            serendipity.append(_pair(graph, t, p, "serendipity", distance))
    return {"recent_technique": unlinked[:limit], "community_bridge": bridges[:limit], "serendipity": serendipity}
