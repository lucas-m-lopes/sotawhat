# tests/test_dedup_vectors.py
import numpy as np

from sotawhat.config import Settings
from sotawhat.items import Item
from sotawhat.pipeline.dedup import find_duplicates, norm_title, same_title
from sotawhat.store.vectors import FastEmbedder, HashEmbedder, get_embedder, item_text, novelty_scores


def _it(iid, title):
    return Item(id=iid, kind="paper", source="pubmed", source_id="", title=title, url="")


def test_titles_from_two_sources_are_the_same_story():
    # real pair from the vault: JMIR RSS vs PubMed (en dash vs hyphen, trailing period)
    a = "Knowledge-Augmented Large Language Model for Multimodal Electronic Health Record–Based Risk Prediction"
    b = "Knowledge-Augmented Large Language Model for Multimodal Electronic Health Record-Based Risk Prediction."
    assert norm_title(a) == norm_title(b)
    assert same_title("AI Scribe Safety: Measuring What Happens After Signing",
                      "AI scribe safety - measuring what happens after signing.")
    assert same_title("Deep learning detects pneumothorax on chest radiographs in a multicenter cohort",
                      "Deep learning detects pneumothorax on chest radiographs: a multicenter cohort study")


def test_same_topic_different_work_is_not_merged():
    assert not same_title("Deep learning detects pneumothorax on chest radiographs",
                          "Deep learning detects pulmonary nodules on low-dose chest CT")
    assert not same_title("Editorial", "Editorial")       # uninformative titles never cluster
    assert not same_title("Qwen3.8 technical report: scaling open multimodal models",
                          "Qwen3.9 technical report: scaling open multimodal models")   # numbers must match


def test_find_duplicates_against_known_and_within_batch():
    known = [("pmid:1", "Real-World Implementation of Large Language Models for Writing Discharge Summaries", None)]
    items = [_it("url:a", "Real-world implementation of large language models for writing discharge summaries."),
             _it("doi:b", "A foundation model for retinal imaging"),
             _it("arxiv:c", "A Foundation Model for Retinal Imaging"),
             _it("pmid:d", "Editorial"), _it("pmid:e", "Editorial")]
    assert find_duplicates(items, known) == {"url:a": "pmid:1", "arxiv:c": "doi:b"}
    assert find_duplicates(items[:1], [("pmid:1", known[0][1], "cluster-x")]) == {"url:a": "cluster-x"}


def test_hash_embedder_is_deterministic_and_unit_norm():
    emb = HashEmbedder(dim=64)
    a, b, c = emb.embed(["sepsis early warning model", "sepsis early warning model", "datacenter chip"])
    assert np.allclose(a, b) and abs(float(np.linalg.norm(a)) - 1) < 1e-6
    assert float(a @ c) < float(a @ b)
    assert emb.embed([]).shape == (0, 64)


def test_novelty_scores_map_similarity_to_d():
    thresholds = (0.70, 0.76, 0.82, 0.88, 0.94)
    ref = np.array([[1.0, 0.0]], dtype=np.float32)
    vecs = np.array([[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]], dtype=np.float32)   # cos 1.0, 0.8, 0.0
    assert novelty_scores(vecs, ref, thresholds) == [0, 3, 5]
    assert novelty_scores(vecs, np.zeros((0, 0)), thresholds) == [5, 5, 5]
    assert novelty_scores(np.zeros((0, 2)), ref, thresholds) == []


def test_item_text_and_backend_factory(tmp_path):
    assert item_text("T", "x" * 5000).count("x") == 2000
    fast = get_embedder(Settings(_env_file=None, sotawhat_data_dir=tmp_path))
    assert isinstance(fast, FastEmbedder) and fast.name == "google/embeddinggemma-300m"
    assert str(fast.cache_dir).endswith("fastembed") and fast._model is None    # nothing downloaded yet
    assert isinstance(get_embedder(Settings(_env_file=None, embeddings_backend="hash")), HashEmbedder)
