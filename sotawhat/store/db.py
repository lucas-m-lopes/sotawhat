# sotawhat/store/db.py
"""SQLite operational store (SDD §6.4): items, runs, source health, LLM cost ledger; since schema 2 (P1)
triage, embeddings, clusters, feedback, deliveries, classifiers and the inbox; since schema 3 (P3) the
entity graph that the interface and the MCP read (extractions, entities, aliases, mentions, relations,
merges, entity embeddings) and the Neo4j mirror watermark (`items.graph_synced_at`)."""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from sotawhat.textmatch import fold

SCHEMA_VERSION = 6
APPROVED = ("main", "frontier", "radar")
ROLE_RANK = {"tag": 0, "mentioned": 1, "used": 2, "main": 3}
IDEA_STATUS = {"up": "curtida", "down": "rejeitada", "test": "testar", "archive": "engavetada", "built": "construida"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS items(
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT,
    canonical_url TEXT,
    doi TEXT,
    arxiv_id TEXT,
    pmid TEXT,
    title TEXT NOT NULL,
    authors_json TEXT NOT NULL DEFAULT '[]',
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    text TEXT,
    content_hash TEXT,
    concepts_json TEXT NOT NULL DEFAULT '[]',
    profile TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    first_run_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_items_fetched ON items(fetched_at);
CREATE TABLE IF NOT EXISTS runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    ok INTEGER,
    stats_json TEXT,
    cost_usd REAL NOT NULL DEFAULT 0,
    error TEXT
);
CREATE TABLE IF NOT EXISTS source_state(
    source TEXT PRIMARY KEY,
    last_ok_at TEXT,
    last_error TEXT,
    last_error_at TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS llm_calls(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    task TEXT NOT NULL,
    requested_model TEXT NOT NULL,
    model TEXT,
    provider TEXT,
    generation_id TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    cached_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    latency_ms INTEGER,
    status TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_created ON llm_calls(created_at);
"""

_SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS triage(
    item_id TEXT PRIMARY KEY,
    run_id INTEGER,
    decision TEXT NOT NULL,          -- main | frontier | radar | reject | muted | duplicate | gated | error
    reason TEXT,
    total REAL,
    scores_json TEXT,                -- {"A":..,"B":..,"C":..,"D":..}
    summary_pt TEXT,
    why_it_matters_pt TEXT,
    tags_json TEXT,
    pre_score REAL,                  -- classifier probability, when a classifier exists
    classifier_version TEXT,
    model TEXT,
    prompt_version TEXT,
    cost_usd REAL NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 1,
    triaged_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_triage_run ON triage(run_id);
CREATE TABLE IF NOT EXISTS embeddings(
    item_id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector BLOB NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clusters(
    id TEXT PRIMARY KEY,             -- = id of the representative item
    representative_item_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL,       -- item | idea | entity
    target_id TEXT NOT NULL,
    value TEXT NOT NULL,             -- up | down | test | archive
    note TEXT,
    channel TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_target ON feedback(target_type, target_id);
CREATE TABLE IF NOT EXISTS deliveries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    day TEXT NOT NULL,
    item_id TEXT NOT NULL,
    key TEXT NOT NULL,               -- short id carried by the Telegram buttons
    section TEXT NOT NULL,           -- main | frontier | radar
    position INTEGER NOT NULL,
    chat_id TEXT,
    message_id INTEGER,
    sent_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_deliveries_key ON deliveries(key);
CREATE INDEX IF NOT EXISTS idx_deliveries_message ON deliveries(chat_id, message_id);
CREATE TABLE IF NOT EXISTS classifier_models(
    version TEXT PRIMARY KEY,
    profile TEXT NOT NULL,
    embed_model TEXT NOT NULL,
    trained_at TEXT NOT NULL,
    n_labels INTEGER NOT NULL,
    metrics_json TEXT,
    path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inbox(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    received_at TEXT NOT NULL,
    processed_at TEXT
);
"""

_SCHEMA_V3 = """
CREATE TABLE IF NOT EXISTS extractions(
    item_id TEXT PRIMARY KEY,
    run_id INTEGER,
    status TEXT NOT NULL,            -- ok | error
    model TEXT,
    prompt_version TEXT,
    payload_json TEXT,               -- validated Extraction (SDD §6.8)
    error TEXT,
    cost_usd REAL NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 1,
    extracted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entities(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,              -- technique | model | dataset | organization | product | problem | regulation
                                     -- | domain | problem_type | technique_family (taxonomy categories)
    name TEXT NOT NULL,
    norm TEXT NOT NULL,              -- normalized name (graph/resolve.normalize)
    category TEXT,                   -- taxonomy key: C.. (technique/model), B.. (problem), the key itself (category)
    first_seen TEXT,                 -- fetched_at of the first and the last item that mention it
    last_seen TEXT,
    mention_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(type, norm)
);
CREATE TABLE IF NOT EXISTS entity_aliases(
    grp TEXT NOT NULL,               -- resolution group: the type, except model and product ("artifact")
    alias_norm TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    PRIMARY KEY(grp, alias_norm)
);
CREATE TABLE IF NOT EXISTS entity_mentions(
    item_id TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    role TEXT NOT NULL,              -- main | used | mentioned | tag
    PRIMARY KEY(item_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_mentions_entity ON entity_mentions(entity_id);
CREATE TABLE IF NOT EXISTS entity_relations(
    subject_id INTEGER NOT NULL,
    predicate TEXT NOT NULL,         -- uses | addresses | developed_by | evaluated_on | compared_with | builds_on
                                     -- | regulated_by | in_category
    object_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,           -- provenance
    created_at TEXT NOT NULL,
    PRIMARY KEY(subject_id, predicate, object_id, item_id)
);
CREATE INDEX IF NOT EXISTS idx_relations_item ON entity_relations(item_id);
CREATE TABLE IF NOT EXISTS entity_merges(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,      -- the entity an extracted name was resolved to
    name TEXT NOT NULL,              -- the name as extracted
    item_id TEXT,
    method TEXT NOT NULL,            -- alias | judge
    score REAL,
    decided_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entity_embeddings(
    entity_id INTEGER PRIMARY KEY,
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector BLOB NOT NULL
);
"""

_SCHEMA_V4 = """
CREATE TABLE IF NOT EXISTS ideas(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL DEFAULT 1,
    parent_id INTEGER,
    run_id INTEGER,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'nova',  -- nova | curtida | rejeitada | testar | engavetada | construida | descartada
    title TEXT NOT NULL,
    lens TEXT,
    persona TEXT,
    niche TEXT,                           -- domain | technique family | form (portfolio cell)
    candidate_json TEXT,                  -- technique × problem, sampler, compact subgraph
    card_json TEXT NOT NULL,              -- IdeaDraft + dossier
    critique_json TEXT,
    novelty_json TEXT,                    -- prior art per layer + facet matrix
    scores_json TEXT,                     -- rubric axes (SDD §8.4)
    score REAL,
    selected INTEGER NOT NULL DEFAULT 0,  -- 1 = finalist delivered in a weekly report
    discard_reason TEXT,
    embedding BLOB
);
CREATE INDEX IF NOT EXISTS idx_ideas_run ON ideas(run_id);
CREATE TABLE IF NOT EXISTS communities(
    run_id INTEGER NOT NULL,
    community INTEGER NOT NULL,
    label TEXT,
    summary TEXT,
    size INTEGER,
    top_entity_id INTEGER,
    PRIMARY KEY(run_id, community)
);
CREATE TABLE IF NOT EXISTS entity_communities(
    run_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    community INTEGER NOT NULL,
    PRIMARY KEY(run_id, entity_id)
);
CREATE TABLE IF NOT EXISTS weekly_reports(
    run_id INTEGER PRIMARY KEY,
    day TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

_SCHEMA_V5 = """
CREATE TABLE IF NOT EXISTS lessons(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    topic TEXT NOT NULL,
    entities_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'nova',  -- nova | planejada | narrada | renderizada | pronta | entregue | falhou
    title TEXT,
    plan_json TEXT,
    report_json TEXT,                     -- gates, attempts per scene, timings, cost
    voice TEXT,
    video_path TEXT,
    duration_s REAL,
    size_bytes INTEGER,
    run_id INTEGER,
    cost_usd REAL,
    delivered_at TEXT,
    requiz_at TEXT,
    review TEXT,                          -- ok | erro (your check, G8)
    comparison TEXT,                      -- melhor | empate | pior than the NotebookLM Video Overview
    error TEXT
);
CREATE TABLE IF NOT EXISTS lesson_answers(
    lesson_id INTEGER NOT NULL,
    round INTEGER NOT NULL,               -- 0 = with the lesson, 1 = re-quiz days later
    question INTEGER NOT NULL,
    chosen INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    answered_at TEXT NOT NULL,
    PRIMARY KEY(lesson_id, round, question)
);
"""
_SCHEMA_V6 = """
CREATE TABLE IF NOT EXISTS radar_repos(
    full_name TEXT PRIMARY KEY,           -- owner/repo in lower case (radar de ferramentas, 2026-11-10)
    name TEXT NOT NULL,                   -- owner/repo as GitHub writes it
    description TEXT,
    language TEXT,
    license TEXT,
    topics_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT,
    homepage TEXT,
    fronts_json TEXT NOT NULL DEFAULT '[]',   -- the radar fronts whose searches found it
    sources_json TEXT NOT NULL DEFAULT '[]',  -- github | hn
    packages_json TEXT,                       -- [{"registry": "npm" | "pypi", "name"}]; NULL: not looked up yet
    release_at TEXT,                          -- the latest release (the two-week rule for dependencies)
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS radar_stars(
    full_name TEXT NOT NULL,
    day TEXT NOT NULL,
    stars INTEGER NOT NULL,
    forks INTEGER,
    pushed_at TEXT,
    PRIMARY KEY(full_name, day)
);
CREATE TABLE IF NOT EXISTS radar_hn(
    full_name TEXT NOT NULL,
    story_id TEXT NOT NULL,
    title TEXT,
    points INTEGER,
    comments INTEGER,
    created_at TEXT,
    PRIMARY KEY(full_name, story_id)
);
CREATE TABLE IF NOT EXISTS radar_picks(
    run_id INTEGER NOT NULL,
    day TEXT NOT NULL,
    full_name TEXT NOT NULL,
    rank INTEGER,                         -- position in the report; NULL: judged and left out
    front TEXT,
    score REAL,
    metrics_json TEXT NOT NULL,
    verdict_json TEXT,
    card_json TEXT,                       -- what the report and the interface show (the picks only)
    PRIMARY KEY(run_id, full_name)
);
"""
LESSON_FIELDS = ("status", "title", "voice", "video_path", "duration_s", "size_bytes", "run_id", "cost_usd",
                 "delivered_at", "requiz_at", "review", "comparison", "error")

_LLM_FIELDS = ("run_id", "task", "requested_model", "model", "provider", "generation_id",
               "input_tokens", "output_tokens", "reasoning_tokens", "cached_tokens",
               "cost_usd", "latency_ms", "status", "error")

_TRIAGE_FIELDS = ("reason", "total", "scores", "summary_pt", "why_it_matters_pt", "tags", "pre_score",
                  "classifier_version", "model", "prompt_version", "cost_usd")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _in(ids) -> str:
    return ",".join("?" * len(ids))


class Store:
    """One connection, shared by the triage worker threads (SQLite runs in serialized mode);
    the writes those threads make go through `_lock`."""

    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.create_function("fold", 1, fold, deterministic=True)   # accent-free search (graph/query.py)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.executescript(_SCHEMA_V2)
        self.conn.executescript(_SCHEMA_V3)
        self.conn.executescript(_SCHEMA_V4)
        self.conn.executescript(_SCHEMA_V5)
        self.conn.executescript(_SCHEMA_V6)
        columns ={row[1] for row in self.conn.execute("PRAGMA table_info(items)")}
        if "cluster_id" not in columns:
            self.conn.execute("ALTER TABLE items ADD COLUMN cluster_id TEXT")
        if "graph_synced_at" not in columns:
            self.conn.execute("ALTER TABLE items ADD COLUMN graph_synced_at TEXT")
        if "card_json" not in {row[1] for row in self.conn.execute("PRAGMA table_info(radar_picks)")}:
            self.conn.execute("ALTER TABLE radar_picks ADD COLUMN card_json TEXT")    # an early v6 store
        self.conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)",
                          (str(SCHEMA_VERSION),))
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # --- meta ---------------------------------------------------------------
    def meta_get(self, key, default=None):
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def meta_set(self, key, value) -> None:
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", (key, str(value)))
            self.conn.commit()

    # --- runs ---------------------------------------------------------------
    def start_run(self, kind: str) -> int:
        cur = self.conn.execute("INSERT INTO runs(kind, started_at) VALUES(?, ?)", (kind, utcnow()))
        self.conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, ok: bool, stats: dict, error: str | None = None) -> None:
        cost = self.conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE run_id = ?",
                                 (run_id,)).fetchone()[0]
        self.conn.execute(
            "UPDATE runs SET finished_at = ?, ok = ?, stats_json = ?, cost_usd = ?, error = ? WHERE id = ?",
            (utcnow(), int(ok), json.dumps(stats, ensure_ascii=False), cost, error, run_id))
        self.conn.commit()

    def last_run(self, kind: str | None = None):
        sql = "SELECT * FROM runs WHERE finished_at IS NOT NULL"
        args = ()
        if kind:
            sql += " AND kind = ?"
            args = (kind,)
        return self.conn.execute(sql + " ORDER BY id DESC LIMIT 1", args).fetchone()

    # --- items --------------------------------------------------------------
    def upsert_items(self, items, run_id: int) -> list[str]:
        """Insert unseen items; for known ids only merge concepts. Returns the ids that were new."""
        new_ids = []
        now = utcnow()
        for it in items:
            row = self.conn.execute("SELECT concepts_json FROM items WHERE id = ?", (it.id,)).fetchone()
            if row is not None:
                merged = json.loads(row["concepts_json"])
                merged += [c for c in it.concepts if c not in merged]
                self.conn.execute("UPDATE items SET concepts_json = ? WHERE id = ?",
                                  (json.dumps(merged, ensure_ascii=False), it.id))
                continue
            self.conn.execute(
                "INSERT INTO items(id, kind, source, source_id, canonical_url, doi, arxiv_id, pmid, title,"
                " authors_json, published_at, fetched_at, text, content_hash, concepts_json, profile,"
                " first_run_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (it.id, it.kind, it.source, it.source_id, it.url, it.doi, it.arxiv_id, it.pmid, it.title,
                 json.dumps(it.authors, ensure_ascii=False), it.published_at, now, it.text,
                 it.content_hash, json.dumps(it.concepts, ensure_ascii=False), it.profile, run_id))
            new_ids.append(it.id)
        self.conn.commit()
        return new_ids

    def requeue_manual(self, item_ids) -> int:
        """Items you sent to the bot that were already known (P5): they become yours (source manual:telegram)
        and, unless already approved, go back to the triage now. Returns how many go back."""
        ids = list(item_ids)
        if not ids:
            return 0
        with self._lock:
            self.conn.execute(f"UPDATE items SET source = 'manual:telegram', fetched_at = ? WHERE id IN ({_in(ids)})",
                              [utcnow()] + ids)
            cur = self.conn.execute(f"DELETE FROM triage WHERE item_id IN ({_in(ids)}) AND decision NOT IN "
                                    f"({_in(APPROVED)})", ids + list(APPROVED))
            self.conn.commit()
        return cur.rowcount

    def count_items(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]

    def get_items(self, ids):
        ids = list(ids)
        if not ids:
            return []
        rows = self.conn.execute(f"SELECT * FROM items WHERE id IN ({_in(ids)})", ids).fetchall()
        order = {i: n for n, i in enumerate(ids)}
        return sorted(rows, key=lambda r: order[r["id"]])

    def titles_since(self, since_iso):
        return self.conn.execute("SELECT id, title, cluster_id FROM items WHERE fetched_at >= ? ORDER BY fetched_at",
                                 (since_iso,)).fetchall()

    def join_cluster(self, item_id, representative_id) -> None:
        with self._lock:
            row = self.conn.execute("SELECT cluster_id FROM items WHERE id = ?", (representative_id,)).fetchone()
            cluster = (row["cluster_id"] if row else None) or representative_id
            self.conn.execute("INSERT OR IGNORE INTO clusters(id, representative_item_id, created_at) VALUES(?,?,?)",
                              (cluster, representative_id, utcnow()))
            self.conn.execute("UPDATE items SET cluster_id = ? WHERE id IN (?, ?)", (cluster, item_id, representative_id))
            self.conn.commit()

    def cluster_sources(self, item_id) -> list:
        row = self.conn.execute("SELECT cluster_id, source FROM items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return []
        if not row["cluster_id"]:
            return [row["source"]]
        rows = self.conn.execute("SELECT DISTINCT source FROM items WHERE cluster_id = ? ORDER BY source",
                                 (row["cluster_id"],)).fetchall()
        return [r[0] for r in rows]

    def redact_item(self, item_id) -> None:
        """Identifiable patient data: keep the id (so it is never fetched again), drop the content."""
        with self._lock:
            self.conn.execute("UPDATE items SET text = NULL, title = '[removido: dado de paciente]' WHERE id = ?",
                              (item_id,))
            self.conn.execute("DELETE FROM embeddings WHERE item_id = ?", (item_id,))
            self.conn.commit()

    # --- source health ------------------------------------------------------
    def record_source_ok(self, source: str) -> None:
        self.conn.execute(
            "INSERT INTO source_state(source, last_ok_at, consecutive_failures) VALUES(?, ?, 0)"
            " ON CONFLICT(source) DO UPDATE SET last_ok_at = excluded.last_ok_at, consecutive_failures = 0",
            (source, utcnow()))
        self.conn.commit()

    def record_source_error(self, source: str, error: str) -> int:
        self.conn.execute(
            "INSERT INTO source_state(source, last_error, last_error_at, consecutive_failures) VALUES(?, ?, ?, 1)"
            " ON CONFLICT(source) DO UPDATE SET last_error = excluded.last_error,"
            " last_error_at = excluded.last_error_at, consecutive_failures = consecutive_failures + 1",
            (source, error[:500], utcnow()))
        self.conn.commit()
        return self.conn.execute("SELECT consecutive_failures FROM source_state WHERE source = ?",
                                 (source,)).fetchone()[0]

    def source_states(self):
        return self.conn.execute("SELECT * FROM source_state ORDER BY source").fetchall()

    # --- LLM ledger ---------------------------------------------------------
    def record_llm_call(self, **fields) -> int:
        unknown = set(fields) - set(_LLM_FIELDS)
        if unknown:
            raise ValueError(f"unknown llm_calls fields: {sorted(unknown)}")
        cols = list(fields) + ["created_at"]
        vals = [fields[c] for c in fields] + [utcnow()]
        with self._lock:
            cur = self.conn.execute(
                f"INSERT INTO llm_calls({', '.join(cols)}) VALUES({', '.join('?' * len(cols))})", vals)
            self.conn.commit()
        return cur.lastrowid

    def llm_cost_since(self, since_iso: str) -> float:
        with self._lock:
            return self.conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE created_at >= ?",
                                     (since_iso,)).fetchone()[0]

    def llm_cost_for_run(self, run_id) -> float:
        with self._lock:
            return self.conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE run_id = ?",
                                     (run_id,)).fetchone()[0]

    def avg_llm_cost(self, task: str, last: int = 200) -> float | None:
        row = self.conn.execute(
            "SELECT AVG(cost_usd) FROM (SELECT cost_usd FROM llm_calls WHERE task = ? AND status = 'ok'"
            " ORDER BY id DESC LIMIT ?)", (task, last)).fetchone()
        return row[0]

    # --- triage -------------------------------------------------------------
    def triage_candidates(self, since_iso: str, max_attempts: int = 3):
        """Items fetched since `since_iso` with no decision yet, or whose triage errored < max_attempts."""
        return self.conn.execute(
            "SELECT i.* FROM items i LEFT JOIN triage t ON t.item_id = i.id WHERE i.fetched_at >= ?"
            " AND (t.item_id IS NULL OR (t.decision = 'error' AND t.attempts < ?)) ORDER BY i.fetched_at DESC",
            (since_iso, max_attempts)).fetchall()

    def record_triage(self, item_id, run_id, decision, **fields) -> None:
        unknown = set(fields) - set(_TRIAGE_FIELDS)
        if unknown:
            raise ValueError(f"unknown triage fields: {sorted(unknown)}")
        scores, tags = fields.pop("scores", None), fields.pop("tags", None)
        row = dict(fields, scores_json=json.dumps(scores) if scores is not None else None,
                   tags_json=json.dumps(tags, ensure_ascii=False) if tags is not None else None)
        cols = ["item_id", "run_id", "decision", "triaged_at"] + list(row)
        vals = [item_id, run_id, decision, utcnow()] + list(row.values())
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols[1:])
        with self._lock:
            self.conn.execute(
                f"INSERT INTO triage({', '.join(cols)}) VALUES({_in(cols)}) ON CONFLICT(item_id) DO UPDATE SET "
                f"{updates}, attempts = triage.attempts + 1", vals)
            self.conn.commit()

    def triage_rows(self, run_id, decisions=("main", "frontier", "radar")):
        decisions = list(decisions)
        return self.conn.execute(
            "SELECT t.*, i.title, i.canonical_url, i.source, i.profile, i.published_at FROM triage t"
            f" JOIN items i ON i.id = t.item_id WHERE t.run_id = ? AND t.decision IN ({_in(decisions)})",
            [run_id] + decisions).fetchall()

    def triage_counts(self, run_id) -> dict:
        rows = self.conn.execute("SELECT decision, COUNT(*) FROM triage WHERE run_id = ? GROUP BY decision",
                                 (run_id,)).fetchall()
        return {r[0]: r[1] for r in rows}

    # --- embeddings ---------------------------------------------------------
    def save_embeddings(self, model: str, pairs) -> None:
        now = utcnow()
        rows = [(item_id, model, int(vec.shape[0]), np.asarray(vec, dtype=np.float32).tobytes(), now)
                for item_id, vec in pairs]
        with self._lock:
            self.conn.executemany("INSERT OR REPLACE INTO embeddings(item_id, model, dim, vector, created_at)"
                                  " VALUES(?,?,?,?,?)", rows)
            self.conn.commit()

    def embedded_ids(self, model: str, ids) -> set:
        ids = list(ids)
        if not ids:
            return set()
        rows = self.conn.execute(f"SELECT item_id FROM embeddings WHERE model = ? AND item_id IN ({_in(ids)})",
                                 [model] + ids).fetchall()
        return {r[0] for r in rows}

    def load_embeddings(self, model: str, ids=None, since_iso=None, exclude=()):
        """-> (ids, float32 matrix of unit vectors). Filter by explicit ids or by items fetched since."""
        sql = "SELECT e.item_id, e.dim, e.vector FROM embeddings e JOIN items i ON i.id = e.item_id WHERE e.model = ?"
        args = [model]
        if ids is not None:
            ids = list(ids)
            if not ids:
                return [], np.zeros((0, 0), dtype=np.float32)
            sql += f" AND e.item_id IN ({_in(ids)})"
            args += ids
        if since_iso:
            sql += " AND i.fetched_at >= ?"
            args.append(since_iso)
        excluded = set(exclude)
        rows = [r for r in self.conn.execute(sql, args).fetchall() if r["item_id"] not in excluded]
        if not rows:
            return [], np.zeros((0, 0), dtype=np.float32)
        matrix = np.stack([np.frombuffer(r["vector"], dtype=np.float32, count=r["dim"]) for r in rows])
        return [r["item_id"] for r in rows], matrix

    # --- feedback -----------------------------------------------------------
    def add_feedback(self, target_type, target_id, value, channel, note=None) -> int:
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO feedback(target_type, target_id, value, note, channel, created_at) VALUES(?,?,?,?,?,?)",
                (target_type, target_id, value, note, channel, utcnow()))
            self.conn.commit()
        return cur.lastrowid

    def item_votes(self, profile=None, ids=None) -> dict:
        """Latest vote per item (a later vote replaces an earlier one)."""
        sql = ("SELECT f.target_id, f.value FROM feedback f JOIN items i ON i.id = f.target_id"
               " WHERE f.target_type = 'item'")
        args = []
        if profile:
            sql += " AND i.profile = ?"
            args.append(profile)
        if ids is not None:
            ids = list(ids)
            if not ids:
                return {}
            sql += f" AND f.target_id IN ({_in(ids)})"
            args += ids
        votes = {}
        for row in self.conn.execute(sql + " ORDER BY f.id", args):
            votes[row[0]] = row[1]
        return votes

    # --- deliveries ---------------------------------------------------------
    def record_delivery(self, run_id, day, item_id, key, section, position) -> int:
        cur = self.conn.execute(
            "INSERT INTO deliveries(run_id, day, item_id, key, section, position) VALUES(?,?,?,?,?,?)",
            (run_id, day, item_id, key, section, position))
        self.conn.commit()
        return cur.lastrowid

    def mark_delivered(self, delivery_ids, chat_id, message_id) -> None:
        ids = list(delivery_ids)
        if not ids:
            return
        self.conn.execute(f"UPDATE deliveries SET chat_id = ?, message_id = ?, sent_at = ? WHERE id IN ({_in(ids)})",
                          [str(chat_id), message_id, utcnow()] + ids)
        self.conn.commit()

    def delivery_by_key(self, key):
        return self.conn.execute("SELECT * FROM deliveries WHERE key = ? ORDER BY id DESC LIMIT 1", (key,)).fetchone()

    def deliveries_for_message(self, chat_id, message_id):
        return self.conn.execute("SELECT * FROM deliveries WHERE chat_id = ? AND message_id = ? ORDER BY position",
                                 (str(chat_id), message_id)).fetchall()

    # --- classifiers --------------------------------------------------------
    def record_classifier(self, version, profile, embed_model, n_labels, metrics, path) -> None:
        self.conn.execute(
            "INSERT INTO classifier_models(version, profile, embed_model, trained_at, n_labels, metrics_json, path)"
            " VALUES(?,?,?,?,?,?,?)",
            (version, profile, embed_model, utcnow(), n_labels, json.dumps(metrics), str(path)))
        self.conn.commit()

    def latest_classifier(self, profile, embed_model):
        return self.conn.execute(
            "SELECT * FROM classifier_models WHERE profile = ? AND embed_model = ? ORDER BY trained_at DESC,"
            " rowid DESC LIMIT 1", (profile, embed_model)).fetchone()

    # --- inbox --------------------------------------------------------------
    def add_inbox(self, channel, payload) -> int:
        cur = self.conn.execute("INSERT INTO inbox(channel, payload_json, received_at) VALUES(?,?,?)",
                                (channel, json.dumps(payload, ensure_ascii=False), utcnow()))
        self.conn.commit()
        return cur.lastrowid

    # --- extraction (schema 3) ----------------------------------------------
    def record_extraction(self, item_id, run_id, status, model=None, prompt_version=None, payload=None,
                          error=None, cost_usd=0.0) -> None:
        payload_json = json.dumps(payload, ensure_ascii=False) if payload is not None else None
        with self._lock:
            self.conn.execute(
                "INSERT INTO extractions(item_id, run_id, status, model, prompt_version, payload_json, error, cost_usd,"
                " extracted_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET"
                " run_id = excluded.run_id, status = excluded.status, model = excluded.model,"
                " prompt_version = excluded.prompt_version, payload_json = excluded.payload_json,"
                " error = excluded.error, cost_usd = excluded.cost_usd, extracted_at = excluded.extracted_at,"
                " attempts = extractions.attempts + 1",
                (item_id, run_id, status, model, prompt_version, payload_json, error, cost_usd, utcnow()))
            self.conn.commit()

    def get_extraction(self, item_id):
        return self.conn.execute("SELECT * FROM extractions WHERE item_id = ?", (item_id,)).fetchone()

    def extraction_candidates(self, max_attempts=3, limit=None):
        """Approved items (main, frontier, radar) with no good extraction yet, or whose extraction errored
        fewer than `max_attempts` times: main first, then frontier and radar, newest first."""
        sql = ("SELECT i.*, t.decision, t.tags_json FROM items i JOIN triage t ON t.item_id = i.id"
               " LEFT JOIN extractions x ON x.item_id = i.id"
               f" WHERE t.decision IN ({_in(APPROVED)})"
               " AND (x.item_id IS NULL OR (x.status = 'error' AND x.attempts < ?))"
               " ORDER BY CASE t.decision WHEN 'main' THEN 0 WHEN 'frontier' THEN 1 ELSE 2 END, i.fetched_at DESC")
        args = list(APPROVED) + [max_attempts]
        if limit:
            sql += " LIMIT ?"
            args.append(int(limit))
        return self.conn.execute(sql, args).fetchall()

    def approved_items(self):
        """(item_id, tags_json, fetched_at) of every approved item, oldest first."""
        return self.conn.execute(
            f"SELECT t.item_id, t.tags_json, i.fetched_at FROM triage t JOIN items i ON i.id = t.item_id"
            f" WHERE t.decision IN ({_in(APPROVED)}) ORDER BY i.fetched_at", list(APPROVED)).fetchall()

    # --- entities (schema 3) ------------------------------------------------
    def add_entity(self, type_, name, norm, category=None) -> int:
        """Id of the entity (type, norm), created when missing."""
        with self._lock:
            self.conn.execute("INSERT OR IGNORE INTO entities(type, name, norm, category, created_at) VALUES(?,?,?,?,?)",
                              (type_, name, norm, category, utcnow()))
            self.conn.commit()
            return self.conn.execute("SELECT id FROM entities WHERE type = ? AND norm = ?", (type_, norm)).fetchone()[0]

    def get_entity(self, entity_id):
        return self.conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()

    def entities_of_types(self, types):
        types = list(types)
        return self.conn.execute(f"SELECT * FROM entities WHERE type IN ({_in(types)}) ORDER BY id", types).fetchall()

    def add_alias(self, grp, alias_norm, entity_id, alias) -> bool:
        """False when the alias already points somewhere (the first entity keeps it)."""
        with self._lock:
            cur = self.conn.execute("INSERT OR IGNORE INTO entity_aliases(grp, alias_norm, entity_id, alias)"
                                    " VALUES(?,?,?,?)", (grp, alias_norm, entity_id, alias))
            self.conn.commit()
            return cur.rowcount == 1

    def entity_context(self, entity_id) -> str:
        """Title of the latest item that mentions the entity (context for the resolution judge)."""
        row = self.conn.execute("SELECT i.title FROM entity_mentions m JOIN items i ON i.id = m.item_id"
                                " WHERE m.entity_id = ? ORDER BY i.fetched_at DESC LIMIT 1", (entity_id,)).fetchone()
        return row[0] if row else ""

    def entity_by_alias(self, grp, alias_norm):
        return self.conn.execute("SELECT e.* FROM entity_aliases a JOIN entities e ON e.id = a.entity_id"
                                 " WHERE a.grp = ? AND a.alias_norm = ?", (grp, alias_norm)).fetchone()

    def _dirty(self, item_id) -> None:
        self.conn.execute("UPDATE items SET graph_synced_at = NULL WHERE id = ?", (item_id,))

    def add_mention(self, item_id, entity_id, role, seen) -> bool:
        """True for a new (item, entity) pair: the entity counts the item once and widens its first/last
        seen. A repeated pair only promotes the role (mentioned < used < main), never demotes it."""
        with self._lock:
            cur = self.conn.execute("INSERT OR IGNORE INTO entity_mentions(item_id, entity_id, role) VALUES(?,?,?)",
                                    (item_id, entity_id, role))
            if cur.rowcount == 1:
                self.conn.execute(
                    "UPDATE entities SET mention_count = mention_count + 1,"
                    " first_seen = CASE WHEN first_seen IS NULL OR ? < first_seen THEN ? ELSE first_seen END,"
                    " last_seen = CASE WHEN last_seen IS NULL OR ? > last_seen THEN ? ELSE last_seen END WHERE id = ?",
                    (seen, seen, seen, seen, entity_id))
                self._dirty(item_id)
                self.conn.commit()
                return True
            current = self.conn.execute("SELECT role FROM entity_mentions WHERE item_id = ? AND entity_id = ?",
                                        (item_id, entity_id)).fetchone()[0]
            if ROLE_RANK.get(role, 0) > ROLE_RANK.get(current, 0):
                self.conn.execute("UPDATE entity_mentions SET role = ? WHERE item_id = ? AND entity_id = ?",
                                  (role, item_id, entity_id))
                self._dirty(item_id)
            self.conn.commit()
            return False

    def add_relation(self, subject_id, predicate, object_id, item_id) -> bool:
        with self._lock:
            cur = self.conn.execute("INSERT OR IGNORE INTO entity_relations(subject_id, predicate, object_id, item_id,"
                                    " created_at) VALUES(?,?,?,?,?)", (subject_id, predicate, object_id, item_id, utcnow()))
            if cur.rowcount == 1:
                self._dirty(item_id)
            self.conn.commit()
            return cur.rowcount == 1

    def relations_of_item(self, item_id) -> list:
        rows = self.conn.execute("SELECT subject_id, predicate, object_id FROM entity_relations WHERE item_id = ?"
                                 " ORDER BY subject_id, predicate, object_id", (item_id,)).fetchall()
        return [tuple(r) for r in rows]

    def record_merge(self, entity_id, name, method, score=None, item_id=None) -> int:
        with self._lock:
            cur = self.conn.execute("INSERT INTO entity_merges(entity_id, name, item_id, method, score, decided_at)"
                                    " VALUES(?,?,?,?,?,?)", (entity_id, name, item_id, method, score, utcnow()))
            self.conn.commit()
            return cur.lastrowid

    def save_entity_embeddings(self, model, pairs) -> None:
        rows = [(entity_id, model, int(vec.shape[0]), np.asarray(vec, dtype=np.float32).tobytes())
                for entity_id, vec in pairs]
        with self._lock:
            self.conn.executemany("INSERT OR REPLACE INTO entity_embeddings(entity_id, model, dim, vector)"
                                  " VALUES(?,?,?,?)", rows)
            self.conn.commit()

    def load_entity_embeddings(self, model, ids) -> dict:
        ids = list(ids)
        if not ids:
            return {}
        rows = self.conn.execute(f"SELECT entity_id, dim, vector FROM entity_embeddings WHERE model = ?"
                                 f" AND entity_id IN ({_in(ids)})", [model] + ids).fetchall()
        return {r[0]: np.frombuffer(r[2], dtype=np.float32, count=r[1]) for r in rows}

    # --- Neo4j mirror watermark (schema 3) ----------------------------------
    def graph_dirty_items(self, limit=None) -> list:
        """Approved items with graph content that changed since the last mirror sync, oldest first."""
        sql = (f"SELECT i.id FROM items i JOIN triage t ON t.item_id = i.id WHERE t.decision IN ({_in(APPROVED)})"
               " AND i.graph_synced_at IS NULL AND EXISTS (SELECT 1 FROM entity_mentions m WHERE m.item_id = i.id)"
               " ORDER BY i.fetched_at, i.id")
        args = list(APPROVED)
        if limit:
            sql += " LIMIT ?"
            args.append(int(limit))
        return [r[0] for r in self.conn.execute(sql, args).fetchall()]

    def mark_graph_synced(self, item_ids, when=None) -> None:
        ids = list(item_ids)
        if not ids:
            return
        with self._lock:
            self.conn.execute(f"UPDATE items SET graph_synced_at = ? WHERE id IN ({_in(ids)})", [when or utcnow()] + ids)
            self.conn.commit()

    def mark_all_graph_dirty(self) -> None:
        with self._lock:
            self.conn.execute("UPDATE items SET graph_synced_at = NULL")
            self.conn.commit()

    # --- idea ledger (schema 4) ---------------------------------------------
    def add_idea(self, run_id, title, card, lens=None, persona=None, niche=None, candidate=None, parent_id=None,
                 embedding=None, status="nova") -> int:
        version = 1
        if parent_id is not None:
            parent = self.get_idea(parent_id)
            version = (parent["version"] + 1) if parent is not None else 1
        blob = np.asarray(embedding, dtype=np.float32).tobytes() if embedding is not None else None
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO ideas(version, parent_id, run_id, created_at, status, title, lens, persona, niche,"
                " candidate_json, card_json, embedding) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (version, parent_id, run_id, utcnow(), status, title, lens, persona, niche,
                 json.dumps(candidate, ensure_ascii=False) if candidate is not None else None,
                 json.dumps(card, ensure_ascii=False), blob))
            self.conn.commit()
            return cur.lastrowid

    def update_idea(self, idea_id, **fields) -> None:
        columns = {"score": "score", "status": "status", "selected": "selected", "discard_reason": "discard_reason",
                   "title": "title", "niche": "niche"}
        json_columns = {"scores": "scores_json", "critique": "critique_json", "novelty": "novelty_json",
                        "card": "card_json", "candidate": "candidate_json"}
        unknown = set(fields) - set(columns) - set(json_columns)
        if unknown:
            raise ValueError(f"unknown idea fields: {sorted(unknown)}")
        sets, values = [], []
        for key, value in fields.items():
            if key in json_columns:
                sets.append(f"{json_columns[key]} = ?")
                values.append(json.dumps(value, ensure_ascii=False))
            else:
                sets.append(f"{columns[key]} = ?")
                values.append(int(value) if key == "selected" else value)
        with self._lock:
            self.conn.execute(f"UPDATE ideas SET {', '.join(sets)} WHERE id = ?", values + [idea_id])
            self.conn.commit()

    def get_idea(self, idea_id):
        return self.conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone()

    def idea_embedding(self, idea_id):
        row = self.conn.execute("SELECT embedding FROM ideas WHERE id = ?", (idea_id,)).fetchone()
        return np.frombuffer(row[0], dtype=np.float32) if row and row[0] else None

    def list_ideas(self, status=None, run_id=None, selected=None, limit=200):
        sql, args = "SELECT * FROM ideas WHERE 1 = 1", []
        for column, value in (("status", status), ("run_id", run_id)):
            if value is not None:
                sql += f" AND {column} = ?"
                args.append(value)
        if selected is not None:
            sql += " AND selected = ?"
            args.append(int(selected))
        return self.conn.execute(sql + " ORDER BY COALESCE(score, 0) DESC, id DESC LIMIT ?", args + [limit]).fetchall()

    def vote_idea(self, idea_id, value, channel, note=None) -> str:
        """Records the vote and moves the idea to the matching status; returns the new status."""
        status = IDEA_STATUS[value]
        self.add_feedback("idea", str(idea_id), value, channel, note=note)
        self.update_idea(idea_id, status=status)
        return status

    # --- communities and weekly reports (schema 4) --------------------------
    def save_communities(self, run_id, assignments, labels) -> None:
        """assignments: {entity_id: community}; labels: {community: (label, summary, size, top_entity_id)}."""
        with self._lock:
            self.conn.executemany("INSERT OR REPLACE INTO entity_communities(run_id, entity_id, community) VALUES(?,?,?)",
                                  [(run_id, e, c) for e, c in assignments.items()])
            self.conn.executemany("INSERT OR REPLACE INTO communities(run_id, community, label, summary, size, top_entity_id)"
                                  " VALUES(?,?,?,?,?,?)", [(run_id, c, *values) for c, values in labels.items()])
            self.conn.commit()

    def latest_communities(self):
        run = self.conn.execute("SELECT MAX(run_id) FROM communities").fetchone()[0]
        if run is None:
            return []
        return self.conn.execute("SELECT * FROM communities WHERE run_id = ? ORDER BY community", (run,)).fetchall()

    def entity_community(self, entity_id):
        row = self.conn.execute("SELECT community FROM entity_communities WHERE entity_id = ? ORDER BY run_id DESC"
                                " LIMIT 1", (entity_id,)).fetchone()
        return row[0] if row else None

    def save_weekly_report(self, run_id, day, payload) -> None:
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO weekly_reports(run_id, day, payload_json, created_at) VALUES(?,?,?,?)",
                              (run_id, day, json.dumps(payload, ensure_ascii=False), utcnow()))
            self.conn.commit()

    def latest_weekly_report(self, kind=None):
        """kind: "weekly" or "ideate" (the run that produced the report); None = any."""
        if kind:
            row = self.conn.execute("SELECT w.* FROM weekly_reports w JOIN runs r ON r.id = w.run_id WHERE r.kind = ? "
                                    "ORDER BY w.run_id DESC LIMIT 1", (kind,)).fetchone()
        else:
            row = self.conn.execute("SELECT * FROM weekly_reports ORDER BY run_id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return {"run_id": row["run_id"], "day": row["day"], "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"]}

    # --- lessons (schema 5) -------------------------------------------------
    def create_lesson(self, topic, entity_ids=()) -> int:
        with self._lock:
            cur = self.conn.execute("INSERT INTO lessons(created_at, updated_at, topic, entities_json) VALUES(?,?,?,?)",
                                    (utcnow(), utcnow(), topic, json.dumps([int(e) for e in entity_ids])))
            self.conn.commit()
            return cur.lastrowid

    def update_lesson(self, lesson_id, plan=None, report=None, **fields) -> None:
        unknown = set(fields) - set(LESSON_FIELDS)
        if unknown:
            raise ValueError(f"unknown lesson fields: {sorted(unknown)}")
        sets, values = ["updated_at = ?"], [utcnow()]
        for key, value in fields.items():
            sets.append(f"{key} = ?")
            values.append(value)
        for column, value in (("plan_json", plan), ("report_json", report)):
            if value is not None:
                sets.append(f"{column} = ?")
                values.append(json.dumps(value, ensure_ascii=False))
        with self._lock:
            self.conn.execute(f"UPDATE lessons SET {', '.join(sets)} WHERE id = ?", values + [lesson_id])
            self.conn.commit()

    def get_lesson(self, lesson_id):
        return self.conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()

    def list_lessons(self, limit=100):
        return self.conn.execute("SELECT * FROM lessons ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def taught_entities(self) -> set:
        """Entities that already have a lesson that did not fail (the selector skips them)."""
        out = set()
        for row in self.conn.execute("SELECT entities_json FROM lessons WHERE status != 'falhou'"):
            out.update(json.loads(row[0] or "[]"))
        return out

    def record_lesson_answer(self, lesson_id, round_, question, chosen, correct) -> bool:
        """The first answer to a question counts; returns False when it was already answered."""
        with self._lock:
            cur = self.conn.execute("INSERT OR IGNORE INTO lesson_answers(lesson_id, round, question, chosen, correct,"
                                    " answered_at) VALUES(?,?,?,?,?,?)",
                                    (lesson_id, round_, question, chosen, int(bool(correct)), utcnow()))
            self.conn.commit()
            return cur.rowcount == 1

    def lesson_score(self, lesson_id, round_) -> tuple:
        row = self.conn.execute("SELECT COALESCE(SUM(correct), 0), COUNT(*) FROM lesson_answers WHERE lesson_id = ?"
                                " AND round = ?", (lesson_id, round_)).fetchone()
        return int(row[0]), int(row[1])

    def lessons_due_requiz(self, before_iso):
        """Delivered before `before_iso` and not re-quizzed yet."""
        return self.conn.execute("SELECT * FROM lessons WHERE delivered_at IS NOT NULL AND delivered_at <= ? AND"
                                 " requiz_at IS NULL ORDER BY id", (before_iso,)).fetchall()
