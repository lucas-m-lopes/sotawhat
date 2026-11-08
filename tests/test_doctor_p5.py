# tests/test_doctor_p5.py
"""doctor (P5): the Apify plan and the Instagram accounts with the last scan."""
import json
from types import SimpleNamespace

from sotawhat.doctor import TASKS, check_instagram
from sotawhat.sources.apify import ApifyError


class Apify:
    def __init__(self, configured=True, used=0.4, fail=False):
        self.configured, self.used, self.fail = configured, used, fail

    def usage(self):
        if self.fail:
            raise ApifyError("Apify: token recusado (401); confira APIFY_TOKEN")
        return {"used": self.used, "limit": 5, "cycle_end": "2026-12-07"}


def _settings(tmp_path):
    return SimpleNamespace(apify_token="t", sotawhat_config_dir=tmp_path, sotawhat_data_dir=tmp_path)


def test_check_instagram(tmp_path):
    settings = _settings(tmp_path)
    apify, accounts = check_instagram(settings, Apify())
    assert (apify.status, accounts.status) == ("ok", "warn") and "instagram import" in accounts.detail
    assert "US$ 0.40 de US$ 5.00" in apify.detail
    assert check_instagram(settings, Apify(used=4.5))[0].status == "warn"
    assert check_instagram(settings, Apify(fail=True))[0].status == "fail"
    assert check_instagram(settings, Apify(configured=False))[0].status == "warn"
    (tmp_path / "instagram_accounts.yaml").write_text(
        "accounts:\n- {username: a, category: ia, enabled: true}\n- {username: b, category: saude, enabled: true}\n"
        "- {username: c, category: fora, enabled: false}\n", encoding="utf-8")
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "instagram.json").write_text(json.dumps({"since_ia": "2026-11-08T07:01:00+00:00",
                                                                   "since_saude": "2026-11-08T07:02:00+00:00"}))
    ok = check_instagram(settings, Apify())[1]
    assert ok.status == "ok" and ok.detail == "2 de 3 na varredura (IA 1, saúde 1) · última varredura 2026-11-08 07:02"
    (tmp_path / "instagram_accounts.yaml").write_text("accounts:\n- {username: 'x y', category: ia}\n", encoding="utf-8")
    assert check_instagram(settings, Apify())[1].status == "fail"
    assert "accounts" in TASKS and "vision" in TASKS
