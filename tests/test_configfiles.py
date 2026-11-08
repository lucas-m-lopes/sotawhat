# tests/test_configfiles.py
from pathlib import Path

import pytest

from sotawhat.config import Settings
from sotawhat.configfiles import ConfigError, Mutes, load_config, load_llm_config, load_mutes, load_rubric
from sotawhat.items import Item

REPO_CONFIG = Path(__file__).resolve().parents[1] / "config"


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_missing_files_mean_defaults(tmp_path):
    config = load_config(tmp_path)
    assert config.rubric.min_total == 3.2 and config.rubric.weights == {"A": 0.35, "B": 0.35, "C": 0.2, "D": 0.1}
    assert config.mutes == Mutes() and config.llm == {"tasks": {}, "bakeoff": {}}


def test_repository_config_files_are_valid():
    config = load_config(REPO_CONFIG)
    assert (config.rubric.main_limit, config.rubric.frontier_limit) == (10, 5) and config.rubric.novelty_thresholds == (0.70, 0.76, 0.82, 0.88, 0.94)
    assert config.llm["tasks"]["triage"]["reasoning"] == "low"
    assert len(config.llm["bakeoff"]["triage"]) == 4


def test_rubric_overrides_and_validation(tmp_path):
    rubric = load_rubric(_write(tmp_path, "r.yaml", "min_total: 3.0\nweights: {A: 0.4, B: 0.4, C: 0.1, D: 0.1}\n"
                                                    "weak_sources: [rss:marktechpost]\n"))
    assert rubric.min_total == 3.0 and rubric.weights["A"] == 0.4 and rubric.weak_sources == ("rss:marktechpost",)
    with pytest.raises(ConfigError, match="somando 1"):
        load_rubric(_write(tmp_path, "r.yaml", "weights: {A: 0.5, B: 0.5, C: 0.5, D: 0.5}\n"))
    with pytest.raises(ConfigError, match="desconhecidas"):
        load_rubric(_write(tmp_path, "r.yaml", "min_totl: 3\n"))
    with pytest.raises(ConfigError, match="crescentes"):
        load_rubric(_write(tmp_path, "r.yaml", "novelty_thresholds: [0.9, 0.8, 0.7, 0.6, 0.5]\n"))
    with pytest.raises(ConfigError, match="YAML inválido"):
        load_rubric(_write(tmp_path, "r.yaml", "weights: {A: [\n"))


def test_mutes_match_with_reasons(tmp_path):
    mutes = load_mutes(_write(tmp_path, "m.yaml", "terms: [webinar]\ntitle_terms: [Sponsored]\n"
                                                  "domains: [example.com]\nauthors: [Spam Bot]\nsources: ['rss:*']\n"))

    def it(**kw):
        base = dict(id="x", kind="article", source="pubmed", source_id="", title="AI triage", url="https://ok.org/a",
                    authors=["Ana"], text="")
        base.update(kw)
        return Item(**base)

    assert mutes.match(it()) is None
    assert "webinar" in mutes.match(it(text="Join our WEBINAR on AI"))
    assert "título" in mutes.match(it(title="Sponsored: AI scribe"))
    assert "example.com" in mutes.match(it(url="https://news.example.com/x"))
    assert "Spam Bot" in mutes.match(it(authors=["spam bot"]))
    assert "rss:*" in mutes.match(it(source="rss:labs"))
    assert mutes.match(it(text="webinars are not a whole-word match")) is None
    with pytest.raises(ConfigError, match="listas"):
        load_mutes(_write(tmp_path, "m.yaml", "terms: webinar\n"))


def test_llm_config_validation(tmp_path):
    ok = load_llm_config(_write(tmp_path, "l.yaml", "tasks:\n  triage: {models: [a/b], reasoning: high}\n"
                                                    "bakeoff:\n  triage: [a/b, c/d]\n"))
    assert ok["tasks"]["triage"]["models"] == ["a/b"] and ok["bakeoff"]["triage"] == ["a/b", "c/d"]
    for bad in ("tasks:\n  triage: {models: [nope]}\n", "tasks:\n  triage: {reasoning: turbo}\n",
                "tasks:\n  triage: {max_tokens: -1}\n", "tasks:\n  triage: {temperature: 1}\n", "other: 1\n"):
        with pytest.raises(ConfigError):
            load_llm_config(_write(tmp_path, "l.yaml", bad))


def test_settings_paths_and_allowed_user(tmp_path):
    s = Settings(_env_file=None, sotawhat_data_dir=tmp_path, telegram_chat_id="42")
    assert s.models_dir == tmp_path / "models" and s.allowed_user_id == "42"
    assert s.embeddings_backend == "fastembed" and s.embeddings_model == "google/embeddinggemma-300m"
    assert Settings(_env_file=None, telegram_chat_id="42", telegram_allowed_user_id="7").allowed_user_id == "7"


def test_rubric_frontier_section_settings(tmp_path):
    from sotawhat.configfiles import Rubric
    default = Rubric()
    assert default.frontier_weights == {"A": 0.6, "C": 0.25, "D": 0.15} and default.frontier_min_total == 3.6
    assert (default.main_limit, default.frontier_limit, default.radar_limit) == (10, 5, 10)
    ok = load_rubric(_write(tmp_path, "r.yaml", "frontier_weights: {A: 0.5, C: 0.3, D: 0.2}\nfrontier_limit: 3\n"))
    assert ok.frontier_weights == {"A": 0.5, "C": 0.3, "D": 0.2} and ok.frontier_limit == 3
    for bad in ("frontier_weights: {A: 0.6, B: 0.4}\n", "frontier_weights: {A: 0.5, C: 0.3}\n"):
        with pytest.raises(ConfigError, match="frontier_weights"):
            load_rubric(_write(tmp_path, "r.yaml", bad))
