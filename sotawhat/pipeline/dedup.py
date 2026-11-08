# sotawhat/pipeline/dedup.py
"""Same-story dedup by near-identical titles (SDD §6.7, stage A).

Measured on 2026-11-07: for 5 local embedding models, cosine similarity does not separate "the same
story worded differently" from "same topic, different work" (gap from -0.05 to -0.12). So clusters are
formed only on near-identical titles, which covers the same paper arriving from PubMed, Crossref,
arXiv and HF. Embeddings feed the novelty score D instead. Cross-outlet news clustering (P2, newsletters)
will add an LLM judge for embedding-similar pairs.
"""
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

_STOP = {"the", "and", "for", "with", "from", "into", "via", "using", "based", "toward", "towards", "its",
         "are", "our", "new", "how", "what", "why", "uma", "para", "com", "por", "dos", "das", "nos", "nas",
         "que", "sobre", "entre"}


def norm_title(title) -> str:
    text = unicodedata.normalize("NFKD", (title or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def title_tokens(title) -> frozenset:
    return frozenset(w for w in norm_title(title).split() if len(w) > 2 and w not in _STOP)


def _numbers(norm) -> frozenset:
    return frozenset(w for w in norm.split() if any(ch.isdigit() for ch in w))


class _Seen:
    __slots__ = ("id", "rep", "norm", "tokens", "nums")

    def __init__(self, item_id, title, rep):
        self.id, self.rep = item_id, rep
        self.norm, self.tokens = norm_title(title), title_tokens(title)
        self.nums = _numbers(self.norm)


def _informative(norm, tokens) -> bool:
    return len(tokens) >= 4 or len(norm) >= 25   # "Editorial" twice is not the same story


def _same(norm, tokens, seen, ratio, jaccard) -> bool:
    if not _informative(norm, tokens) or not seen.norm:
        return False
    if norm == seen.norm:
        return True
    if _numbers(norm) != seen.nums:
        return False   # "Qwen3.8 technical report" vs "Qwen3.9 technical report", "Part 1" vs "Part 2"
    if len(tokens) >= 4 and len(seen.tokens) >= 4:
        overlap = len(tokens & seen.tokens) / len(tokens | seen.tokens)
        if overlap >= jaccard:
            return True
        if overlap < 0.5:
            return False
    return SequenceMatcher(None, norm, seen.norm).ratio() >= ratio


def same_title(a, b, ratio=0.92, jaccard=0.8) -> bool:
    return _same(norm_title(a), title_tokens(a), _Seen("b", b, "b"), ratio, jaccard)


class _Index:
    """Exact normalized titles + an inverted token index, so each title is compared only with
    titles that share at least half of its words."""

    def __init__(self):
        self.entries, self.exact, self.postings = [], {}, {}

    def add(self, entry):
        self.exact.setdefault(entry.norm, entry)
        position = len(self.entries)
        self.entries.append(entry)
        for token in entry.tokens:
            self.postings.setdefault(token, []).append(position)

    def candidates(self, tokens):
        counts = Counter()
        for token in tokens:
            counts.update(self.postings.get(token, ()))
        need = max(1, len(tokens) // 2)
        return [self.entries[i] for i, c in counts.items() if c >= need]


def find_duplicates(items, known, ratio=0.92, jaccard=0.8) -> dict:
    """items: new Items, in priority order. known: rows (id, title, cluster_id) already stored.
    Returns {item_id: representative_id} for every item that repeats a known item or an earlier one."""
    index = _Index()
    for row in known:
        index.add(_Seen(row[0], row[1], row[2] or row[0]))
    out = {}
    for it in items:
        norm, tokens = norm_title(it.title), title_tokens(it.title)
        informative = _informative(norm, tokens)
        match = index.exact.get(norm) if informative else None
        if match is None and informative:
            match = next((s for s in index.candidates(tokens) if _same(norm, tokens, s, ratio, jaccard)), None)
        if match is not None:
            out[it.id] = match.rep
            continue
        index.add(_Seen(it.id, it.title, it.id))
    return out
