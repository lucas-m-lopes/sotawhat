# tests/test_email.py
import smtplib

import pytest

from sotawhat.config import Settings
from sotawhat.notify.email import EmailError, EmailNotifier, looks_like_app_password
from sotawhat.pipeline.deliver import Digest, Entry, render_email, send_email


def _entry(n, section, total):
    return Entry(item_id=f"pmid:{n}", title=f"Título <{n}>", url=f"https://example.org/{n}", source="pubmed",
                 profile="medico", total=total, scores={"A": 4, "B": 5, "C": 3, "D": 5}, summary=f"Resumo {n}.",
                 why="Útil para o PS.", tags={"domains": ["A06"]}, sources=["pubmed"], section=section, position=n)


def _digest():
    return Digest(day="2026-11-08", stats_line="coletados 9 · saúde 1 · fronteira 1 · radar 1",
                  main=[_entry(1, "main", 4.2)], radar=[_entry(3, "radar", 2.9)], extra=[],
                  failing=[("arxiv", 3, "timeout")], frontier=[_entry(2, "frontier", 4.4)])


def fake_smtp(log, fail_login=False):
    class FakeSMTP:
        def __init__(self, host, port, timeout=None, context=None):
            log.append(("connect", host, port, context is not None))

        def ehlo(self):
            log.append("ehlo")

        def starttls(self, context=None):
            log.append(("starttls", context is not None))

        def login(self, user, password):
            log.append(("login", user, password))
            if fail_login:
                raise smtplib.SMTPAuthenticationError(534, b"5.7.9 Application-specific password required")

        def send_message(self, msg):
            log.append(("send", msg))

        def quit(self):
            log.append("quit")

        def close(self):
            log.append("close")

    return FakeSMTP


def test_email_copy_has_both_sections_inline_styles_and_a_plain_part():
    subject, text, html = render_email(_digest())
    assert subject == "🗞️ SOTA What · 08/11 · 🩺 1 em IA ∩ Saúde · 🔭 1 na fronteira · ⚠️"
    assert "## 🩺 IA ∩ Saúde" in text and "## 🔭 Fronteira de IA" in text and "🗞️ SOTA What · 08/11/2026" in html
    assert "Título &lt;1&gt;" in html and 'style="' in html and "<style" not in html and "var(--" not in html
    assert html.index("IA ∩ Saúde") < html.index("Fronteira de IA") < html.index("Radar")
    assert "Telegram" in html                                    # votes stay in Telegram


def test_send_over_starttls_with_the_app_password_without_spaces():
    log = []
    mail = EmailNotifier("smtp.gmail.com", 587, "eu@gmail.com", "abcd efgh ijkl mnop", smtp=fake_smtp(log))
    send_email(mail, _digest(), "eu@gmail.com")
    assert log[0] == ("connect", "smtp.gmail.com", 587, False) and ("starttls", True) in log
    assert ("login", "eu@gmail.com", "abcdefghijklmnop") in log and log[-1] == "quit"
    msg = next(entry[1] for entry in log if isinstance(entry, tuple) and entry[0] == "send")
    assert (msg["From"], msg["To"]) == ("eu@gmail.com", "eu@gmail.com") and msg["Subject"].startswith("🗞️ SOTA What · 08/11")
    assert [part.get_content_type() for part in msg.iter_parts()] == ["text/plain", "text/html"]
    assert msg["Message-ID"].endswith("@gmail.com>")              # no local host name in the headers


def test_port_465_uses_implicit_tls_and_keeps_other_providers_passwords():
    log = []
    EmailNotifier("smtp.example.org", 465, "me@example.org", "pass word", smtp_ssl=fake_smtp(log)).check_login()
    assert log[0] == ("connect", "smtp.example.org", 465, True) and "ehlo" not in log
    assert ("login", "me@example.org", "pass word") in log and log[-1] == "quit"


def test_gmail_account_password_is_never_sent_and_errors_hide_the_secret():
    log = []
    with pytest.raises(EmailError, match="senha de app"):
        EmailNotifier("smtp.gmail.com", 587, "eu@gmail.com", "Senha123!", smtp=fake_smtp(log)).check_login()
    assert log == []                                              # refused before connecting
    with pytest.raises(EmailError) as err:
        EmailNotifier("smtp.gmail.com", 587, "eu@gmail.com", "abcdefghijklmnop",
                      smtp=fake_smtp(log, fail_login=True)).check_login()
    assert "534" in str(err.value) and "senha de app" in str(err.value) and "abcdefghijklmnop" not in str(err.value)
    assert log[-1] == "close"
    assert looks_like_app_password("abcd efgh ijkl mnop") and not looks_like_app_password("Senha123!")


def test_settings_reuse_the_gmail_pair_for_smtp():
    s = Settings(_env_file=None, gmail_address="eu@gmail.com", gmail_app_password="abcd efgh ijkl mnop",
                 digest_email_to="eu@gmail.com")
    assert (s.smtp_host, s.smtp_port, s.smtp_login, s.smtp_secret) == (
        "smtp.gmail.com", 587, "eu@gmail.com", "abcd efgh ijkl mnop")
    assert s.email_enabled
    assert not Settings(_env_file=None, gmail_address="eu@gmail.com", gmail_app_password="x").email_enabled
    other = Settings(_env_file=None, digest_email_to="a@b.org", smtp_host="smtp.b.org", smtp_user="me@b.org",
                     smtp_password="p", gmail_address="eu@gmail.com")
    assert (other.smtp_login, other.smtp_secret) == ("me@b.org", "p")
