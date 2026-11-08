# tests/test_classifier.py
from datetime import datetime, timezone

from sotawhat.items import Item
from sotawhat.store.classifier import load_gate, refresh, train
from sotawhat.store.db import Store
from sotawhat.store.vectors import HashEmbedder

EMB = HashEmbedder(dim=64)
NOW = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)


def _seed(st, n_pos, n_neg, profile="medico", start=0):
    run = st.start_run("daily")
    items, votes = [], []
    for i in range(start, start + n_pos):
        items.append(Item(id=f"p{i}", kind="paper", source="pubmed", source_id="", url="", profile=profile,
                          title=f"deep learning radiology model {i}", text="hospital imaging ai validation"))
        votes.append((f"p{i}", "up" if i % 3 else "test"))
    for i in range(start, start + n_neg):
        items.append(Item(id=f"n{i}", kind="paper", source="pubmed", source_id="", url="", profile=profile,
                          title=f"asthma antibody phase trial {i}", text="randomized dosing placebo cohort"))
        votes.append((f"n{i}", "down"))
    st.upsert_items(items, run)
    st.save_embeddings(EMB.name, zip([it.id for it in items],
                                     EMB.embed([f"{it.title}\n{it.text}" for it in items])))
    for item_id, value in votes:
        st.add_feedback("item", item_id, value, "telegram")


def test_no_model_below_min_ratings_or_with_one_class(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        _seed(st, 30, 0)
        assert train(st, "medico", EMB.name, tmp_path / "models", min_ratings=20) is None   # one class only
        _seed(st, 0, 5)
        assert train(st, "medico", EMB.name, tmp_path / "models", min_ratings=100) is None  # 35 < 100


def test_trained_gate_ranks_positives_first(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        _seed(st, 60, 50)
        info = train(st, "medico", EMB.name, tmp_path / "models", min_ratings=100, now=NOW)
        assert info["version"] == "medico-20261108T100000"
        assert info["metrics"]["n"] == 110 and info["metrics"]["f1"] >= 0.9
        gate = load_gate(st, "medico", EMB.name)
        good, bad = gate.score(EMB.embed(["deep learning radiology model for hospital imaging",
                                          "asthma antibody dosing trial"]))
        assert good > 0.5 > bad


def test_refresh_retrains_only_when_votes_change(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        _seed(st, 60, 50)
        gates = refresh(st, ["medico", "geral"], EMB.name, tmp_path / "models", min_ratings=100, now=NOW)
        assert set(gates) == {"medico"}
        assert refresh(st, ["medico"], EMB.name, tmp_path / "models", min_ratings=100,
                       now=datetime(2026, 11, 9, tzinfo=timezone.utc))["medico"].version == "medico-20261108T100000"
        st.add_feedback("item", "n1", "up", "telegram")     # a changed vote is not a new vote: count stays 110
        st.add_feedback("item", "p0", "down", "telegram")
        _seed(st, 1, 0, start=500)                            # one more labeled item -> retrain
        later = datetime(2026, 11, 10, tzinfo=timezone.utc)
        assert refresh(st, ["medico"], EMB.name, tmp_path / "models", 100, now=later)["medico"].version \
            == "medico-20261110T000000"
