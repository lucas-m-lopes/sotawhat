# sotawhat/notify/telegram.py
"""Telegram Bot API client (SDD §7.7): messages with inline buttons, updates (votes and links) and
button refresh. The bot token never appears in raised errors."""
import html
import json
import time
from pathlib import Path

import httpx

API = "https://api.telegram.org"
LIMIT = 4096


class TelegramError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


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
    def __init__(self, token, chat_id, transport=None, timeout=30.0, sleep=time.sleep):
        self.token = token
        self.chat_id = chat_id
        self._http = httpx.Client(base_url=f"{API}/bot{token}", timeout=timeout, transport=transport)
        self._sleep = sleep

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def _call(self, method, payload=None, timeout=None, files=None):
        for attempt in range(2):
            try:
                if files:   # multipart upload (video, audio): the other fields go as form fields
                    form = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in (payload or {}).items()}
                    opened = {k: (name, open(path, "rb"), mime) for k, (name, path, mime) in files.items()}
                    try:
                        response = self._http.post(f"/{method}", data=form, files=opened,
                                                   timeout=timeout or httpx.USE_CLIENT_DEFAULT)
                    finally:
                        for _, handle, _ in opened.values():
                            handle.close()
                else:
                    response = self._http.post(f"/{method}", json=payload or {},
                                               timeout=timeout or httpx.USE_CLIENT_DEFAULT)
            except httpx.TransportError as exc:
                raise TelegramError(f"{method}: transport error {type(exc).__name__}") from None
            try:
                data = response.json()
            except ValueError:
                data = {}
            if response.status_code == 429 and attempt == 0:   # flood control: wait as told, once
                self._sleep(min(float((data.get("parameters") or {}).get("retry_after", 1)), 30.0))
                continue
            if response.status_code != 200 or not data.get("ok"):
                raise TelegramError(f"{method}: HTTP {response.status_code} {data.get('description', '')}".strip(),
                                    status=response.status_code)
            return data.get("result")

    def send(self, text, parse_mode="HTML") -> int:
        parts = chunk(text)
        for part in parts:
            self._call("sendMessage", {"chat_id": self.chat_id, "text": part, "parse_mode": parse_mode,
                                       "disable_web_page_preview": True})
        return len(parts)

    def send_message(self, text, reply_markup=None, disable_notification=False, parse_mode="HTML") -> dict:
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode,
                   "disable_web_page_preview": True}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if disable_notification:
            payload["disable_notification"] = True
        return self._call("sendMessage", payload) or {}

    def get_updates(self, offset=None, timeout=0, allowed_updates=("callback_query", "message")) -> list:
        payload = {"timeout": timeout, "allowed_updates": list(allowed_updates)}
        if offset is not None:
            payload["offset"] = offset
        return self._call("getUpdates", payload, timeout=timeout + 15) or []

    def answer_callback(self, callback_id, text="") -> None:
        self._call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})

    def edit_reply_markup(self, chat_id, message_id, reply_markup) -> None:
        self._call("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": message_id,
                                              "reply_markup": reply_markup})

    def edit_message_text(self, chat_id, message_id, text, reply_markup=None, parse_mode="HTML") -> None:
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode,
                   "disable_web_page_preview": True}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        self._call("editMessageText", payload)

    def send_video(self, path, caption="", reply_markup=None, duration=None, width=None, height=None) -> dict:
        """Up to 50 MB with the cloud Bot API; the player streams it (supports_streaming)."""
        payload = {"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML", "supports_streaming": "true"}
        for key, value in (("duration", duration), ("width", width), ("height", height)):
            if value:
                payload[key] = int(value)
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._call("sendVideo", payload, timeout=600,
                          files={"video": (Path(path).name, path, "video/mp4")}) or {}

    def send_document(self, path, caption="", mime="text/html", name=None, disable_notification=False) -> dict:
        """A file (the interactive 3D page of a lesson); up to 50 MB with the cloud Bot API."""
        payload = {"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"}
        if disable_notification:
            payload["disable_notification"] = "true"
        return self._call("sendDocument", payload, timeout=300, files={"document": (name or Path(path).name, path, mime)}) or {}

    def send_audio(self, path, title="", caption="", reply_markup=None) -> dict:
        payload = {"chat_id": self.chat_id, "title": title, "caption": caption, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._call("sendAudio", payload, timeout=120, files={"audio": (Path(path).name, path, "audio/wav")}) or {}

    def get_me(self) -> dict:
        return self._call("getMe") or {}

    def get_chat(self) -> dict:
        return self._call("getChat", {"chat_id": self.chat_id}) or {}
