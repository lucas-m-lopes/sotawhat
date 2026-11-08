# tests/conftest.py
import os

import pytest

from sotawhat.config import Settings

_PREFIXES = ("SOTAWHAT_", "OPENROUTER_", "TELEGRAM_", "CROSSREF_", "GMAIL_", "SMTP_", "DIGEST_")


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Tests never see the developer's real keys: none of our environment variables and no `.env` file,
    whatever the working directory (the real `.env` holds live OpenRouter, Telegram and Gmail secrets)."""
    for key in list(os.environ):
        if key.startswith(_PREFIXES):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
