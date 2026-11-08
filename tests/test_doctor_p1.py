# tests/test_doctor_p1.py
import json
from datetime import datetime, timedelta, timezone

from sotawhat.config import Settings
from sotawhat.doctor import (check_classifiers, check_config, check_embeddings, check_feedback, check_golden,
                             model_requirements)
from sotawhat.pipeline.feedback import HEARTBEAT_KEY, LAST_PULL_KEY
from sotawhat.store.db import Store

NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)


def test_requirements_cover_llm_yaml_and_bakeoff():
    llm = {"tasks": {"triage": {"models": ["a/x", "b/y"], "reasoning": "low"}},
           "bakeoff": {"triage": ["c/z"]}}
    needs = model_requirements(Settings(_env_file=None), llm)
    assert needs["a/x"] == {"low"} and needs["c/z"] == {"low"}
    assert "deepseek/deepseek-v4.1-flash-1017" in needs     # other tasks keep their defaults


def test_config_check(tmp_path):
    check, config = check_config(tmp_path)
    assert check.status == "warn" and config.rubric.min_total == 3.2       # no files: defaults
    (tmp_path / "rubric.yaml").write_text("weights: {A: 0.5, B: 0.5}\n", encoding="utf-8")
    check, config = check_config(tmp_path)
    assert check.status == "fail" and config is None and "somando 1" in check.detail


def test_embeddings_check(tmp_path):
    assert check_embeddings(Settings(_env_file=None, embeddings_backend="hash")).status == "warn"
    settings = Settings(_env_file=None, sotawhat_data_dir=tmp_path)
    assert check_embeddings(settings).status == "warn"                     # not downloaded yet
    (tmp_path / "models" / "fastembed" / "models--onnx-community--embeddinggemma-300m-ONNX").mkdir(parents=True)
    assert check_embeddings(settings).status == "ok"
    bad = Settings(_env_file=None, embeddings_model="nope/nope")
    assert check_embeddings(bad).status == "fail"


def test_classifier_feedback_and_golden_checks(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        [check] = check_classifiers(st, "m", 100, ["medico"])
        assert "0/100 votos" in check.detail
        st.record_classifier("medico-1", "medico", "m", 120, {"n": 120, "f1": 0.81, "auc": 0.9}, tmp_path / "c.pkl")
        assert "F1 0.81" in check_classifiers(st, "m", 100, ["medico"])[0].detail
        assert check_feedback(st, NOW).status == "warn"
        st.meta_set(LAST_PULL_KEY, (NOW - timedelta(hours=30)).isoformat())
        assert "24 h" in check_feedback(st, NOW).detail
        st.meta_set(LAST_PULL_KEY, (NOW - timedelta(hours=2)).isoformat())
        assert check_feedback(st, NOW).status == "ok"
        st.meta_set(HEARTBEAT_KEY, (NOW - timedelta(seconds=30)).isoformat())
        assert "listen" in check_feedback(st, NOW).detail
    path = tmp_path / "golden.jsonl"
    assert check_golden(path).status == "warn"
    path.write_text("".join(json.dumps({"id": str(i), "label": "main"}) + "\n" for i in range(50)), encoding="utf-8")
    assert check_golden(path).status == "ok"
