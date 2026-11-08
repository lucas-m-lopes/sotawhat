# tests/test_telegram.py
import json

import httpx
import pytest

from sotawhat.notify.telegram import TelegramError, TelegramNotifier, chunk, esc

TOKEN = "123456:SECRET-TOKEN"


def _notifier(handler):
    return TelegramNotifier(TOKEN, "42", transport=httpx.MockTransport(handler))


def test_send_posts_html_message_to_bot_api():
    seen = []

    def handler(request):
        seen.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    assert _notifier(handler).send("<b>oi</b>") == 1
    path, body = seen[0]
    assert path == f"/bot{TOKEN}/sendMessage"
    assert body == {"chat_id": "42", "text": "<b>oi</b>", "parse_mode": "HTML", "disable_web_page_preview": True}


def test_long_text_is_split_on_lines():
    text = "\n".join(["x" * 100] * 50)          # 5.049 characters
    parts = chunk(text)
    assert len(parts) == 2 and all(len(p) <= 4096 for p in parts)
    assert "\n".join(parts) == text
    assert chunk("y" * 5000) == ["y" * 4096, "y" * 904]


def test_errors_never_leak_the_token():
    def handler(request):
        return httpx.Response(401, json={"ok": False, "description": "Unauthorized"})

    with pytest.raises(TelegramError) as err:
        _notifier(handler).send("x")
    assert "SECRET" not in str(err.value) and "401" in str(err.value)


def test_esc_and_configured():
    assert esc("a < b & c") == "a &lt; b &amp; c"
    assert TelegramNotifier("", "").configured is False
