# sotawhat/notify/telegram.py
"""Send-only Telegram notifier (SDD §7.7). The bot token never appears in raised errors."""
import html

import httpx

API = "https://api.telegram.org"
LIMIT = 4096


class TelegramError(Exception):
    pass


def esc(text) -> str:
    return html.escape(str(text), quote=False)


def esc_attr(text) -> str:
    return html.escape(str(text), quote=True)


def chunk(text, limit=LIMIT) -> list:
    """Split on line boundaries (HTML tags never span lines here); hard-split overlong lines."""
    parts, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            parts.append(current)
            current = line
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


class TelegramNotifier:
    def __init__(self, token, chat_id, transport=None, timeout=30.0):
        self.token = token
        self.chat_id = chat_id
        self._http = httpx.Client(base_url=f"{API}/bot{token}", timeout=timeout, transport=transport)

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def _call(self, method, payload=None) -> dict:
        try:
            response = self._http.post(f"/{method}", json=payload or {})
        except httpx.TransportError as exc:
            raise TelegramError(f"{method}: transport error {type(exc).__name__}") from None
        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code != 200 or not data.get("ok"):
            raise TelegramError(f"{method}: HTTP {response.status_code} {data.get('description', '')}".strip())
        return data.get("result") or {}

    def send(self, text, parse_mode="HTML") -> int:
        parts = chunk(text)
        for part in parts:
            self._call("sendMessage", {"chat_id": self.chat_id, "text": part, "parse_mode": parse_mode,
                                       "disable_web_page_preview": True})
        return len(parts)

    def get_me(self) -> dict:
        return self._call("getMe")
