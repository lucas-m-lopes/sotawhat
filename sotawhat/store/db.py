# sotawhat/store/db.py
"""SQLite operational store (SDD §6.4): items, runs, source health and LLM cost ledger."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1

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

_LLM_FIELDS = ("run_id", "task", "requested_model", "model", "provider", "generation_id",
               "input_tokens", "output_tokens", "reasoning_tokens", "cached_tokens",
               "cost_usd", "latency_ms", "status", "error")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)",
                          (str(SCHEMA_VERSION),))
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

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
        cur = self.conn.execute(
            f"INSERT INTO llm_calls({', '.join(cols)}) VALUES({', '.join('?' * len(cols))})", vals)
        self.conn.commit()
        return cur.lastrowid

    def llm_cost_since(self, since_iso: str) -> float:
        return self.conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE created_at >= ?",
                                 (since_iso,)).fetchone()[0]
