"""Votes both ways (2026-11-20): a vote made in the interface moves the ✅ of the Telegram buttons of every message that
carries the item, idea or tool; the interface reads the votes made in Telegram since its last look. No network: the
notifier is a double."""
import pytest
from fastapi.testclient import TestClient

from sotawhat.items import Item
from sotawhat.notify.telegram import TelegramError
from sotawhat.pipeline.feedback import mirror_vote, vote_changes
from sotawhat.store.db import Store
from sotawhat.web.app import create_app

BASE = "http://127.0.0.1:8765"


class FakeTelegram:
    def __init__(self, fail=False, configured=True):
        self.edits, self.fail, self.configured = [], fail, configured

    def edit_reply_markup(self, chat_id, message_id, reply_markup):
        if self.fail:
            raise TelegramError("editMessageReplyMarkup: HTTP 400 Bad Request: message is not modified", status=400)
        self.edits.append((str(chat_id), message_id, reply_markup))


def labels(markup) -> list:
    return [button["text"] for row in markup["inline_keyboard"] for button in row]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "insight.db"
    with Store(path) as st:
        run = st.start_run("daily")
        st.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"T{n}",
                              url=f"https://example.org/{n}", text="t", profile="medico") for n in (1, 2, 3)], run)
        # a digest message with one item, the radar list with two, an idea of the weekly report, a tool of the radar
        one = st.record_delivery(run, "2026-11-20", "pmid:1", "a000000001", "main", 1)
        two = st.record_delivery(run, "2026-11-20", "pmid:2", "a000000002", "radar", 1)
        three = st.record_delivery(run, "2026-11-20", "pmid:3", "a000000003", "radar", 2)
        idea = st.record_delivery(run, "2026-11-16", "idea:7", "a000000004", "idea", 1)
        tool = st.record_delivery(run, "2026-11-16", "tool:owner/repo", "a000000005", "tool", 1)
        st.record_delivery(run, "2026-11-21", "pmid:1", "a000000006", "main", 1)      # recorded, never sent
        st.mark_delivered([one], "42", 100)
        st.mark_delivered([two, three], "42", 101)
        st.mark_delivered([idea], "42", 102)
        st.mark_delivered([tool], "42", 103)
    return path


def test_a_vote_here_moves_the_check_on_every_message_that_carries_it(db):
    tg = FakeTelegram()
    with Store(db) as st:
        st.add_feedback("item", "pmid:2", "down", "telegram")              # voted there earlier
        st.add_feedback("item", "pmid:3", "up", "web")
        assert mirror_vote(st, tg, "item", "pmid:3", "up") == 1
        assert tg.edits[-1][:2] == ("42", 101) and labels(tg.edits[-1][2]) == ["1 👍", "✅1 👎", "✅2 👍", "2 👎"]
        st.add_feedback("item", "pmid:1", "test", "web")
        assert mirror_vote(st, tg, "item", "pmid:1", "test") == 1           # the unsent delivery has no message
        assert tg.edits[-1][:2] == ("42", 100) and labels(tg.edits[-1][2]) == ["👍", "👎", "✅🧪"]
        assert mirror_vote(st, tg, "idea", 7, "test") == 1
        assert labels(tg.edits[-1][2]) == ["👍 explorar", "👎", "✅🧪 testar", "🗄️ engavetar"]
        assert mirror_vote(st, tg, "tool", "owner/repo", "archive") == 1
        assert labels(tg.edits[-1][2]) == ["🧪 testar", "👍", "👎", "✅🗄️ depois"]
        assert mirror_vote(st, tg, "idea", 8, "up") == 0                    # never sent to Telegram
        assert mirror_vote(st, FakeTelegram(fail=True), "item", "pmid:1", "up") == 0      # logged, the vote stands
        assert mirror_vote(st, FakeTelegram(configured=False), "item", "pmid:1", "up") == 0
        assert mirror_vote(st, None, "item", "pmid:1", "up") == 0


def test_the_interface_reads_the_votes_made_in_telegram(db):
    with Store(db) as st:
        start = vote_changes(st)
        assert start == {"items": {}, "ideas": {}, "tools": {}, "cursor": 0}
        st.add_feedback("item", "pmid:1", "up", "telegram")
        st.add_feedback("item", "pmid:1", "down", "telegram")              # the latest vote wins
        st.add_feedback("idea", "7", "archive", "telegram")
        st.add_feedback("tool", "owner/repo", "up", "telegram")
        st.add_feedback("entity", "e5", "up", "web")                       # not a button of the interface
        changes = vote_changes(st, start["cursor"])
        assert changes == {"items": {"pmid:1": "down"}, "ideas": {"7": "engavetada"}, "tools": {"owner/repo": "up"},
                           "cursor": 5}
        assert vote_changes(st, changes["cursor"]) == {"items": {}, "ideas": {}, "tools": {}, "cursor": 5}


def test_the_web_vote_reaches_telegram_after_the_answer(db, tmp_path):
    tg = FakeTelegram()
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html>", encoding="utf-8")
    with TestClient(create_app(db, static_dir=static, telegram=tg), base_url=BASE) as c:
        cursor = c.get("/api/votes").json()["cursor"]
        voted = c.post("/api/feedback", json={"item_id": "pmid:1", "value": "test"}, headers={"origin": BASE})
        assert voted.status_code == 200 and voted.json()["vote"] == "test"
        assert tg.edits and tg.edits[-1][:2] == ("42", 100) and "✅🧪" in labels(tg.edits[-1][2])
        assert c.get(f"/api/votes?after={cursor}").json()["items"] == {"pmid:1": "test"}
        assert c.get("/api/votes?after=-1").status_code == 422
    with TestClient(create_app(db, static_dir=static), base_url=BASE) as bare:              # no Telegram: the vote alone
        assert bare.post("/api/feedback", json={"item_id": "pmid:2", "value": "up"}).status_code == 200
