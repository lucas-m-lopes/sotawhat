# sotawhat/pipeline/feedback.py
"""Telegram feedback (SDD §6.11, §7.7). Buttons -> `feedback`; messages from the user (links) ->
`inbox`, kept for manual capture (P5). Telegram keeps updates for 24 h only, so `run daily` pulls them
first, and `sotawhat feedback listen` can run all day as a logon task (instant ✅ on the buttons)."""
import logging
import re
import time
from datetime import datetime, timezone

from sotawhat.lessons.deliver import handle_callback as handle_lesson_callback
from sotawhat.notify.telegram import TelegramError
from sotawhat.pipeline.deliver import CODES, VOTES, idea_keyboard, keyboard
from sotawhat.store.db import utcnow

VALUES = {code: value for value, code in CODES.items()}
OFFSET_KEY = "telegram_offset"
LAST_PULL_KEY = "telegram_last_pull_at"
HEARTBEAT_KEY = "telegram_listener_at"
_URL = re.compile(r"https?://\S+")
log = logging.getLogger("sotawhat.feedback")


def parse_callback(data):
    parts = (data or "").split(":")
    if len(parts) == 3 and parts[0] == "f" and parts[2] in VALUES and re.fullmatch(r"[0-9a-f]{10}", parts[1]):
        return parts[1], VALUES[parts[2]]
    return None


def _answer(notifier, query, text):
    try:
        notifier.answer_callback(query["id"], text)
    except TelegramError:
        pass   # queries older than a few minutes can no longer be answered; the vote still counts


def handle_update(store, notifier, update, allowed_user) -> str:
    query = update.get("callback_query")
    if query is not None:
        if str((query.get("from") or {}).get("id")) != str(allowed_user):
            return "ignored"
        if handle_lesson_callback(store, notifier, query):        # quiz, lesson review, voice test
            return "vote"
        parsed = parse_callback(query.get("data"))
        row = store.delivery_by_key(parsed[0]) if parsed else None
        if row is None:
            _answer(notifier, query, "item não encontrado")
            return "ignored"
        value = parsed[1]
        message = query.get("message") or {}
        chat, message_id = (message.get("chat") or {}).get("id"), message.get("message_id")
        if row["item_id"].startswith("idea:"):                      # P4: weekly report ideas
            status = store.vote_idea(int(row["item_id"].split(":", 1)[1]), value, "telegram")
            _answer(notifier, query, f"ideia: {status}")
            if chat is not None and message_id:
                try:
                    notifier.edit_reply_markup(chat, message_id, idea_keyboard(row, value))
                except TelegramError:
                    pass
            return "vote"
        if value not in VOTES:
            _answer(notifier, query, "opção só vale para ideias")
            return "ignored"
        store.add_feedback("item", row["item_id"], value, "telegram")
        _answer(notifier, query, f"{VOTES[value]} registrado")
        rows = store.deliveries_for_message(chat, message_id) if chat is not None and message_id else []
        if rows:
            try:
                notifier.edit_reply_markup(chat, message_id,
                                           keyboard(rows, store.item_votes(ids=[r["item_id"] for r in rows])))
            except TelegramError:
                pass   # "message is not modified" or too old to edit
        return "vote"
    message = update.get("message")
    if message and str((message.get("from") or {}).get("id")) == str(allowed_user):
        text = message.get("text") or message.get("caption") or ""
        hidden = [e.get("url") for e in (message.get("entities") or message.get("caption_entities") or [])
                  if e.get("type") == "text_link" and e.get("url")]
        urls = list(dict.fromkeys(_URL.findall(text) + hidden))
        store.add_inbox("telegram", {"message_id": message.get("message_id"), "date": message.get("date"),
                                     "text": text, "urls": urls})
        if urls:                                          # P5: the capture is confirmed in the chat
            try:
                notifier.send_message(f"📥 recebido ({len(urls)} link{'s' if len(urls) > 1 else ''}): entra no "
                                      "próximo digest.", disable_notification=True)
            except TelegramError:
                pass
        return "inbox"
    return "ignored"


def pull(store, notifier, allowed_user, timeout=0) -> dict:
    """Process pending updates; with timeout=0 drain everything, otherwise long-poll one batch."""
    counts = {"vote": 0, "inbox": 0, "ignored": 0}
    offset = store.meta_get(OFFSET_KEY)
    while True:
        updates = notifier.get_updates(offset=int(offset) if offset else None, timeout=timeout)
        for update in updates:
            try:
                counts[handle_update(store, notifier, update, allowed_user)] += 1
            except Exception:  # noqa: BLE001 - one bad update must not block the queue
                log.exception("update %s", update.get("update_id"))
                counts["ignored"] += 1
            offset = update["update_id"] + 1
            store.meta_set(OFFSET_KEY, offset)
        if not updates or timeout:
            break
    store.meta_set(LAST_PULL_KEY, utcnow())
    return counts


def listener_active(store, now=None, max_age_s=180) -> bool:
    beat = store.meta_get(HEARTBEAT_KEY)
    if not beat:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - datetime.fromisoformat(beat)).total_seconds() < max_age_s


def listen(store, notifier, allowed_user, should_stop=lambda: False, timeout=50, sleep=time.sleep) -> None:
    while not should_stop():
        store.meta_set(HEARTBEAT_KEY, utcnow())
        try:
            counts = pull(store, notifier, allowed_user, timeout=timeout)
            if counts["vote"] or counts["inbox"]:
                log.info("feedback %s", counts)
        except TelegramError as exc:
            log.warning("telegram: %s", exc)
            sleep(60 if exc.status == 409 else 15)   # 409: another getUpdates is running


def main_feedback(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.notify.telegram import TelegramNotifier
    from sotawhat.pipeline.daily import setup_logging
    from sotawhat.store.db import Store

    settings = load_settings()
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if not notifier.configured:
        print("Telegram não configurado: preencha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env")
        return 2
    with Store(settings.db_path) as store:
        if ns.action == "pull":
            counts = pull(store, notifier, settings.allowed_user_id)
            print(f"votos {counts['vote']} · mensagens {counts['inbox']} · ignorados {counts['ignored']}")
            return 0
        setup_logging(settings.sotawhat_data_dir, datetime.now().date().isoformat(), settings.sotawhat_log_level)
        print("ouvindo o Telegram (Ctrl+C para sair)")
        try:
            listen(store, notifier, settings.allowed_user_id)
        except KeyboardInterrupt:
            pass
    return 0
