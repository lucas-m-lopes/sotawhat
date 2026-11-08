# tests/test_feedback.py
import json
from datetime import datetime, timedelta, timezone

from sotawhat.configfiles import Rubric
from sotawhat.items import Item
from sotawhat.notify.telegram import TelegramError
from sotawhat.pipeline.daily import DailyReport
from sotawhat.pipeline.deliver import build_digest, item_key, send_digest
from sotawhat.pipeline.feedback import HEARTBEAT_KEY, handle_update, listen, listener_active, parse_callback, pull
from sotawhat.pipeline.triage import TriageStats
from sotawhat.store.db import Store

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
                  url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", profile="medico") for n in range(1, 5)]
    st.upsert_items(items, run)
    rows = [("pmid:1", "main", 4.2, {"A": 4, "B": 5, "C": 3, "D": 5}),
            ("pmid:2", "main", 3.5, {"A": 3, "B": 4, "C": 3, "D": 5}),
            ("pmid:3", "radar", 2.9, {"A": 5, "B": 1, "C": 4, "D": 5}),
            ("pmid:4", "reject", 1.0, {"A": 0, "B": 1, "C": 0, "D": 5})]
    for item_id, decision, total, scores in rows:
        st.record_triage(item_id, run, decision, total=total, scores=scores, summary_pt=f"Resumo de {item_id}.",
                         why_it_matters_pt="Útil para o PS.", tags={"domains": ["A06"], "techniques": ["C02"],
                                                                    "evidence_stage": "D2"})
    report = DailyReport(run_id=run, day="2026-11-08", collected={"medico": 4}, new_items=items,
                         failing={"semantic_scholar": (3, "429 Too Many Requests"), "arxiv": (1, "timeout")},
                         cost_usd=0.0123, triage=TriageStats(triaged=4, main=2, radar=1, rejected=1, deferred=2))
    return run, report



def test_votes_are_recorded_acknowledged_and_shown(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run, report = _seed(st)
        d = build_digest(st, report, Rubric())
        bot = FakeBot()
        send_digest(bot, st, d, run, pause=0)
        key = item_key("pmid:1")
        vote = {"update_id": 7, "callback_query": {"id": "cq1", "from": {"id": 42}, "data": f"f:{key}:t",
                                                   "message": {"message_id": 102, "chat": {"id": 42}}}}
        stranger = {"update_id": 8, "callback_query": {"id": "cq2", "from": {"id": 666}, "data": f"f:{key}:d"}}
        link = {"update_id": 9, "message": {"message_id": 5, "from": {"id": 42}, "date": 1,
                                            "text": "olha https://example.org/post?x=1"}}
        bot.updates = [vote, stranger, link]
        assert pull(st, bot, "42") == {"vote": 1, "inbox": 1, "ignored": 1}
        assert st.item_votes() == {"pmid:1": "test"} and bot.answers == ["🧪 registrado"]
        assert bot.edits[0][2]["inline_keyboard"][0][2]["text"] == "✅🧪"
        payload = json.loads(st.conn.execute("SELECT payload_json FROM inbox").fetchone()[0])
        assert payload["urls"] == ["https://example.org/post?x=1"]
        assert st.meta_get("telegram_offset") == "10" and st.meta_get("telegram_last_pull_at")
        assert parse_callback("f:zz:u") is None and parse_callback(f"f:{key}:x") is None
        assert handle_update(st, bot, {"update_id": 1, "callback_query": {"id": "c", "from": {"id": 42},
                                                                          "data": "f:0123456789:u"}}, "42") == "ignored"


def test_listener_heartbeat(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        assert not listener_active(st, now)
        st.meta_set(HEARTBEAT_KEY, (now - timedelta(seconds=60)).isoformat())
        assert listener_active(st, now) and not listener_active(st, now + timedelta(minutes=5))


def test_listen_survives_conflicts_and_keeps_a_heartbeat(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        class Bot(FakeBot):
            calls = 0

            def get_updates(self, offset=None, timeout=0):
                Bot.calls += 1
                if Bot.calls == 1:
                    raise TelegramError("getUpdates: HTTP 409 Conflict", status=409)
                return []

        waits = []
        listen(st, Bot(), "42", should_stop=lambda: Bot.calls >= 2, timeout=1, sleep=waits.append)
        assert waits == [60] and listener_active(st)
