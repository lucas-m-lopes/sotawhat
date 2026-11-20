# sotawhat/rag/index.py
"""The passages the retrieval searches (SDD §6.15), kept in `rag_passages` of the SQLite store.

Kinds:
- card: one per approved item: title, summary and "why it matters" in pt-BR, its numbers, its entities and
  its triage categories. What a question in Portuguese meets first;
- text: the item's own text (mostly English) in chunks of about 1,100 characters, for the details the
  summary leaves out;
- entity: the name and aliases of each entity, to link a question to the graph when the words differ
  ("sepse" finds "sepsis early detection");
- community: label and summary of each community of the last weekly run (questions about themes);
- idea: the finalists and the ideas you voted for; glossary: the terms of the digests.

`refresh` compares what the store holds now with what is indexed: an unchanged passage keeps its vector, a
changed one is embedded again, one whose source is gone is deleted. It runs after the graph stage of the
daily run (seconds for a day's items) and can stop at any point: what is missing is embedded next time.
Vectors use the retrieval prompts of the embedding model (store/vectors.py); nothing here calls an LLM."""
import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass

import numpy as np

from sotawhat import taxonomy as tx
from sotawhat.graph.query import ENTITY_TYPES, TYPE_LABELS
from sotawhat.store.db import APPROVED, utcnow
from sotawhat.store.vectors import passage_text

ITEM_KINDS = ("card", "text")
KINDS = ITEM_KINDS + ("entity", "community", "idea", "glossary")
CHUNK, MAX_CHUNKS, MIN_TEXT = 1100, 8, 400
IDEA_STATUSES = ("curtida", "testar", "engavetada", "construida")
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-ZÀ-Ý0-9])|\n{2,}")
_IN = ",".join("?" * len(APPROVED))
log = logging.getLogger("sotawhat.rag")


@dataclass(frozen=True)
class Passage:
    kind: str
    ref: str
    seq: int
    item_id: str | None
    title: str
    body: str
    day: str | None

    @property
    def key(self) -> tuple:
        return self.kind, self.ref, self.seq

    @property
    def hash(self) -> str:
        return hashlib.sha1(f"{self.title}\n{self.body}".encode("utf-8")).hexdigest()


@dataclass
class IndexStats:
    passages: int = 0
    added: int = 0
    changed: int = 0
    removed: int = 0
    embedded: int = 0
    pending: int = 0        # passages still without a vector (the embedder failed or was not given)
    lexical: bool = True

    def as_dict(self) -> dict:
        return asdict(self)


def chunks(text, size=CHUNK, limit=MAX_CHUNKS) -> list:
    """The text in pieces of at most `size` characters, cut at sentence ends; each piece starts with the last
    sentence of the one before, so a fact split by the cut is whole in one of them."""
    text = " ".join((text or "").split()) if "\n\n" not in (text or "") else (text or "").strip()
    sentences = [s.strip() for s in _SENTENCE.split(text) if s and s.strip()]
    pieces, current = [], []
    for sentence in sentences:
        while len(sentence) > size:                      # a "sentence" longer than a chunk: cut it at a space
            cut = sentence.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            sentences_head, sentence = sentence[:cut].strip(), sentence[cut:].strip()
            if current:
                pieces.append(" ".join(current))
                current = []
            pieces.append(sentences_head)
        if current and len(" ".join(current)) + 1 + len(sentence) > size:
            pieces.append(" ".join(current))
            current = [current[-1]] if len(current[-1]) < size // 3 else []
        current.append(sentence)
    if current:
        pieces.append(" ".join(current))
    return [p for p in pieces if p][:limit]


def _labels(keys) -> str:
    return ", ".join(tx.label(k) for k in keys or [])


def _item_passages(store):
    names = {}
    for item_id, name, role in store.conn.execute(
            "SELECT m.item_id, e.name, m.role FROM entity_mentions m JOIN entities e ON e.id = m.entity_id"
            f" WHERE m.role IN ('main', 'used') AND e.type IN ({','.join('?' * len(ENTITY_TYPES))})"
            " ORDER BY m.item_id, CASE m.role WHEN 'main' THEN 0 ELSE 1 END, e.mention_count DESC", list(ENTITY_TYPES)):
        names.setdefault(item_id, []).append(name)
    rows = store.conn.execute(
        "SELECT i.id, i.title, i.text, i.fetched_at, t.summary_pt, t.why_it_matters_pt, t.tags_json, x.payload_json"
        " FROM items i JOIN triage t ON t.item_id = i.id LEFT JOIN extractions x ON x.item_id = i.id AND x.status = 'ok'"
        f" WHERE t.decision IN ({_IN}) ORDER BY i.fetched_at, i.id", list(APPROVED))
    for r in rows:
        tags = json.loads(r["tags_json"] or "{}")
        claims = [c.get("text_pt") for c in json.loads(r["payload_json"] or "{}").get("claims", []) if c.get("text_pt")]
        parts = [r["summary_pt"] or ""]
        if r["why_it_matters_pt"]:
            parts.append(f"Por que importa: {r['why_it_matters_pt']}")
        if claims:
            parts.append("Números: " + " ".join(claims[:5]))
        if names.get(r["id"]):
            parts.append("Entidades: " + ", ".join(names[r["id"]][:10]))
        categories = ", ".join(x for x in (_labels(tags.get("domains")), _labels(tags.get("techniques")),
                                           _labels(tags.get("problem_types"))) if x)
        if categories:
            parts.append(f"Categorias: {categories}")
        body = "\n".join(p for p in parts if p.strip())
        if body:
            yield Passage("card", r["id"], 0, r["id"], r["title"], body, r["fetched_at"])
        text = (r["text"] or "").strip()
        if len(text) >= MIN_TEXT:
            for seq, piece in enumerate(chunks(text)):
                yield Passage("text", r["id"], seq, r["id"], r["title"], piece, r["fetched_at"])


def _entity_passages(store):
    aliases = {}
    for entity_id, alias in store.conn.execute("SELECT entity_id, alias FROM entity_aliases ORDER BY entity_id, alias"):
        aliases.setdefault(entity_id, []).append(alias)
    types = list(TYPE_LABELS)
    for r in store.conn.execute(f"SELECT * FROM entities WHERE type IN ({','.join('?' * len(types))}) AND mention_count > 0"
                                " ORDER BY id", types):
        other = [a for a in aliases.get(r["id"], []) if a.lower() != r["name"].lower()][:6]
        body = TYPE_LABELS.get(r["type"], r["type"])
        if other:
            body += "; também: " + ", ".join(other)
        if r["category"] and r["type"] in ENTITY_TYPES:
            body += f"; {tx.label(r['category'])}"
        yield Passage("entity", str(r["id"]), 0, None, r["name"], body, None)


def _other_passages(store):
    names = dict(store.conn.execute("SELECT id, name FROM entities").fetchall())
    for c in store.latest_communities():
        members = [names[r[0]] for r in store.conn.execute(
            "SELECT ec.entity_id FROM entity_communities ec JOIN entities e ON e.id = ec.entity_id WHERE ec.run_id = ?"
            " AND ec.community = ? ORDER BY e.mention_count DESC LIMIT 12", (c["run_id"], c["community"])) if r[0] in names]
        body = (c["summary"] or "") + (f"\nEntidades centrais: {', '.join(members)}" if members else "")
        if body.strip():
            yield Passage("community", str(c["community"]), 0, None, c["label"] or f"comunidade {c['community']}", body, None)
    marks = ",".join("?" * len(IDEA_STATUSES))
    for r in store.conn.execute(f"SELECT * FROM ideas WHERE selected = 1 OR status IN ({marks}) ORDER BY id",
                                list(IDEA_STATUSES)):
        draft = (json.loads(r["card_json"] or "{}").get("draft") or {})
        parts = [f"Situação: {r['status']}", f"Problema: {draft.get('problema_jtbd', '')}",
                 f"Mecanismo: {draft.get('mecanismo', '')}", f"Técnicas: {', '.join(draft.get('tecnicas') or [])}",
                 f"Por que agora: {draft.get('why_now', '')}", f"Modelo de negócio: {draft.get('modelo_negocio', '')}"]
        yield Passage("idea", str(r["id"]), 0, None, r["title"], "\n".join(p for p in parts if not p.endswith(": ")),
                      r["created_at"])
    for r in store.glossary_terms():
        title = f"{r['term']} ({r['expansion']})" if r["expansion"] else r["term"]
        yield Passage("glossary", str(r["id"]), 0, None, title, r["definition_pt"], None)


def wanted(store):
    yield from _item_passages(store)
    yield from _entity_passages(store)
    yield from _other_passages(store)


def _fts(store, passage_id, title=None, body=None) -> None:
    if not store.fts:
        return
    store.conn.execute("DELETE FROM rag_fts WHERE rowid = ?", (passage_id,))
    if body is not None:
        store.conn.execute("INSERT INTO rag_fts(rowid, title, body) VALUES(?,?,?)", (passage_id, title or "", body))


def embed_pending(store, embedder, batch=32, progress=None) -> int:
    """Embeds the passages with no vector of this embedder; commits per batch, so it can be interrupted."""
    done = 0
    while True:
        rows = store.conn.execute("SELECT id, title, body FROM rag_passages WHERE vector IS NULL OR model IS NOT ?"
                                  " ORDER BY id LIMIT ?", (embedder.name, batch)).fetchall()
        if not rows:
            return done
        vectors = embedder.embed([passage_text(embedder.name, r["title"], r["body"]) for r in rows], raw=True)
        with store._lock:
            store.conn.executemany(
                "UPDATE rag_passages SET model = ?, dim = ?, vector = ? WHERE id = ?",
                [(embedder.name, int(v.shape[0]), np.asarray(v, dtype=np.float32).tobytes(), r["id"])
                 for r, v in zip(rows, vectors)])
            store.conn.commit()
        done += len(rows)
        if progress:
            progress(done)


def refresh(store, embedder=None, rebuild=False, batch=32, progress=None) -> IndexStats:
    stats = IndexStats(lexical=bool(store.fts))
    with store._lock:
        if rebuild:
            store.conn.execute("DELETE FROM rag_passages")
            if store.fts:
                store.conn.execute("DELETE FROM rag_fts")
        have = {(r["kind"], r["ref"], r["seq"]): (r["id"], r["hash"])
                for r in store.conn.execute("SELECT id, kind, ref, seq, hash FROM rag_passages")}
        seen = set()
        for p in wanted(store):
            seen.add(p.key)
            known = have.get(p.key)
            if known is not None and known[1] == p.hash:
                continue
            if known is None:
                cur = store.conn.execute(
                    "INSERT INTO rag_passages(kind, ref, seq, item_id, title, body, day, hash) VALUES(?,?,?,?,?,?,?,?)",
                    (p.kind, p.ref, p.seq, p.item_id, p.title, p.body, p.day, p.hash))
                _fts(store, cur.lastrowid, p.title, p.body)
                stats.added += 1
            else:
                store.conn.execute("UPDATE rag_passages SET item_id = ?, title = ?, body = ?, day = ?, hash = ?,"
                                   " vector = NULL, model = NULL, dim = NULL WHERE id = ?",
                                   (p.item_id, p.title, p.body, p.day, p.hash, known[0]))
                _fts(store, known[0], p.title, p.body)
                stats.changed += 1
        for key, (passage_id, _) in have.items():
            if key not in seen:
                store.conn.execute("DELETE FROM rag_passages WHERE id = ?", (passage_id,))
                _fts(store, passage_id)
                stats.removed += 1
        store.conn.commit()
    if embedder is not None:
        try:
            stats.embedded = embed_pending(store, embedder, batch=batch, progress=progress)
        except Exception as exc:  # noqa: BLE001 - e.g. the model download failed: the lexical index still works
            log.warning("rag embeddings: %s", exc)
    stats.passages = store.conn.execute("SELECT COUNT(*) FROM rag_passages").fetchone()[0]
    stats.pending = store.conn.execute("SELECT COUNT(*) FROM rag_passages WHERE vector IS NULL").fetchone()[0]
    store.meta_set("rag_indexed_at", utcnow())
    return stats


def status(store) -> dict:
    by_kind = {r[0]: {"passages": r[1], "embedded": r[2]} for r in store.conn.execute(
        "SELECT kind, COUNT(*), SUM(vector IS NOT NULL) FROM rag_passages GROUP BY kind")}
    approved = store.conn.execute(f"SELECT COUNT(*) FROM triage WHERE decision IN ({_IN})", list(APPROVED)).fetchone()[0]
    return {"indexed_at": store.meta_get("rag_indexed_at"), "kinds": by_kind, "approved_items": approved,
            "items_indexed": (by_kind.get("card") or {}).get("passages", 0), "lexical": bool(store.fts),
            "models": [r[0] for r in store.conn.execute("SELECT DISTINCT model FROM rag_passages WHERE model IS NOT NULL")]}


def render_line(stats) -> str:
    parts = [f"rag: {stats.passages} passagens"]
    if stats.added or stats.changed or stats.removed:
        parts.append(f"+{stats.added} novas · {stats.changed} refeitas · {stats.removed} removidas")
    if stats.embedded:
        parts.append(f"{stats.embedded} vetores")
    if stats.pending:
        parts.append(f"{stats.pending} sem vetor")
    if not stats.lexical:
        parts.append("sem FTS5 (só busca densa)")
    return " · ".join(parts)
