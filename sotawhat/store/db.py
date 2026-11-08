# sotawhat/store/db.py
"""SQLite operational store (SDD §6.4): items, runs, source health, LLM cost ledger and, since
schema 2 (P1), triage, embeddings, clusters, feedback, deliveries, classifiers and the inbox."""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SCHEMA_VERSION = 2

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
    decision TEXT NOT NULL,          -- main | radar | reject | muted | duplicate | gated | error
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
    section TEXT NOT NULL,           -- main | radar
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
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.executescript(_SCHEMA_V2)
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(items)")}
        if "cluster_id" not in columns:
            self.conn.execute("ALTER TABLE items ADD COLUMN cluster_id TEXT")
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

    def triage_rows(self, run_id, decisions=("main", "radar")):
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
