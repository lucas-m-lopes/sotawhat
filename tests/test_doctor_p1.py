# tests/test_doctor_p1.py
import json
from datetime import datetime, timedelta, timezone

from sotawhat.config import Settings
from sotawhat.doctor import (check_classifiers, check_config, check_embeddings, check_feedback, check_golden,
                             model_requirements)
from sotawhat.notify.telegram import TelegramError
from sotawhat.pipeline.feedback import HEARTBEAT_KEY, LAST_PULL_KEY
from sotawhat.store.db import Store

NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)


def test_requirements_cover_llm_yaml_and_bakeoff():
    llm = {"tasks": {"triage": {"models": ["a/x", "b/y"], "reasoning": "low"}},
           "bakeoff": {"triage": ["c/z"]}}
    needs = model_requirements(Settings(_env_file=None), llm)
    assert needs["a/x"] == {"low"} and needs["c/z"] == {"low"}
    assert "deepseek/deepseek-v4.1-flash-1017" in needs     # other tasks keep their defaults


def test_config_check(tmp_path):
    check, config = check_config(tmp_path)
    assert check.status == "warn" and config.rubric.min_total == 3.2       # no files: defaults
    (tmp_path / "rubric.yaml").write_text("weights: {A: 0.5, B: 0.5}\n", encoding="utf-8")
    check, config = check_config(tmp_path)
    assert check.status == "fail" and config is None and "somando 1" in check.detail


def test_embeddings_check(tmp_path):
    assert check_embeddings(Settings(_env_file=None, embeddings_backend="hash")).status == "warn"
    settings = Settings(_env_file=None, sotawhat_data_dir=tmp_path)
    assert check_embeddings(settings).status == "warn"                     # not downloaded yet
    (tmp_path / "models" / "fastembed" / "models--onnx-community--embeddinggemma-300m-ONNX").mkdir(parents=True)
    assert check_embeddings(settings).status == "ok"
    bad = Settings(_env_file=None, embeddings_model="nope/nope")
    assert check_embeddings(bad).status == "fail"


def test_classifier_feedback_and_golden_checks(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        [check] = check_classifiers(st, "m", 100, ["medico"])
        assert "0/100 votos" in check.detail
        st.record_classifier("medico-1", "medico", "m", 120, {"n": 120, "f1": 0.81, "auc": 0.9}, tmp_path / "c.pkl")
        assert "F1 0.81" in check_classifiers(st, "m", 100, ["medico"])[0].detail
        assert check_feedback(st, NOW).status == "warn"
        st.meta_set(LAST_PULL_KEY, (NOW - timedelta(hours=30)).isoformat())
        assert "24 h" in check_feedback(st, NOW).detail
        st.meta_set(LAST_PULL_KEY, (NOW - timedelta(hours=2)).isoformat())
        assert check_feedback(st, NOW).status == "ok"
        st.meta_set(HEARTBEAT_KEY, (NOW - timedelta(seconds=30)).isoformat())
        assert "listen" in check_feedback(st, NOW).detail
    path = tmp_path / "golden.jsonl"
    assert check_golden(path).status == "warn"
    path.write_text("".join(json.dumps({"id": str(i), "label": "main"}) + "\n" for i in range(50)), encoding="utf-8")
    assert check_golden(path).status == "ok"


def test_doctor_flags_a_chat_id_that_is_not_a_number():
    from sotawhat.doctor import check_settings
    s = Settings(_env_file=None, openrouter_api_key="k", telegram_bot_token="1:x", telegram_chat_id="Sotawhat_bot")
    telegram = {c.name: c for c in check_settings(s)}["Telegram"]
    assert telegram.status == "fail" and "número do chat" in telegram.detail
    ok = Settings(_env_file=None, openrouter_api_key="k", telegram_bot_token="1:x", telegram_chat_id="868708003")
    assert {c.name: c.status for c in check_settings(ok)}["Telegram"] == "ok"


class _Bot:
    chat_id = "42"

    def __init__(self, chat=None, updates=()):
        self.chat, self.updates = chat, list(updates)

    def get_me(self):
        return {"username": "Sotawhat_bot"}

    def get_chat(self):
        if self.chat is None:
            raise TelegramError("getChat: HTTP 400 Bad Request: chat not found", status=400)
        return self.chat

    def get_updates(self, offset=None, timeout=0):
        assert offset is None                       # a check must not consume the user's updates
        return self.updates


def test_doctor_reaches_the_chat_and_suggests_the_right_id():
    from sotawhat.doctor import check_telegram
    ok = check_telegram(_Bot({"type": "private", "first_name": "Lucas"}))
    assert (ok.status, ok.detail) == ("ok", "@Sotawhat_bot → chat private (Lucas)")
    start = {"update_id": 5, "message": {"chat": {"id": 868708003, "type": "private", "first_name": "Lucas"},
                                         "text": "/start"}}
    bad = check_telegram(_Bot(updates=[start]))
    assert bad.status == "fail" and "TELEGRAM_CHAT_ID=868708003 (Lucas)" in bad.detail
    assert "Iniciar" in check_telegram(_Bot()).detail


def test_doctor_checks_the_smtp_login_without_sending():
    from sotawhat.doctor import check_email
    from sotawhat.notify.email import EmailNotifier

    def no_network(*args, **kwargs):
        raise AssertionError("no connection expected")

    def factory(*args):
        return EmailNotifier(*args, smtp=no_network, smtp_ssl=no_network)

    assert check_email(Settings(_env_file=None)).status == "ok"                 # optional: off
    missing = check_email(Settings(_env_file=None, digest_email_to="eu@gmail.com"), factory=factory)
    assert missing.status == "fail" and "GMAIL_APP_PASSWORD" in missing.detail
    account = Settings(_env_file=None, digest_email_to="eu@gmail.com", gmail_address="eu@gmail.com",
                       gmail_app_password="Senha123!")
    refused = check_email(account, factory=factory)
    assert refused.status == "fail" and "senha de app" in refused.detail       # refused before connecting
    calls = []

    class Mail:
        def __init__(self, *args):
            calls.append(args)

        def check_login(self):
            return None

    good = Settings(_env_file=None, digest_email_to="eu@gmail.com", gmail_address="eu@gmail.com",
                    gmail_app_password="abcd efgh ijkl mnop")
    ok = check_email(good, factory=Mail)
    assert ok.status == "ok" and "smtp.gmail.com:587" in ok.detail
    assert calls == [("smtp.gmail.com", 587, "eu@gmail.com", "abcd efgh ijkl mnop")]


def test_notifier_get_chat_payload():
    import httpx

    from sotawhat.notify.telegram import TelegramNotifier
    seen = []

    def handler(request):
        seen.append((request.url.path.rsplit("/", 1)[-1], json.loads(request.content)))
        return httpx.Response(200, json={"ok": True, "result": {"type": "private"}})

    bot = TelegramNotifier("1:x", "42", transport=httpx.MockTransport(handler))
    assert bot.get_chat() == {"type": "private"} and seen == [("getChat", {"chat_id": "42"})]


def test_doctor_warns_when_a_dotenv_model_pin_hides_llm_yaml():
    from sotawhat.doctor import check_model_pins
    llm = {"tasks": {"triage": {"models": ["minimax/minimax-m3.1-flash", "z-ai/glm-5.3-flash"]}}, "bakeoff": {}}
    pinned = Settings(_env_file=None, sotawhat_model_triage="deepseek/deepseek-v4.1-flash-1017")
    check = check_model_pins(pinned, llm)
    assert check.status == "warn" and "SOTAWHAT_MODEL_TRIAGE" in check.detail and "minimax/minimax-m3.1-flash" in check.detail
    assert check_model_pins(Settings(_env_file=None), llm).status == "ok"
    same = Settings(_env_file=None, sotawhat_model_triage="minimax/minimax-m3.1-flash")
    assert check_model_pins(same, llm).status == "ok"
