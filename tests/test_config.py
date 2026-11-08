# tests/test_config.py
from pathlib import Path

import pytest

from sotawhat.config import Settings, load_settings


@pytest.fixture(autouse=True)
def _in_empty_dir(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no stray `.env` from the repository root


def test_defaults_are_private_and_cheap():
    s = load_settings()
    assert s.openrouter_zdr is True
    assert s.openrouter_data_collection == "deny"
    assert s.quantizations == ["fp8", "bf16", "fp16", "fp32", "unknown"]
    assert s.sotawhat_llm_budget_usd_day == 1.0
    assert s.db_path == Path("data") / "insight.db"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("OPENROUTER_ZDR", "false")
    monkeypatch.setenv("SOTAWHAT_MODEL_TRIAGE", "xiaomi/mimo-v2.6-flash")
    monkeypatch.setenv("SOTAWHAT_LLM_BUDGET_USD_DAY", "0.5")
    s = load_settings()
    assert s.openrouter_zdr is False
    assert s.model_override("triage") == "xiaomi/mimo-v2.6-flash"
    assert s.model_override("extract") == ""
    assert s.sotawhat_llm_budget_usd_day == 0.5


def test_reads_dotenv_in_working_directory(tmp_path):
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=sk-test\nTELEGRAM_CHAT_ID=42\n", encoding="utf-8")
    s = Settings()
    assert s.openrouter_api_key == "sk-test"
    assert s.telegram_chat_id == "42"
