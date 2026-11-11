# sotawhat/graph/fixes.py
"""`sotawhat repair entities` (2026-11-11): the entity graph corrected by hand and by the current naming rule.

config/entity_fixes.yaml names each entity as "type: name":
- merge: the left entity disappears into the right one, also across types. Its mentions (each item keeps the
  stronger role), its relations (those the right type still allows, "uses" a problem as "addresses";
  self-relations go) and its aliases move, so
  the next extraction of the same name lands on the right one. Communities, lessons and the audit trail
  (entity_merges, method "repair") follow.
- rename: a new name and key; the old key stays an alias. A name that another entity already has becomes a merge.
- drop: entities that should not exist, with their mentions, relations and aliases; the resolver skips the name
  from then on (graph/resolve.py, `ignore`).
The naming rule: an acronym in parentheses inside a name ("large language model (LLM) agent") leaves it, as the
resolver now does (`strip_inner_acronyms`); when the clean name is already an entity, the two merge.

Everything runs in one transaction. Removed entities would linger in the Neo4j mirror, so the repair leaves
meta graph_rebuild = 1 and the next sync rebuilds it (graph/neo4j_sync.py)."""
import json
from dataclasses import dataclass, field

from sotawhat.graph.resolve import (ENTITY_CATEGORY, TYPES, display_name, fit_relation, group, normalize,
                                    strip_inner_acronyms)
from sotawhat.store.db import ROLE_RANK, utcnow

NAME_RULE = "sigla no meio do nome"


@dataclass
class Step:
    action: str                     # merge | rename | drop
    source: dict                    # id, type, name, norm, category, mentions
    target: dict | None = None      # merge: the entity that stays
    new_name: str | None = None     # rename
    why: str = "config"             # config | NAME_RULE


@dataclass
class Plan:
    steps: list = field(default_factory=list)
    skipped: list = field(default_factory=list)


def _entity(row) -> dict:
    return {"id": row["id"], "type": row["type"], "name": row["name"], "norm": row["norm"],
            "category": row["category"], "mentions": row["mention_count"]}


def find(store, type_, name):
    """The entity that "type: name" is now: by its key or name, else by an alias (a merged name answers with the
    entity it went into)."""
    norm = normalize(name, type_)
    row = store.conn.execute("SELECT * FROM entities WHERE type = ? AND (norm = ? OR name = ?) ORDER BY id",
                             (type_, norm, name)).fetchone()
    return row if row is not None else store.entity_by_alias(group(type_), norm)


def _owner(store, type_, norm, not_id):
    """Another entity that already answers for (type, key), by its own key or by an alias of the group."""
    row = store.conn.execute("SELECT * FROM entities WHERE type = ? AND norm = ? AND id != ?",
                             (type_, norm, not_id)).fetchone()
    if row is None:
        row = store.entity_by_alias(group(type_), norm)
    return row if row is not None and row["id"] != not_id else None


def _plan_rename(store, plan, gone, row, new_name, why) -> None:
    new_norm = normalize(new_name, row["type"])
    if (new_name, new_norm) == (row["name"], row["norm"]):
        return                                                    # renamed already
    owner = _owner(store, row["type"], new_norm, row["id"])
    if owner is not None and owner["id"] not in gone:
        plan.steps.append(Step("merge", _entity(row), _entity(owner), why=why))
        gone.add(row["id"])
    elif owner is None:
        plan.steps.append(Step("rename", _entity(row), new_name=new_name, why=why))
    else:
        plan.skipped.append(f"rename {row['type']}: {row['name']} → {new_name}: o nome é de uma entidade que sai")


def plan_fixes(store, fixes) -> Plan:
    """What `apply_fixes` would do, in order: the merges, renames and drops of the file, then the naming rule.
    Nothing is written. A merge or rename that matches nothing is listed in `skipped`; one done already, and a
    drop whose entity is gone, are silent."""
    plan, gone = Plan(), set()                  # gone: ids that an earlier step removes
    ref = lambda type_, name: f"{type_}: {name}"  # noqa: E731
    for (s_type, s_name), (t_type, t_name) in fixes.get("merge", []):
        source, target = find(store, s_type, s_name), find(store, t_type, t_name)
        if source is None or target is None:
            missing = ref(s_type, s_name) if source is None else ref(t_type, t_name)
            plan.skipped.append(f"merge {ref(s_type, s_name)} → {ref(t_type, t_name)}: {missing} não encontrada")
        elif source["id"] != target["id"] and source["id"] not in gone and target["id"] not in gone:
            plan.steps.append(Step("merge", _entity(source), _entity(target)))
            gone.add(source["id"])
    for (type_, name), new_name in fixes.get("rename", []):
        row = find(store, type_, name)
        if row is None:
            plan.skipped.append(f"rename {ref(type_, name)} → {new_name}: não encontrada")
        elif row["id"] not in gone:
            _plan_rename(store, plan, gone, row, new_name, "config")
    for type_, name in fixes.get("drop", []):
        row = find(store, type_, name)
        if row is not None and row["id"] not in gone:      # absent is what a drop wants: nothing to say
            plan.steps.append(Step("drop", _entity(row)))
            gone.add(row["id"])
    renamed = {s.source["id"] for s in plan.steps if s.action == "rename"}
    for row in store.conn.execute(f"SELECT * FROM entities WHERE type IN ({','.join('?' * len(TYPES))}) ORDER BY id",
                                  TYPES).fetchall():
        stripped = strip_inner_acronyms(row["name"])
        if stripped != row["name"] and row["id"] not in gone and row["id"] not in renamed:
            _plan_rename(store, plan, gone, row, display_name(stripped, row["type"]), NAME_RULE)
    return plan


def describe(step) -> str:
    source = f"{step.source['type']}: {step.source['name']} ({step.source['mentions']} itens)"
    why = f" [{step.why}]" if step.why != "config" else ""
    if step.action == "merge":
        return f"funde {source} → {step.target['type']}: {step.target['name']}{why}"
    if step.action == "rename":
        return f"renomeia {source} → {step.new_name}{why}"
    return f"remove {source}"


# --- writing ------------------------------------------------------------------------------------------------
def _type(conn, entity_id):
    row = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()
    return row[0] if row is not None else None


def _refit(conn, predicate, subject, obj):
    """The predicate the relation keeps between the new types ("uses" a problem: "addresses"), or None."""
    subject_type, object_type = _type(conn, subject), _type(conn, obj)
    if predicate == "in_category":
        return predicate if ENTITY_CATEGORY.get(subject_type, (None,))[0] == object_type else None
    return fit_relation(predicate, subject_type, object_type)


def _recount(conn, entity_id) -> None:
    conn.execute("UPDATE entities SET mention_count = (SELECT COUNT(*) FROM entity_mentions WHERE entity_id = :id),"
                 " first_seen = (SELECT MIN(i.fetched_at) FROM entity_mentions m JOIN items i ON i.id = m.item_id"
                 " WHERE m.entity_id = :id), last_seen = (SELECT MAX(i.fetched_at) FROM entity_mentions m"
                 " JOIN items i ON i.id = m.item_id WHERE m.entity_id = :id) WHERE id = :id", {"id": entity_id})


def _repoint_lessons(conn, old, new=None) -> None:
    for lesson_id, raw in conn.execute("SELECT id, entities_json FROM lessons").fetchall():
        ids = json.loads(raw or "[]")
        if old not in ids:
            continue
        kept = []
        for entity_id in ids:
            entity_id = new if entity_id == old else entity_id
            if entity_id is not None and entity_id not in kept:
                kept.append(entity_id)
        conn.execute("UPDATE lessons SET entities_json = ? WHERE id = ?", (json.dumps(kept), lesson_id))


def _merge(conn, source, target) -> int:
    """-> relations dropped (self-relations and the ones the target's type does not allow)."""
    s, t = source["id"], target["id"]
    for item_id, role in conn.execute("SELECT item_id, role FROM entity_mentions WHERE entity_id = ?", (s,)).fetchall():
        current = conn.execute("SELECT role FROM entity_mentions WHERE item_id = ? AND entity_id = ?",
                               (item_id, t)).fetchone()
        if current is None:
            conn.execute("INSERT INTO entity_mentions(item_id, entity_id, role) VALUES(?,?,?)", (item_id, t, role))
        elif ROLE_RANK.get(role, 0) > ROLE_RANK.get(current[0], 0):
            conn.execute("UPDATE entity_mentions SET role = ? WHERE item_id = ? AND entity_id = ?", (role, item_id, t))
    conn.execute("DELETE FROM entity_mentions WHERE entity_id = ?", (s,))
    relations = conn.execute("SELECT subject_id, predicate, object_id, item_id, created_at FROM entity_relations"
                             " WHERE subject_id = ? OR object_id = ?", (s, s)).fetchall()
    conn.execute("DELETE FROM entity_relations WHERE subject_id = ? OR object_id = ?", (s, s))
    dropped = 0
    for subject, predicate, obj, item_id, created_at in relations:
        subject, obj = (t if subject == s else subject), (t if obj == s else obj)
        predicate = _refit(conn, predicate, subject, obj) if subject != obj else None
        if predicate is None:
            dropped += 1
            continue
        conn.execute("INSERT OR IGNORE INTO entity_relations(subject_id, predicate, object_id, item_id, created_at)"
                     " VALUES(?,?,?,?,?)", (subject, predicate, obj, item_id, created_at))
    conn.execute("UPDATE entity_aliases SET entity_id = ? WHERE entity_id = ?", (t, s))     # also across types
    conn.execute("INSERT OR IGNORE INTO entity_aliases(grp, alias_norm, entity_id, alias) VALUES(?,?,?,?)",
                 (group(source["type"]), source["norm"], t, source["name"]))
    conn.execute("UPDATE entity_merges SET entity_id = ? WHERE entity_id = ?", (t, s))
    conn.execute("INSERT INTO entity_merges(entity_id, name, item_id, method, score, decided_at)"
                 " VALUES(?, ?, NULL, 'repair', NULL, ?)", (t, source["name"], utcnow()))
    conn.execute("UPDATE OR IGNORE entity_communities SET entity_id = ? WHERE entity_id = ?", (t, s))
    conn.execute("DELETE FROM entity_communities WHERE entity_id = ?", (s,))
    conn.execute("UPDATE communities SET top_entity_id = ? WHERE top_entity_id = ?", (t, s))
    _repoint_lessons(conn, s, t)
    if not target["category"] and source["category"] in ENTITY_CATEGORY.get(target["type"], (None, {}))[1]:
        conn.execute("UPDATE entities SET category = ? WHERE id = ?", (source["category"], t))
    conn.execute("DELETE FROM entity_embeddings WHERE entity_id = ?", (s,))
    conn.execute("DELETE FROM entities WHERE id = ?", (s,))
    _recount(conn, t)
    return dropped


def _rename(conn, entity, new_name) -> None:
    grp, new_norm = group(entity["type"]), normalize(new_name, entity["type"])
    for norm, alias in ((entity["norm"], entity["name"]), (new_norm, new_name)):     # the old key stays an alias
        conn.execute("INSERT OR IGNORE INTO entity_aliases(grp, alias_norm, entity_id, alias) VALUES(?,?,?,?)",
                     (grp, norm, entity["id"], alias))
    conn.execute("UPDATE entities SET name = ?, norm = ? WHERE id = ?", (new_name, new_norm, entity["id"]))


def _drop(conn, entity) -> None:
    eid = entity["id"]
    for table in ("entity_mentions", "entity_aliases", "entity_embeddings", "entity_communities"):
        conn.execute(f"DELETE FROM {table} WHERE entity_id = ?", (eid,))
    conn.execute("DELETE FROM entity_relations WHERE subject_id = ? OR object_id = ?", (eid, eid))
    conn.execute("UPDATE communities SET top_entity_id = NULL WHERE top_entity_id = ?", (eid,))
    _repoint_lessons(conn, eid)
    conn.execute("DELETE FROM entities WHERE id = ?", (eid,))


def apply_fixes(store, plan) -> dict:
    """Runs the plan in one transaction -> {"merged", "renamed", "dropped", "relations_dropped"}."""
    report = {"merged": 0, "renamed": 0, "dropped": 0, "relations_dropped": 0}
    if not plan.steps:
        return report
    conn = store.conn
    with store._lock:
        try:
            for step in plan.steps:
                if step.action == "merge":
                    report["relations_dropped"] += _merge(conn, step.source, step.target)
                    report["merged"] += 1
                elif step.action == "rename":
                    _rename(conn, step.source, step.new_name)
                    report["renamed"] += 1
                else:
                    _drop(conn, step.source)
                    report["dropped"] += 1
            conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('graph_rebuild', '1')")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return report
