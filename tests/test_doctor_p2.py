# tests/test_doctor_p2.py
"""`sotawhat doctor` checks added in P2: GitHub and Hugging Face tokens, the Gmail newsletter query."""
import imaplib

import httpx

from sotawhat.config import Settings
from sotawhat.doctor import check_github, check_gmail, check_hf


def _get(status, payload):
    def get(url, headers=None, timeout=None):
        get.calls.append((url, headers))
        return httpx.Response(status, json=payload, request=httpx.Request("GET", url))
    get.calls = []
    return get


def test_check_github():
    assert check_github(Settings(_env_file=None)).status == "warn"
    get = _get(200, {"resources": {"core": {"limit": 5000, "remaining": 4990}, "search": {"limit": 30, "remaining": 30}}})
    ok = check_github(Settings(_env_file=None, github_token="ghp_x"), get=get)
    assert ok.status == "ok" and "busca 30/30 por minuto" in ok.detail and get.calls[0][1]["Authorization"] == "Bearer ghp_x"
    bad = check_github(Settings(_env_file=None, github_token="ghp_x"), get=_get(401, {"message": "Bad credentials"}))
    assert bad.status == "fail" and "ghp_x" not in bad.detail


def test_check_hf():
    assert check_hf(Settings(_env_file=None)).status == "warn"
    assert check_hf(Settings(_env_file=None, hf_token="hf_x"), get=_get(200, {"name": "lucas"})).detail.startswith("conta lucas")
    assert check_hf(Settings(_env_file=None, hf_token="hf_x"), get=_get(401, {"error": "Invalid"})).status == "fail"


class FakeIMAP:
    def __init__(self, count=0, fail=False):
        self.count, self.fail, self.queries = count, fail, []

    def login(self, user, password):
        if self.fail:
            raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials (Failure)")

    def list(self):
        return "OK", [b'(\\All \\HasNoChildren) "/" "[Gmail]/All Mail"']

    def select(self, mailbox, readonly=False):
        return "OK", [b"1"]

    def uid(self, command, *args):
        self.queries.append(args[-1])
        return "OK", [b" ".join(str(n).encode() for n in range(1, self.count + 1))]

    def logout(self):
        pass


def test_check_gmail():
    assert check_gmail(Settings(_env_file=None)).status == "warn"
    settings = Settings(_env_file=None, gmail_address="eu@gmail.com", gmail_app_password="abcdefghijklmnop",
                        gmail_query="label:newsletters-ai newer_than:2d")
    imap = FakeIMAP(count=12)
    ok = check_gmail(settings, imap_factory=lambda: imap)
    assert ok.status == "ok" and "12 mensagens em 30 dias" in ok.detail and imap.queries == ['"label:newsletters-ai newer_than:30d"']
    empty = check_gmail(settings, imap_factory=lambda: FakeIMAP(count=0))
    assert empty.status == "warn" and "filtro" in empty.detail
    failed = check_gmail(settings, imap_factory=lambda: FakeIMAP(fail=True))
    assert failed.status == "fail" and "senha de app" in failed.detail and "abcdefghijklmnop" not in failed.detail
