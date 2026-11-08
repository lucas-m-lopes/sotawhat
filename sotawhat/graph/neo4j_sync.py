# sotawhat/graph/neo4j_sync.py
"""Neo4j mirror of the entity graph kept in SQLite (SDD §6.3, D16).

`sync` sends the approved items whose graph rows changed since the last sync (watermark
`items.graph_synced_at`), the entities they touch, their MENTIONS and the typed relations, aggregated
over every item that states them (`items`, `weight`). Everything is MERGE, so a sync can be repeated.
`rebuild` empties the database in batches and sends everything again (RNF8).
Labels and relationship types come from closed tables: an unknown type in SQLite is skipped, never
interpolated into Cypher."""
from dataclasses import asdict, dataclass

from sotawhat.graph.query import SECTIONS
from sotawhat.store.db import APPROVED, utcnow

LABELS = {"technique": "Technique", "model": "Model", "dataset": "Dataset", "organization": "Organization",
          "product": "Product", "problem": "Problem", "regulation": "Regulation", "domain": "Domain",
          "problem_type": "ProblemType", "technique_family": "TechniqueFamily"}
REL_TYPES = {"uses": "USES", "addresses": "ADDRESSES", "developed_by": "DEVELOPED_BY", "evaluated_on": "EVALUATED_ON",
             "compared_with": "COMPARED_WITH", "builds_on": "BUILDS_ON", "regulated_by": "REGULATED_BY",
             "in_category": "IN_CATEGORY"}


@dataclass
class SyncStats:
    items: int = 0
    entities: int = 0
    mentions: int = 0
    relations: int = 0
    deleted: int = 0
    rebuilt: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def _in(values) -> str:
    return ",".join("?" * len(values))


class Neo4jMirror:
    def __init__(self, driver, database="neo4j"):
        self.driver, self.database = driver, database

    @classmethod
    def from_settings(cls, settings, driver_factory=None):
        """None when NEO4J_PASSWORD is empty (mirror off)."""
        if not settings.neo4j_password:
            return None
        if driver_factory is None:
            from neo4j import GraphDatabase
            driver_factory = GraphDatabase.driver
        driver = driver_factory(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password),
                                connection_timeout=5, max_connection_lifetime=300)
        return cls(driver, settings.neo4j_database)

    def _run(self, query, **params):
        records, _, _ = self.driver.execute_query(query, parameters_=params, database_=self.database)
        return records

    def read(self, query, limit=200, **params) -> tuple:
        """-> (rows as dicts, truncated). READ access mode: the server itself refuses writes."""
        from neo4j import RoutingControl

        records, _, _ = self.driver.execute_query(query, parameters_=params, database_=self.database,
                                                  routing_=RoutingControl.READ)
        return [r.data() for r in records[:limit]], len(records) > limit

    def ping(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:  # noqa: BLE001 - any failure means "not reachable now"
            return False

    def close(self) -> None:
        self.driver.close()

    def ensure_schema(self) -> None:
        self._run("CREATE CONSTRAINT item_id IF NOT EXISTS FOR (i:Item) REQUIRE i.id IS UNIQUE")
        self._run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")

    def counts(self) -> dict:
        nodes = self._run("MATCH (n) RETURN count(n) AS n")[0]["n"]
        relationships = self._run("MATCH ()-[r]->() RETURN count(r) AS n")[0]["n"]
        return {"nodes": nodes, "relationships": relationships}

    def sync(self, store, rebuild=False, batch=500) -> SyncStats:
        stats = SyncStats(rebuilt=rebuild)
        self.ensure_schema()
        if rebuild:
            while True:
                deleted = self._run("MATCH (n) WITH n LIMIT 5000 DETACH DELETE n RETURN count(*) AS n")[0]["n"]
                stats.deleted += deleted
                if not deleted:
                    break
            store.mark_all_graph_dirty()
        while True:
            ids = store.graph_dirty_items(limit=batch)
            if not ids:
                break
            self._sync_items(store, ids, stats)
            store.mark_graph_synced(ids)
        store.meta_set("graph_synced_at", utcnow())
        return stats

    def _sync_items(self, store, ids, stats) -> None:
        conn = store.conn
        items = conn.execute(
            "SELECT i.id, i.title, i.canonical_url, i.source, i.kind, i.fetched_at, i.published_at, t.decision,"
            f" t.total, t.summary_pt, t.why_it_matters_pt FROM items i JOIN triage t ON t.item_id = i.id"
            f" WHERE i.id IN ({_in(ids)})", ids).fetchall()
        self._run("UNWIND $rows AS row MERGE (i:Item {id: row.id}) SET i += row.props", rows=[
            {"id": r["id"], "props": {"title": r["title"], "url": r["canonical_url"], "source": r["source"],
                                      "kind": r["kind"], "fetched_at": r["fetched_at"],
                                      "published_at": r["published_at"], "decision": r["decision"],
                                      "section": SECTIONS.get(r["decision"], r["decision"]), "total": r["total"],
                                      "summary_pt": r["summary_pt"], "why_it_matters_pt": r["why_it_matters_pt"]}}
            for r in items])
        stats.items += len(items)

        mentions = conn.execute(f"SELECT item_id, entity_id, role FROM entity_mentions WHERE item_id IN ({_in(ids)})",
                                ids).fetchall()
        triples = {(r[0], r[1], r[2]) for r in conn.execute(
            f"SELECT subject_id, predicate, object_id FROM entity_relations WHERE item_id IN ({_in(ids)})", ids)
            if r[1] in REL_TYPES}
        touched = {m["entity_id"] for m in mentions} | {t[0] for t in triples} | {t[2] for t in triples}
        entities = conn.execute(f"SELECT * FROM entities WHERE id IN ({_in(touched)})", list(touched)).fetchall() \
            if touched else []
        known, by_label = set(), {}
        for row in entities:
            label = LABELS.get(row["type"])
            if label is None:
                continue
            known.add(row["id"])
            by_label.setdefault(label, []).append(
                {"id": row["id"], "props": {"name": row["name"], "type": row["type"], "norm": row["norm"],
                                            "category": row["category"], "mention_count": row["mention_count"],
                                            "first_seen": row["first_seen"], "last_seen": row["last_seen"]}})
        for label, rows in by_label.items():
            self._run(f"UNWIND $rows AS row MERGE (e:Entity {{id: row.id}}) SET e += row.props, e:{label}", rows=rows)
            stats.entities += len(rows)

        self._run("UNWIND $ids AS id MATCH (:Item {id: id})-[m:MENTIONS]->() DELETE m", ids=list(ids))
        rows = [{"item": m["item_id"], "entity": m["entity_id"], "role": m["role"]} for m in mentions
                if m["entity_id"] in known]
        if rows:
            self._run("UNWIND $rows AS row MATCH (i:Item {id: row.item}) MATCH (e:Entity {id: row.entity})"
                      " MERGE (i)-[m:MENTIONS]->(e) SET m.role = row.role", rows=rows)
            stats.mentions += len(rows)

        by_type = {}
        for subject, predicate, obj in sorted(triples):
            if subject not in known or obj not in known:
                continue
            items_of = [r[0] for r in conn.execute(
                "SELECT DISTINCT r.item_id FROM entity_relations r JOIN triage t ON t.item_id = r.item_id"
                f" WHERE r.subject_id = ? AND r.predicate = ? AND r.object_id = ? AND t.decision IN ({_in(APPROVED)})"
                " ORDER BY r.item_id", [subject, predicate, obj] + list(APPROVED))]
            by_type.setdefault(REL_TYPES[predicate], []).append(
                {"s": subject, "o": obj, "items": items_of, "weight": len(items_of)})
        for rel_type, rows in by_type.items():
            self._run(f"UNWIND $rows AS row MATCH (s:Entity {{id: row.s}}) MATCH (o:Entity {{id: row.o}})"
                      f" MERGE (s)-[r:{rel_type}]->(o) SET r.items = row.items, r.weight = row.weight", rows=rows)
            stats.relations += len(rows)
