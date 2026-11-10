# tests/test_deliver.py
import json

import httpx

from sotawhat.configfiles import Rubric
from sotawhat.items import Item
from sotawhat.notify.telegram import TelegramError, TelegramNotifier
from sotawhat.pipeline.daily import DailyReport
from sotawhat.pipeline.deliver import (build_digest, item_key, keyboard, render_html, render_markdown, send_digest,
                                       telegram_messages, write_files)
from sotawhat.pipeline.triage import TriageStats
from sotawhat.store.db import Store

TOKEN = "123456:SECRET-TOKEN"


class FakeBot:
    def __init__(self, updates=()):
        self.chat_id = "42"
        self.sent, self.answers, self.edits = [], [], []
        self.updates = list(updates)

    def send_message(self, text, reply_markup=None, disable_notification=False):
        self.sent.append((text, reply_markup, disable_notification))
        return {"message_id": 100 + len(self.sent)}

    def get_updates(self, offset=None, timeout=0):
        batch = [u for u in self.updates if offset is None or u["update_id"] >= offset]
        self.updates = []
        return batch

    def answer_callback(self, callback_id, text=""):
        self.answers.append(text)

    def edit_reply_markup(self, chat_id, message_id, markup):
        self.edits.append((chat_id, message_id, markup))


def _seed(st):
    run = st.start_run("daily")
    items = [Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"Título <{n}>",
                  url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", profile="medico") for n in range(1, 7)]
    st.upsert_items(items, run)
    rows = [("pmid:1", "main", 4.2, {"A": 4, "B": 5, "C": 3, "D": 5}),
            ("pmid:2", "main", 3.5, {"A": 3, "B": 4, "C": 3, "D": 5}),
            ("pmid:3", "radar", 2.9, {"A": 5, "B": 1, "C": 4, "D": 5}),
            ("pmid:4", "reject", 1.0, {"A": 0, "B": 1, "C": 0, "D": 5}),
            ("pmid:5", "frontier", 4.4, {"A": 5, "B": 0, "C": 4, "D": 4}),
            ("pmid:6", "frontier", 3.9, {"A": 4, "B": 1, "C": 3, "D": 5})]
    for item_id, decision, total, scores in rows:
        st.record_triage(item_id, run, decision, total=total, scores=scores, summary_pt=f"Resumo de {item_id}.",
                         why_it_matters_pt="Útil para o PS.", tags={"domains": ["A06"], "techniques": ["C02"],
                                                                    "evidence_stage": "D2"})
    report = DailyReport(run_id=run, day="2026-11-08", collected={"medico": 4}, new_items=items,
                         failing={"semantic_scholar": (3, "429 Too Many Requests"), "arxiv": (1, "timeout")},
                         cost_usd=0.0123, triage=TriageStats(triaged=4, main=2, radar=1, rejected=1, deferred=2))
    return run, report



def test_digest_ranks_limits_and_renders(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run, report = _seed(st)
        d = build_digest(st, report, Rubric(main_limit=1, frontier_limit=1))
        assert [e.item_id for e in d.main] == ["pmid:1"] and [e.item_id for e in d.extra] == ["pmid:2"]
        assert [e.item_id for e in d.frontier] == ["pmid:5"] and d.worth_sending
        # frontier items beyond the limit become the first radar lines; numbering runs on across sections
        assert [e.item_id for e in d.radar] == ["pmid:6", "pmid:3"]
        assert [e.position for e in d.main + d.frontier] == [1, 2] and [e.position for e in d.radar] == [1, 2]
        assert "saúde 1 · fronteira 1 · radar 2 · custo US$ 0,01" in d.stats_line
        assert any("2 itens ficaram" in n for n in d.notes) and any("+1 aprovados" in n for n in d.notes)
        md = render_markdown(d)
        assert "### 1. [Título <1>](https://pubmed.ncbi.nlm.nih.gov/1/)" in md and "**4,20** · A4 B5 C3 D5" in md
        assert "emergência/triagem" in md and "3ª falha seguida" in md and "## ➕ Também aprovados" in md
        assert md.startswith("# 🗞️ SOTA What · 08/11/2026\n\n📊 coletados")
        assert md.index("## 🩺 IA ∩ Saúde") < md.index("## 🔭 Fronteira de IA") < md.index("## 📡 Radar")
        assert "### 2. [Título <5>](https://pubmed.ncbi.nlm.nih.gov/5/)" in md
        page = render_html(d)
        assert "Título &lt;1&gt;" in page and "<script" not in page and 'lang="pt-BR"' in page
        assert "<h2>🔭 Fronteira de IA</h2>" in page and "<title>SOTA What · 08/11/2026</title>" in page
        md_path, html_path = write_files(d, tmp_path / "digests")
        assert md_path.name == "2026-11-08.md" and html_path.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_nothing_relevant_and_no_alerts_sends_nothing(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        report = DailyReport(run_id=run, day="2026-11-08", failing={"arxiv": (1, "timeout")},
                             triage=TriageStats())
        d = build_digest(st, report, Rubric())
        assert not d.worth_sending and "Nada relevante hoje." in render_markdown(d)


def test_telegram_messages_buttons_and_delivery_records(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run, report = _seed(st)
        d = build_digest(st, report, Rubric())
        messages = telegram_messages(d)
        assert len(messages) == 6 and messages[0]["silent"] is False and all(m["silent"] for m in messages[1:])
        assert "saúde 2 · fronteira 2 · radar 1" in messages[0]["text"]
        assert messages[0]["text"].startswith("🗞️ <b>SOTA What</b> · 08/11/2026\n📊 coletados")
        assert messages[1]["text"].startswith("🩺 <b>1.</b>") and messages[3]["text"].startswith("🔭 <b>3.</b>")
        assert "Fronteira de IA" not in messages[1]["text"]
        assert "⚠️ <b>Alertas</b>: semantic_scholar (3ª falha seguida)" in messages[0]["text"]
        assert "falha hoje: arxiv" in messages[0]["text"] and "Título &lt;1&gt;" in messages[1]["text"]
        bot = FakeBot()
        assert send_digest(bot, st, d, run, pause=0) == 6
        main_markup = bot.sent[1][1]["inline_keyboard"]
        key = item_key("pmid:1")
        assert main_markup == [[{"text": "👍", "callback_data": f"f:{key}:u"},
                                {"text": "👎", "callback_data": f"f:{key}:d"},
                                {"text": "🧪", "callback_data": f"f:{key}:t"}]]
        assert bot.sent[5][1]["inline_keyboard"][0][0]["text"] == "👍"   # one radar item: plain buttons
        assert st.delivery_by_key(item_key("pmid:5"))["section"] == "frontier"
        row = st.delivery_by_key(key)
        assert (row["item_id"], row["message_id"], row["chat_id"]) == ("pmid:1", 102, "42")


def test_keyboard_marks_the_chosen_vote():
    rows = [{"key": "a" * 10, "position": 1, "item_id": "x"}, {"key": "b" * 10, "position": 2, "item_id": "y"}]
    kb = keyboard(rows, {"y": "down"})["inline_keyboard"]
    assert [b["text"] for b in kb[0]] == ["1 👍", "1 👎", "2 👍", "✅2 👎"]


def test_notifier_buttons_updates_and_flood_control():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append((request.url.path.rsplit("/", 1)[-1], body))
        if len(calls) == 1:
            return httpx.Response(429, json={"ok": False, "parameters": {"retry_after": 3}})
        if calls[-1][0] == "getUpdates":
            return httpx.Response(200, json={"ok": True, "result": []})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 9}})

    waits = []
    bot = TelegramNotifier(TOKEN, "42", transport=httpx.MockTransport(handler), sleep=waits.append)
    assert bot.send_message("oi", reply_markup={"inline_keyboard": []}, disable_notification=True) == {"message_id": 9}
    assert waits == [3.0] and calls[1][1]["disable_notification"] is True
    assert bot.get_updates(offset=10, timeout=0) == [] and calls[2][1] == {
        "timeout": 0, "allowed_updates": ["callback_query", "message"], "offset": 10}
    bot.answer_callback("c1", "ok")
    bot.edit_reply_markup(42, 9, {"inline_keyboard": []})
    assert [c[0] for c in calls[3:]] == ["answerCallbackQuery", "editMessageReplyMarkup"]


def test_notifier_error_keeps_status_without_token():
    bot = TelegramNotifier(TOKEN, "42", transport=httpx.MockTransport(
        lambda r: httpx.Response(409, json={"ok": False, "description": "Conflict"})))
    try:
        bot.get_updates()
    except TelegramError as exc:
        assert exc.status == 409 and "SECRET" not in str(exc)
    else:
        raise AssertionError("expected TelegramError")
