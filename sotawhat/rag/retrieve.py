# sotawhat/rag/retrieve.py
"""Hybrid retrieval over the knowledge graph (SDD §6.15): what a question gets before a small model answers.

A small model answers well only from a short, precise context, so the work is here and none of it needs an LLM:

1. the question: a time window written in Portuguese ("esta semana", "últimos 30 dias") becomes a filter, and
   words like "quantos", "mais citados" or "em alta" ask for numbers that are computed from the graph instead
   of being left to the model;
2. entity linking: names and aliases written in the question (exact, longest first) and entities whose name
   is close in meaning (dense, so "sepse" finds "sepsis early detection");
3. six rankings of the approved items:
   - dense: cosine between the question and the passages (cards in pt-BR, text chunks mostly in English);
   - bm25: SQLite FTS5 over the same passages, the question's words plus the names of the linked entities
     (the lexical bridge from a Portuguese question to English text);
   - graph: personalized PageRank from the linked entities over the entity graph (co-occurrence and typed
     relations), then the items by the probability mass of the entities they mention: the multi-hop channel
     ("which techniques address sepsis" reaches items that never write the question's words);
   - mention: the items that mention a linked entity, the ones about it first;
   - relation: the items that state a typed relation of a linked entity ("X addresses sepsis", "X developed
     by Google"), the ones that state the most first: what a "which ... / who ..." question is after;
   - category: the items the triage tagged with a linked category (domain, problem type, technique family);
4. reciprocal rank fusion of the six, then a multilingual cross-encoder rereads the best candidates;
5. the context pack: facts stated by the graph (entity cards with relations, counts, rankings, trends,
   communities) and numbered sources (card + the closest chunk of the item's text).

Everything is read from SQLite (`rag_passages`, the entity tables), so it runs wherever a copy of the store is."""
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np

from sotawhat.graph import intelligence as intel
from sotawhat.graph import query as q
from sotawhat.graph.resolve import GENERIC, normalize
from sotawhat.store.db import APPROVED
from sotawhat.store.vectors import query_text
from sotawhat.textmatch import fold

# Measured on 2026-11-20 with 40 questions written from the items (`sotawhat rag eval`): the dense ranking alone put
# the right item first in 95%, BM25 in 82%, the graph rankings in 42-55% (they are for questions about relations,
# which that set does not have). Hence dense counts double; with these weights every right item was within the
# first 16 of the fusion, and the cross-encoder brought 95% of them to the first place reading only 10.
WEIGHTS = {"dense": 2.0, "bm25": 1.0, "relation": 0.7, "mention": 0.6, "graph": 0.4, "category": 0.2}
RRF_K = 60
POOL = 40                 # items each ranking contributes
RERANK_TOP = 10           # candidates the cross-encoder reads (16 gave the same result and took 2 s more)
RERANK_WEIGHT = 0.7       # final = 0.7 · cross-encoder + 0.3 · fusion (the graph evidence it cannot see)
# Cosine thresholds per embedding model: (the closest entity is linked from here, the next ones from here and
# only this close to the first, below this the best passage means the graph has nothing on the question).
# EmbeddingGemma, measured on 2026-11-20 with questions in Portuguese against English names: the right entity
# came first with 0.36 to 0.56, an off-topic question peaked at 0.24; the best passage of an on-topic question
# had 0.44 to 0.63, of an off-topic one 0.21 to 0.22.
THRESHOLDS = {"google/embeddinggemma-300m": (0.35, 0.45, 0.04, 0.30)}
DEFAULT_THRESHOLDS = (0.52, 0.60, 0.08, None)
DENSE_ENTITIES = 3
PPR_DAMPING, PPR_STEPS = 0.5, 20
ROLE_WEIGHT = {"main": 1.0, "used": 0.6, "mentioned": 0.3}
# a relation read from its object's side, as a plain phrase: the small models misread "é o alvo de «usa» de"
INBOUND = {"uses": "é usado por", "addresses": "é abordado por", "developed_by": "desenvolveu",
           "evaluated_on": "serviu para avaliar", "builds_on": "serve de base para", "regulated_by": "regula"}
WEAK = 0.02               # below this cross-encoder probability the best source is probably off topic
CATEGORY_TYPES = q.CATEGORY_TYPES
_IN = ",".join("?" * len(APPROVED))
_TOKEN = re.compile(r"[^\W_]+")
STOP = set("""a o os as um uma uns umas de da do das dos em no na nos nas por para pra com sem sob sobre entre ate e ou
mas que qual quais quem como quando onde porque por que se ja nao sim mais menos muito muita muitos muitas pouco ha
tem tinha ter sao ser foi era esta estao estar isso isto esse essa esses essas este estes aquele aquela ao aos pela
pelo pelas pelos meu minha meus minhas seu sua seus suas me te lhe nos eles elas ele ela voce voces eu the of and or
in on for to is are was were be been with without by at as it its this that these those what which who how when
where why do does did can could about from into over than then there their has have had not no yes me my our your
existe existem alguma algum alguns algumas fala falam falou sobre diz dizem saiu sairam chegou chegaram apareceu
apareceram tenho temos grafo item itens artigo artigos estudo estudos paper papers coisa coisas tipo quero queria
gostaria saber mostre mostra liste lista explique explica resuma resume conte diga fale""".split())
TYPE_WORDS = {
    "model": ("modelo", "modelos", "model", "models", "llm", "llms"),
    "technique": ("tecnica", "tecnicas", "metodo", "metodos", "abordagem", "abordagens", "technique", "techniques"),
    "organization": ("organizacao", "organizacoes", "empresa", "empresas", "laboratorio", "laboratorios", "hospital",
                     "hospitais", "universidade", "universidades", "instituicao", "instituicoes", "startup", "startups"),
    "dataset": ("dataset", "datasets", "benchmark", "benchmarks", "base", "bases"),
    "product": ("produto", "produtos", "plataforma", "plataformas", "ferramenta", "ferramentas", "sistema", "sistemas"),
    "problem": ("problema", "problemas", "desafio", "desafios", "dor", "dores"),
    "regulation": ("regulacao", "regulacoes", "norma", "normas", "lei", "leis", "regulamento", "regulamentos",
                   "padrao", "padroes"),
}
_COUNT = re.compile(r"\bquant[oa]s?\b")
_TOP = re.compile(r"\b(mais (citad|mencionad|frequent|comun|popular|falad|presente)\w*|principais|top\s*\d*|ranking|"
                  r"mais aparece\w*)\b")
_TREND = re.compile(r"\b(em alta|tendencias?|subiu|subindo|subiram|crescendo|cresceu|novidades?|de novo|bombando|"
                    r"ganhando forca|emergentes?)\b")
_GLOBAL = re.compile(r"\b(panorama|visao geral|grandes temas|principais temas|temas|resum[oa] (geral|d[ao]s?)|mapa|"
                     r"comunidades?|como esta|estado da arte)\b")
_IDEAS = re.compile(r"\bidei?as?\b")
_WINDOWS = (
    (re.compile(r"\b(ultim[oa]s?|nos ultimos|nas ultimas)\s+(\d{1,3})\s+dias?\b"), lambda m: int(m.group(2))),
    (re.compile(r"\b(ultim[oa]s?|nas ultimas|nos ultimos)\s+(\d{1,2})\s+semanas?\b"), lambda m: 7 * int(m.group(2))),
    (re.compile(r"\b(ultim[oa]s?|nos ultimos)\s+(\d{1,2})\s+mes(es)?\b"), lambda m: 30 * int(m.group(2))),
    (re.compile(r"\bhoje\b"), lambda m: 1),
    (re.compile(r"\bontem\b"), lambda m: 2),
    (re.compile(r"\b(esta|nesta|essa|nessa|ultima|na ultima|da) semana\b|\bsemana passada\b"), lambda m: 7),
    (re.compile(r"\b(este|neste|esse|nesse|ultimo|no ultimo|do) mes\b|\bmes passado\b"), lambda m: 31),
    (re.compile(r"\b(este|neste|esse|nesse) ano\b"), lambda m: 365),
)


def window_days(question) -> int | None:
    """The time window a question asks for, in days: "o que saiu esta semana" -> 7."""
    text = fold(question or "")
    for pattern, days in _WINDOWS:
        match = pattern.search(text)
        if match:
            return max(1, days(match))
    return None


def content_tokens(question) -> list:
    """The question's words that carry meaning, without case or accents, in order and without repeats."""
    seen, out = set(), []
    for token in _TOKEN.findall(fold(question or "")):
        if token not in STOP and token not in seen and (len(token) > 1 or token.isdigit()):
            seen.add(token)
            out.append(token)
    return out


@dataclass
class Linked:
    entity_id: int
    name: str
    type: str
    how: str            # "nome" (written in the question) | "sentido" (close in meaning) | "fontes" (shared by
                        # the best sources: how a word in Portuguese reaches an entity named in English)
    weight: float


@dataclass
class Source:
    n: int
    item_id: str
    title: str
    url: str
    source: str
    day: str
    section: str
    summary: str
    why: str
    excerpt: str = ""               # the chunk of the item's own text closest to the question
    score: float = 0.0
    relevance: float | None = None  # cross-encoder probability, when a reranker ran
    channels: dict = field(default_factory=dict)   # ranking -> position (1 = first)


@dataclass
class Pack:
    question: str
    days: int | None = None
    entities: list = field(default_factory=list)
    facts: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    timings: dict = field(default_factory=dict)
    far: bool = False       # the closest passage is below the embedder's off-topic threshold

    @property
    def weak(self) -> bool:
        """The graph probably has nothing on the question: no source, or neither a named entity nor a close text."""
        if not self.sources:
            return True
        if any(e.how == "nome" for e in self.entities):
            return False
        best = max((s.relevance for s in self.sources if s.relevance is not None), default=None)
        return bool(self.far) or (best is not None and best < WEAK)

    def context(self, budget=9000) -> str:
        """The text the model reads: the facts of the graph, then the numbered sources, inside `budget` characters
        (the first three sources always enter; the excerpts are the first thing to be left out)."""
        parts = []
        if self.facts:
            parts.append("## Fatos do grafo\n" + "\n".join(self.facts))
        used = sum(len(p) for p in parts)
        blocks = []
        for s in self.sources:
            head = f"[{s.n}] {s.title} ({s.source}, {_br_day(s.day)}, {s.section})"
            body = "\n".join(x for x in (s.summary, f"Por que importa: {s.why}" if s.why else "") if x)
            block = f"{head}\n{body}"
            if s.excerpt and used + len(block) + len(s.excerpt) < budget:
                block += f'\nTrecho do original: "{s.excerpt}"'
            if blocks and len(blocks) >= 3 and used + len(block) > budget:
                break
            blocks.append(block)
            used += len(block)
        if blocks:
            parts.append("## Fontes\n" + "\n\n".join(blocks))
        return "\n\n".join(parts)

    def as_dict(self) -> dict:
        return {"question": self.question, "days": self.days, "weak": self.weak,
                "entities": [vars(e) for e in self.entities], "facts": list(self.facts),
                "sources": [vars(s) for s in self.sources], "notes": list(self.notes), "timings": dict(self.timings)}


def _br_day(iso) -> str:
    day = (iso or "")[:10]
    return f"{day[8:10]}/{day[5:7]}/{day[:4]}" if len(day) == 10 else "?"


class Reranker:
    """A multilingual cross-encoder through fastembed (ONNX on the CPU), loaded at the first question."""

    def __init__(self, model, cache_dir=None):
        self.name, self.cache_dir, self._model = model, cache_dir, None

    def score(self, question, texts) -> list:
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder   # heavy import; only when used
            self._model = TextCrossEncoder(self.name, cache_dir=str(self.cache_dir) if self.cache_dir else None)
        return [1.0 / (1.0 + math.exp(-float(x))) for x in self._model.rerank(question, list(texts), batch_size=8)]


def get_reranker(settings):
    name = (getattr(settings, "rag_reranker", "") or "").strip()
    return Reranker(name, cache_dir=settings.models_dir / "fastembed") if name else None


class Corpus:
    """What the retrieval reads from the store, loaded once: the vectors, the names and the entity graph."""

    def __init__(self, store):
        from scipy import sparse

        self.stamp = stamp(store)
        rows = store.conn.execute("SELECT id, kind, ref, item_id, day, dim, vector FROM rag_passages"
                                  " WHERE vector IS NOT NULL ORDER BY id").fetchall()
        self.models = {r[0] for r in store.conn.execute("SELECT DISTINCT model FROM rag_passages WHERE model IS NOT NULL")}
        self.ids = np.array([r["id"] for r in rows], dtype=np.int64)
        self.kinds = np.array([r["kind"] for r in rows], dtype=object)
        self.refs = [r["ref"] for r in rows]
        self.items = [r["item_id"] for r in rows]
        self.days = np.array([r["day"] or "" for r in rows], dtype=object)
        dims = {r["dim"] for r in rows}
        self.matrix = (np.stack([np.frombuffer(r["vector"], dtype=np.float32, count=r["dim"]) for r in rows])
                       if rows and len(dims) == 1 else np.zeros((0, 0), dtype=np.float32))
        self.entities = {r["id"]: r for r in store.conn.execute("SELECT * FROM entities")}
        self.aliases = {}
        for norm, entity_id in store.conn.execute("SELECT alias_norm, entity_id FROM entity_aliases"):
            self.aliases.setdefault(norm, set()).add(entity_id)
        for entity_id, row in self.entities.items():
            self.aliases.setdefault(row["norm"], set()).add(entity_id)
            if row["type"] in CATEGORY_TYPES:                      # "radiologia/imagem" answers to "radiologia" too
                for part in row["name"].split("/"):
                    key = normalize(part)
                    if len(key) >= 6:
                        self.aliases.setdefault(key, set()).add(entity_id)
        # the entity graph: co-occurrence in approved items, typed relations counting double
        nodes = [i for i, r in self.entities.items() if r["type"] in q.ENTITY_TYPES and r["mention_count"] > 0]
        self.node = {entity_id: n for n, entity_id in enumerate(nodes)}
        self.nodes = nodes
        weights = {}
        for a, b, n in store.conn.execute(
                "SELECT a.entity_id, b.entity_id, COUNT(*) FROM entity_mentions a JOIN entity_mentions b"
                " ON b.item_id = a.item_id AND a.entity_id < b.entity_id JOIN triage t ON t.item_id = a.item_id"
                f" WHERE t.decision IN ({_IN}) AND a.role != 'tag' AND b.role != 'tag' GROUP BY a.entity_id, b.entity_id",
                list(APPROVED)):
            if a in self.node and b in self.node:
                weights[(self.node[a], self.node[b])] = float(n)
        for s, o, n in store.conn.execute("SELECT subject_id, object_id, COUNT(DISTINCT item_id) FROM entity_relations"
                                          " WHERE predicate != 'in_category' GROUP BY subject_id, object_id"):
            if s in self.node and o in self.node and s != o:
                key = (min(self.node[s], self.node[o]), max(self.node[s], self.node[o]))
                weights[key] = weights.get(key, 0.0) + 2.0 * n
        size = len(nodes)
        if weights:
            i, j = np.array([k[0] for k in weights]), np.array([k[1] for k in weights])
            w = np.array(list(weights.values()), dtype=np.float64)
            adjacency = sparse.coo_matrix((np.concatenate([w, w]), (np.concatenate([i, j]), np.concatenate([j, i]))),
                                          shape=(size, size)).tocsr()
            degree = np.asarray(adjacency.sum(axis=0)).ravel()
            degree[degree == 0] = 1.0
            self.walk = adjacency.multiply(1.0 / degree).tocsr()        # column-stochastic
        else:
            self.walk = sparse.csr_matrix((size, size))
        # items × entities, weighted by the role of the mention
        self.item_ids, index, r_, c_, v_ = [], {}, [], [], []
        for item_id, entity_id, role in store.conn.execute(
                "SELECT m.item_id, m.entity_id, m.role FROM entity_mentions m JOIN triage t ON t.item_id = m.item_id"
                f" WHERE t.decision IN ({_IN}) AND m.role != 'tag'", list(APPROVED)):
            if entity_id not in self.node:
                continue
            row = index.setdefault(item_id, len(index))
            if row == len(self.item_ids):
                self.item_ids.append(item_id)
            r_.append(row), c_.append(self.node[entity_id]), v_.append(ROLE_WEIGHT.get(role, 0.3))
        self.mentions = sparse.csr_matrix((v_, (r_, c_)), shape=(len(self.item_ids), size)) if r_ else None
        self.day_of = dict(store.conn.execute(
            f"SELECT i.id, i.fetched_at FROM items i JOIN triage t ON t.item_id = i.id WHERE t.decision IN ({_IN})",
            list(APPROVED)).fetchall())

    def rows(self, kinds) -> np.ndarray:
        return np.flatnonzero(np.isin(self.kinds, list(kinds))) if len(self.kinds) else np.zeros(0, dtype=np.int64)


def stamp(store) -> tuple:
    return (store.meta_get("rag_indexed_at"), store.conn.execute("SELECT COUNT(*) FROM rag_passages").fetchone()[0],
            store.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0])


class Retriever:
    def __init__(self, store, embedder, reranker=None, now=None):
        self.store, self.embedder, self.reranker = store, embedder, reranker
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._corpus = None

    @property
    def corpus(self) -> Corpus:
        if self._corpus is None or self._corpus.stamp != stamp(self.store):
            self._corpus = Corpus(self.store)
        return self._corpus

    @property
    def thresholds(self) -> tuple:
        return THRESHOLDS.get(getattr(self.embedder, "name", ""), DEFAULT_THRESHOLDS)

    # --- the question --------------------------------------------------------
    def _embed(self, question):
        corpus = self.corpus
        if self.embedder is None or not corpus.matrix.size or self.embedder.name not in corpus.models:
            return None
        try:
            vector = np.asarray(self.embedder.embed([query_text(self.embedder.name, question)], raw=True)[0],
                                dtype=np.float32)
        except Exception:  # noqa: BLE001 - e.g. the model cannot be loaded here: the lexical and graph rankings remain
            return None
        return vector if vector.shape[0] == corpus.matrix.shape[1] else None

    def link(self, question, vector=None) -> list:
        """Entities the question names (exact, the longest name first) or means (dense)."""
        corpus = self.corpus
        words = normalize(question).split()
        linked, taken = {}, set()
        for n in range(min(5, len(words)), 0, -1):
            for start in range(len(words) - n + 1):
                span = set(range(start, start + n))
                if span & taken:
                    continue
                text = " ".join(words[start:start + n])
                if n == 1 and (text in STOP or text in GENERIC or len(text) < 3 or text.isdigit()):
                    continue
                found = corpus.aliases.get(text) or corpus.aliases.get(normalize(text, "technique"))
                if not found:
                    continue
                taken |= span
                best = sorted(found, key=lambda e: -corpus.entities[e]["mention_count"])[:3]
                for entity_id in best:
                    if corpus.entities[entity_id]["mention_count"] > 0:
                        linked[entity_id] = ("nome", 1.0)
        if vector is not None:
            rows = corpus.rows(("entity",))
            first, following, gap, _ = self.thresholds
            if len(rows):
                sims = corpus.matrix[rows] @ vector
                order = np.argsort(-sims)[:DENSE_ENTITIES]
                top = float(sims[order[0]])
                for rank, position in enumerate(order):
                    sim = float(sims[position])
                    entity_id = int(corpus.refs[rows[position]])
                    close = sim >= first if rank == 0 else (sim >= following and sim >= top - gap)
                    if close and entity_id not in linked and entity_id in corpus.entities:
                        linked[entity_id] = ("sentido", round(min(0.8, 0.3 + (sim - first)), 3))
        out = [Linked(e, corpus.entities[e]["name"], corpus.entities[e]["type"], how, weight)
               for e, (how, weight) in linked.items()]
        out.sort(key=lambda x: (x.how != "nome", -x.weight, -corpus.entities[x.entity_id]["mention_count"]))
        return out[:8]

    # --- the rankings --------------------------------------------------------
    def _dense(self, vector, allowed):
        """-> (items in order, {item: (similarity, passage row)}, {item: row of its best text chunk})."""
        corpus = self.corpus
        rows = corpus.rows(("card", "text"))
        if vector is None or not len(rows):
            return [], {}, {}
        sims = corpus.matrix[rows] @ vector
        best, chunk = {}, {}
        for position in np.argsort(-sims):
            row = rows[position]
            item = corpus.items[row]
            if allowed is not None and item not in allowed:
                continue
            if corpus.kinds[row] == "text" and item not in chunk:
                chunk[item] = (float(sims[position]), int(row))
            if item not in best:
                if len(best) >= POOL:
                    if len(chunk) >= POOL:
                        break
                    continue
                best[item] = (float(sims[position]), int(row))
        return list(best), best, chunk

    def _bm25(self, question, linked, allowed):
        if not self.store.fts:
            return []
        terms = [f'"{t}"' for t in content_tokens(question)]
        for entity in linked:
            name = " ".join(_TOKEN.findall(fold(entity.name)))
            if name and entity.how == "nome":
                terms.append(f'"{name}"')
        if not terms:
            return []
        rows = self.store.conn.execute(         # bm25() cannot sit inside an aggregate: the best passage of each
            "SELECT p.item_id, bm25(rag_fts, 4.0, 1.0) AS s FROM rag_fts JOIN rag_passages p ON p.id = rag_fts.rowid"
            " WHERE rag_fts MATCH ? AND p.kind IN ('card', 'text') ORDER BY s LIMIT ?",     # item is its first row
            (" OR ".join(dict.fromkeys(terms)), POOL * 8)).fetchall()
        items = dict.fromkeys(r[0] for r in rows if allowed is None or r[0] in allowed)
        return list(items)[:POOL]

    def _graph(self, linked, allowed):
        corpus = self.corpus
        seeds = {corpus.node[e.entity_id]: e.weight / math.log(2.0 + corpus.entities[e.entity_id]["mention_count"])
                 for e in linked if e.entity_id in corpus.node}
        if not seeds or corpus.mentions is None:
            return []
        start = np.zeros(len(corpus.nodes))
        for node, weight in seeds.items():
            start[node] = weight
        start /= start.sum()
        rank = start.copy()
        for _ in range(PPR_STEPS):
            rank = (1 - PPR_DAMPING) * start + PPR_DAMPING * (corpus.walk @ rank)
        scores = corpus.mentions @ rank
        counts = np.diff(corpus.mentions.indptr)
        scores = scores / np.sqrt(np.maximum(counts, 1))
        out = []
        for row in np.argsort(-scores):
            if scores[row] <= 0 or len(out) >= POOL:
                break
            item = corpus.item_ids[row]
            if allowed is None or item in allowed:
                out.append(item)
        return out

    def _mentioning(self, entity_ids, allowed, tags=False):
        if not entity_ids:
            return []
        marks = ",".join("?" * len(entity_ids))
        order = ("t.total DESC, i.fetched_at DESC" if tags else
                 "CASE m.role WHEN 'main' THEN 0 WHEN 'used' THEN 1 ELSE 2 END, i.fetched_at DESC")
        rows = self.store.conn.execute(
            "SELECT i.id FROM entity_mentions m JOIN items i ON i.id = m.item_id JOIN triage t ON t.item_id = i.id"
            f" WHERE m.entity_id IN ({marks}) AND t.decision IN ({_IN}) GROUP BY i.id ORDER BY {order} LIMIT ?",
            list(entity_ids) + list(APPROVED) + [POOL * 3]).fetchall()
        return [r[0] for r in rows if allowed is None or r[0] in allowed][:POOL]

    def _relating(self, entity_ids, allowed):
        """Items that state a typed relation of one of these entities, the ones that state the most first."""
        if not entity_ids:
            return []
        marks = ",".join("?" * len(entity_ids))
        rows = self.store.conn.execute(
            "SELECT r.item_id FROM entity_relations r JOIN items i ON i.id = r.item_id JOIN triage t ON t.item_id = i.id"
            f" WHERE (r.subject_id IN ({marks}) OR r.object_id IN ({marks})) AND r.predicate != 'in_category'"
            f" AND t.decision IN ({_IN}) GROUP BY r.item_id ORDER BY COUNT(*) DESC, i.fetched_at DESC LIMIT ?",
            list(entity_ids) * 2 + list(APPROVED) + [POOL * 3]).fetchall()
        return [r[0] for r in rows if allowed is None or r[0] in allowed][:POOL]

    def _shared(self, items, known, limit=2) -> list:
        """Entities that at least two of the best sources mention and the question did not link: "sepse" never
        equals "sepsis early detection", but the items found for it are about that entity. Hubs that a large
        part of the graph mentions ("large language model") say nothing about the question and stay out."""
        if len(items) < 2:
            return []
        corpus = self.corpus
        ceiling = max(8, len(corpus.day_of) // 25)
        rows = self.store.conn.execute(
            f"SELECT entity_id, COUNT(DISTINCT item_id) FROM entity_mentions WHERE item_id IN ({','.join('?' * len(items))})"
            " AND role != 'tag' GROUP BY entity_id HAVING COUNT(DISTINCT item_id) >= 2", list(items)).fetchall()
        found = [(n, corpus.entities[e]) for e, n in rows if e in corpus.entities and e not in known
                 and corpus.entities[e]["type"] in q.ENTITY_TYPES and corpus.entities[e]["mention_count"] <= ceiling]
        found.sort(key=lambda pair: (-pair[0], pair[1]["mention_count"], pair[1]["name"]))
        return [Linked(row["id"], row["name"], row["type"], "fontes", 0.4) for _, row in found[:limit]]

    # --- the facts of the graph ----------------------------------------------
    def _entity_fact(self, entity_id) -> str:
        d = q.entity_detail(self.store, entity_id, items_limit=6)
        if d is None:
            return ""
        head = f"• {d['name']} ({d['type_label']}" + (f"; {d['category_label']}" if d["category_label"] else "") + ")"
        head += f": citado em {d['mention_count']} itens, de {_br_day(d['first_seen'])} a {_br_day(d['last_seen'])}."
        if d["aliases"]:
            head += f" Também escrito: {', '.join(d['aliases'][:4])}."
        grouped = {}
        for r in d["relations"][:12]:
            arrow = INBOUND.get(r["relation"], f"← {r['label']}") if r["direction"] == "in" else r["label"]
            grouped.setdefault(arrow, []).append(r["other"]["name"])
        lines = [head] + [f"  - {arrow}: {', '.join(names[:6])}" for arrow, names in grouped.items()]
        near = [f"{n['name']} ({n['shared']})" for n in d["neighbors"] if n["type"] in q.ENTITY_TYPES][:6]
        if near:
            lines.append(f"  - aparece junto com (itens em comum): {', '.join(near)}")
        for claim in d["claims"][:2]:
            lines.append(f"  - número citado: {claim['text_pt']}")
        return "\n".join(lines)

    def _facts(self, question, linked, days, since) -> list:
        store, text = self.store, fold(question)
        facts, period = [], f"nos últimos {days} dias" if days else "em todo o grafo"
        named = [e for e in linked if e.how == "nome" and e.type in q.ENTITY_TYPES][:4]
        others = [e for e in linked if e.how != "nome" and e.type in q.ENTITY_TYPES]
        for entity in named + others[:max(0, 3 - len(named))]:
            fact = self._entity_fact(entity.entity_id)
            if fact:
                facts.append(fact)
        for entity in [e for e in linked if e.type == "technique" or e.how == "nome"][:4]:
            row = store.conn.execute("SELECT term, expansion, definition_pt FROM glossary WHERE entity_id = ?",
                                     (entity.entity_id,)).fetchone()
            if row is not None:
                facts.append(f"• Glossário, {row['term']}: {row['definition_pt']}")
        for row in store.glossary_terms():                           # a term asked by name ("o que é LoRA?")
            from sotawhat.glossary import occurs, surfaces
            if any(occurs(s, question) for s in surfaces(row)) and not any(row["term"] in f for f in facts):
                facts.append(f"• Glossário, {row['term']}"
                             + (f" ({row['expansion']})" if row["expansion"] else "") + f": {row['definition_pt']}")
                if len(facts) >= 8:
                    break
        if _COUNT.search(text):
            args = list(APPROVED) + ([since] if since else [])
            total = store.conn.execute(
                f"SELECT COUNT(*) FROM triage t JOIN items i ON i.id = t.item_id WHERE t.decision IN ({_IN})"
                + (" AND i.fetched_at >= ?" if since else ""), args).fetchone()[0]
            facts.append(f"• Contagem: {total} itens aprovados {period}.")
            for entity in linked[:4]:
                n = store.conn.execute(
                    "SELECT COUNT(DISTINCT m.item_id) FROM entity_mentions m JOIN items i ON i.id = m.item_id"
                    f" JOIN triage t ON t.item_id = i.id WHERE m.entity_id = ? AND t.decision IN ({_IN})"
                    + (" AND i.fetched_at >= ?" if since else ""), [entity.entity_id] + args).fetchone()[0]
                facts.append(f"• Contagem: {n} itens aprovados citam {entity.name} {period}.")
        if _TOP.search(text) or _COUNT.search(text):
            words = set(_TOKEN.findall(text))
            for type_, keys in TYPE_WORDS.items():
                if words & set(keys):
                    rows = [r for r in q._window_counts(store, [type_], since)][:10]
                    if rows:
                        facts.append(f"• Mais citados ({q.TYPE_LABELS[type_]}, {period}): "
                                     + "; ".join(f"{r['name']} ({r['n']})" for r in rows))
        if _TREND.search(text):
            rising = intel.trends(store, now=self._now(), limit=10)
            if rising:
                facts.append("• Em alta (7 dias contra os 28 anteriores): " + "; ".join(
                    f"{t['name']} ({t['recent']} itens" + (", novo" if t["new"] else "") + ")" for t in rising))
        return facts

    def _communities(self, vector, limit=3) -> list:
        corpus = self.corpus
        rows = corpus.rows(("community",))
        if vector is None or not len(rows):
            return []
        sims = corpus.matrix[rows] @ vector
        picked = [int(corpus.ids[rows[p]]) for p in np.argsort(-sims)[:limit]]
        found = {r["id"]: r for r in self.store.conn.execute(
            f"SELECT id, title, body FROM rag_passages WHERE id IN ({','.join('?' * len(picked))})", picked)}
        return [f"• Tema do grafo, {found[i]['title']}: {found[i]['body'].splitlines()[0]}" for i in picked if i in found]

    def _ideas(self, vector, limit=3) -> list:
        corpus = self.corpus
        rows = corpus.rows(("idea",))
        if vector is None or not len(rows):
            return []
        sims = corpus.matrix[rows] @ vector
        picked = [int(corpus.ids[rows[p]]) for p in np.argsort(-sims)[:limit]]
        found = {r["id"]: r for r in self.store.conn.execute(
            f"SELECT id, title, body FROM rag_passages WHERE id IN ({','.join('?' * len(picked))})", picked)}
        return [f"• Ideia do seu ledger, {found[i]['title']}: " + " ".join(found[i]["body"].split())[:420]
                for i in picked if i in found]

    # --- the whole thing -----------------------------------------------------
    def retrieve(self, question, days=None, k=8, channels=None) -> Pack:
        """`channels`: only these rankings (the evaluation asks each one alone); None = all of them."""
        t0 = time.perf_counter()
        question = " ".join((question or "").split())
        pack = Pack(question=question)
        if not question:
            return pack
        corpus = self.corpus
        days = days if days else window_days(question)
        pack.days = days
        since = (self._now() - timedelta(days=days)).isoformat(timespec="seconds") if days else None
        allowed = {i for i, day in corpus.day_of.items() if day >= since} if since else None
        if since:
            pack.notes.append(f"janela: últimos {days} dias ({len(allowed)} itens aprovados)")
        vector = self._embed(question)
        if vector is None:
            pack.notes.append("sem vetores para este embedder: só as buscas por palavras e pelo grafo "
                              "(rode `sotawhat rag index`)")
        linked = self.link(question, vector)
        pack.entities = linked
        pack.timings["entender"] = round(time.perf_counter() - t0, 3)

        t1 = time.perf_counter()
        dense, dense_best, chunk = self._dense(vector, allowed)
        off_topic = self.thresholds[3]
        pack.far = bool(dense_best) and off_topic is not None and max(s for s, _ in dense_best.values()) < off_topic
        named = [e.entity_id for e in linked if e.how == "nome" and e.type in q.ENTITY_TYPES]
        categories = [e.entity_id for e in linked if e.type in CATEGORY_TYPES]
        rankings = {"dense": dense, "bm25": self._bm25(question, linked, allowed),
                    "graph": self._graph(linked, allowed), "mention": self._mentioning(named, allowed),
                    "relation": self._relating(named, allowed),
                    "category": self._mentioning(categories, allowed, tags=True)}
        if channels is not None:
            rankings = {name: items for name, items in rankings.items() if name in channels}
        fused, positions = {}, {}
        for name, items in rankings.items():
            for rank, item in enumerate(items, 1):
                fused[item] = fused.get(item, 0.0) + WEIGHTS[name] / (RRF_K + rank)
                positions.setdefault(item, {})[name] = rank
        order = sorted(fused, key=lambda i: (-fused[i], i))
        pack.timings["buscar"] = round(time.perf_counter() - t1, 3)

        t2 = time.perf_counter()
        candidates = order[:max(k, RERANK_TOP if self.reranker is not None else k)]
        rows = {r["id"]: r for r in self.store.conn.execute(
            "SELECT i.id, i.title, i.canonical_url, i.source, i.fetched_at, t.decision, t.summary_pt, t.why_it_matters_pt"
            f" FROM items i JOIN triage t ON t.item_id = i.id WHERE i.id IN ({','.join('?' * len(candidates))})",
            candidates)} if candidates else {}
        candidates = [i for i in candidates if i in rows]
        relevance = {}
        if self.reranker is not None and candidates:
            try:
                texts = [f"{rows[i]['title']}\n{rows[i]['summary_pt'] or ''} {rows[i]['why_it_matters_pt'] or ''}"[:900]
                         for i in candidates]
                relevance = dict(zip(candidates, self.reranker.score(question, texts)))
            except Exception as exc:  # noqa: BLE001 - e.g. the model is not downloaded here: the fusion order stands
                pack.notes.append(f"reranker indisponível ({type(exc).__name__}): ordem só da fusão")
        if relevance:
            top_r, top_f = max(relevance.values()) or 1.0, max(fused[i] for i in candidates) or 1.0
            final = {i: RERANK_WEIGHT * relevance[i] / top_r + (1 - RERANK_WEIGHT) * fused[i] / top_f for i in candidates}
        else:
            final = {i: fused[i] for i in candidates}
        picked = sorted(candidates, key=lambda i: (-final[i], i))[:k]
        pack.timings["reordenar"] = round(time.perf_counter() - t2, 3)

        excerpts = {}
        wanted = [chunk[i][1] for i in picked if i in chunk]
        if wanted:
            ids = [int(corpus.ids[row]) for row in wanted]
            bodies = dict(self.store.conn.execute(
                f"SELECT item_id, body FROM rag_passages WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall())
            excerpts = {i: " ".join(bodies[i].split())[:700] for i in picked if i in bodies}
        for n, item in enumerate(picked, 1):
            r = rows[item]
            pack.sources.append(Source(
                n=n, item_id=item, title=r["title"], url=r["canonical_url"] or "", source=r["source"],
                day=r["fetched_at"], section=q.SECTIONS.get(r["decision"], r["decision"]),
                summary=r["summary_pt"] or "", why=r["why_it_matters_pt"] or "", excerpt=excerpts.get(item, ""),
                score=round(final[item], 4), relevance=round(relevance[item], 4) if item in relevance else None,
                channels=positions.get(item, {})))

        linked += self._shared(picked[:5], {e.entity_id for e in linked})
        pack.facts = self._facts(question, linked, days, since)
        text = fold(question)
        if _GLOBAL.search(text) or _TREND.search(text):
            pack.facts += self._communities(vector)
        if _IDEAS.search(text):
            pack.facts += self._ideas(vector)
        if not linked:
            pack.notes.append("nenhuma entidade do grafo reconhecida na pergunta: resposta só pelos textos")
        if pack.weak:
            pack.notes.append("as fontes encontradas parecem pouco ligadas à pergunta")
        pack.timings["total"] = round(time.perf_counter() - t0, 3)
        return pack
