# tests/conftest.py
import os

import pytest

_PREFIXES = ("SOTAWHAT_", "OPENROUTER_", "TELEGRAM_", "CROSSREF_")


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Tests never see the developer's real keys (a real `.env` is avoided per test)."""
    for key in list(os.environ):
        if key.startswith(_PREFIXES):
            monkeypatch.delenv(key, raising=False)
