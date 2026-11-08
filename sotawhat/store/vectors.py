# sotawhat/store/vectors.py
"""Local embeddings (SDD §6.3, D3): fastembed (ONNX on CPU, no per-call cost) and vector helpers.

Default model: google/embeddinggemma-300m (768-d, multilingual, 1.2 GB, downloaded once to
data/models/fastembed). On the reference machine (Ryzen 5 5500) it embeds ~2.4 items/s, about 1 min
for a day's items. BGE-M3, assumed in SDD v1.1, is not offered by fastembed 0.9.
"""
import hashlib
import re

import numpy as np

DEFAULT_MODEL = "google/embeddinggemma-300m"
# EmbeddingGemma expects a task prefix; "clustering" fits both novelty and the relevance classifier.
_PREFIXES = {"google/embeddinggemma-300m": "task: clustering | query: "}


def item_text(title, text, limit=2000) -> str:
    return f"{title}\n{(text or '')[:limit]}".strip()


def normalize(matrix) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.ndim == 1:
        matrix = matrix[None, :]
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class FastEmbedder:
    def __init__(self, model=DEFAULT_MODEL, cache_dir=None, batch_size=16):
        self.name = model
        self.cache_dir = cache_dir
        self.batch_size = batch_size
        self._model = None

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding   # heavy import (onnxruntime); only when used
            self._model = TextEmbedding(self.name, cache_dir=str(self.cache_dir) if self.cache_dir else None)
        return self._model

    def embed(self, texts) -> np.ndarray:
        texts = list(texts)
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        prefix = _PREFIXES.get(self.name, "")
        vectors = self._load().embed([prefix + t for t in texts], batch_size=self.batch_size)
        return normalize(np.array(list(vectors), dtype=np.float32))


class HashEmbedder:
    """Deterministic bag-of-words hashing. Used by the tests and as an explicit offline backend
    (EMBEDDINGS_BACKEND=hash); far weaker than a real model."""

    def __init__(self, dim=256):
        self.dim = dim
        self.name = f"hash-{dim}"

    def embed(self, texts) -> np.ndarray:
        texts = list(texts)
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in re.findall(r"\w+", text.lower()):
                out[row, int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16) % self.dim] += 1.0
        return normalize(out) if texts else out


def get_embedder(settings):
    backend = (settings.embeddings_backend or "fastembed").lower()
    if backend == "hash":
        return HashEmbedder()
    if backend == "fastembed":
        return FastEmbedder(settings.embeddings_model, cache_dir=settings.models_dir / "fastembed")
    raise ValueError(f"EMBEDDINGS_BACKEND desconhecido: {settings.embeddings_backend}")


def novelty_scores(vectors, reference, thresholds) -> list:
    """D (0–5) per row of `vectors`: 5 minus how many thresholds the best cosine match reaches."""
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.size == 0:
        return []
    reference = np.asarray(reference, dtype=np.float32)
    if reference.size == 0:
        return [5] * len(vectors)
    best = (vectors @ reference.T).max(axis=1)
    return [5 - sum(1 for t in thresholds if score >= t) for score in best.tolist()]
