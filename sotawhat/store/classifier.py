# sotawhat/store/classifier.py
"""Per-profile relevance classifier (SDD §6.7, D9): logistic regression over the local embeddings,
trained on the user's votes (👍/🧪 positive, 👎 negative). Below `min_ratings` votes nothing is trained
and the LLM sees every item (cold start); afterwards the classifier decides which items reach it."""
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

POSITIVE = {"up", "test"}
NEGATIVE = {"down"}


@dataclass
class Gate:
    version: str
    model: object

    def score(self, vectors) -> np.ndarray:
        return self.model.predict_proba(np.asarray(vectors, dtype=np.float32))[:, 1]


def training_data(store, profile, embed_model):
    votes = {i: v for i, v in store.item_votes(profile=profile).items() if v in POSITIVE | NEGATIVE}
    ids, matrix = store.load_embeddings(embed_model, ids=list(votes))
    labels = np.array([1 if votes[i] in POSITIVE else 0 for i in ids], dtype=int)
    return ids, matrix, labels, len(votes)


def train(store, profile, embed_model, models_dir, min_ratings=100, now=None):
    """Train, cross-validate, save and register a classifier; None when there is not enough data."""
    ids, X, y, n_votes = training_data(store, profile, embed_model)
    if len(ids) < min_ratings or len(set(y.tolist())) < 2:
        return None
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    model = LogisticRegression(class_weight="balanced", max_iter=2000)
    metrics = {"n": int(len(y)), "positives": int(y.sum()), "votes": n_votes}
    folds = min(5, int(np.bincount(y).min()))
    if folds >= 2:
        proba = cross_val_predict(model, X, y, cv=StratifiedKFold(folds, shuffle=True, random_state=13),
                                  method="predict_proba")[:, 1]
        p, r, f1, _ = precision_recall_fscore_support(y, (proba >= 0.5).astype(int), average="binary",
                                                      zero_division=0)
        metrics.update(precision=round(float(p), 3), recall=round(float(r), 3), f1=round(float(f1), 3),
                       auc=round(float(roc_auc_score(y, proba)), 3))
    model.fit(X, y)
    version = f"{profile}-{(now or datetime.now(timezone.utc)).strftime('%Y%m%dT%H%M%S')}"
    path = Path(models_dir) / f"classifier-{version}.pkl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(model))
    store.record_classifier(version, profile, embed_model, int(len(y)), metrics, path)
    return {"version": version, "metrics": metrics}


def load_gate(store, profile, embed_model):
    row = store.latest_classifier(profile, embed_model)
    if row is None or not Path(row["path"]).exists():
        return None
    return Gate(row["version"], pickle.loads(Path(row["path"]).read_bytes()))   # our own file in data/models


def refresh(store, profiles, embed_model, models_dir, min_ratings=100, now=None) -> dict:
    """Retrain a profile whenever its vote count changed since the last model; return the gates."""
    import json

    gates = {}
    for profile in profiles:
        latest = store.latest_classifier(profile, embed_model)
        trained_votes = json.loads(latest["metrics_json"] or "{}").get("votes") if latest else None
        current = len([v for v in store.item_votes(profile=profile).values() if v in POSITIVE | NEGATIVE])
        if current >= min_ratings and current != trained_votes:
            train(store, profile, embed_model, models_dir, min_ratings, now)
        gate = load_gate(store, profile, embed_model)
        if gate is not None:
            gates[profile] = gate
    return gates
