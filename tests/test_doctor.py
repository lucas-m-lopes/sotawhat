# tests/test_doctor.py
from datetime import date, datetime, timedelta, timezone

from sotawhat.config import Settings
from sotawhat.doctor import (Smoke, check_last_run, check_models, check_month_cost, check_openrouter_key,
                             check_settings, llm_smoke, model_requirements, render)
from sotawhat.store.db import Store

DS = "deepseek/deepseek-v4.1-flash-1017"
GLM = "z-ai/glm-5.3-flash"


class FakeClient:
    def __init__(self, key=None, catalog=(), zdr=(), credits=None):
        self._key, self._catalog, self._zdr, self._credits = key, list(catalog), list(zdr), credits

    def key_info(self):
        return self._key

    def credits(self):
        if self._credits is None:
            raise RuntimeError("403: this key may not read the credits")
        return self._credits

    def models(self):
        return self._catalog

    def zdr_endpoints(self):
        return self._zdr


def _ep(model, quant="fp8", structured=True):
    return {"model_id": model, "quantization": quant,
            "supported_parameters": ["response_format"] + (["structured_outputs"] if structured else [])}


def test_settings_checks_flag_missing_key_and_weak_privacy():
    s = Settings(_env_file=None, openrouter_zdr=False)
    by_name = {c.name: c.status for c in check_settings(s)}
    assert by_name == {"OPENROUTER_API_KEY": "fail", "privacidade LLM": "warn", "Telegram": "warn"}


def test_key_without_spend_limit_is_a_warning():
    assert check_openrouter_key(FakeClient(key={"limit": None, "usage_monthly": 2.0})).status == "warn"
    ok = check_openrouter_key(FakeClient(key={"limit": 30, "limit_remaining": 25.0, "usage_monthly": 5.0}))
    assert ok.status == "ok" and "restante US$ 25.00" in ok.detail and "saldo da conta" not in ok.detail


def test_the_account_balance_and_the_key_limit_are_reported_apart():
    # the case of 2026-11-20: US$ 6.47 on the account, US$ 0.87 left of a key limit that does not renew
    key = {"limit": 5, "limit_remaining": 0.87, "limit_reset": None, "usage_monthly": 4.13}
    both = check_openrouter_key(FakeClient(key=key, credits={"total_credits": 37, "total_usage": 30.53}))
    assert both.status == "warn"
    assert "limite da chave US$ 5.00 · restante US$ 0.87" in both.detail and "saldo da conta US$ 6.47" in both.detail
    assert "os runs param nele, mesmo com saldo na conta" in both.detail
    # the other way round: the key has room and the account is nearly empty
    roomy = {"limit": 30, "limit_remaining": 25.0, "limit_reset": "monthly", "usage_monthly": 5.0}
    empty = check_openrouter_key(FakeClient(key=roomy, credits={"total_credits": 37, "total_usage": 36.2}))
    assert empty.status == "warn" and "quem para os runs primeiro é o saldo da conta" in empty.detail
    fine = check_openrouter_key(FakeClient(key=roomy, credits={"total_credits": 60, "total_usage": 30.0}))
    assert fine.status == "ok" and "saldo da conta US$ 30.00" in fine.detail


def test_models_need_zdr_endpoints_compatible_reasoning_and_no_close_expiry():
    catalog = [{"id": DS, "reasoning": {"supported_efforts": ["max", "high", "low", "none"]}},
               {"id": GLM, "reasoning": {"mandatory": True, "supported_efforts": ["max", "high", "low"]},
                "expiration_date": "2026-11-20"},
               {"id": "x/fp4-only"}]
    zdr = [_ep(DS), _ep(DS, quant="unknown"), _ep(GLM), _ep("x/fp4-only", quant="fp4")]
    reqs = {DS: {"low", "high"}, GLM: {"low"}, "x/fp4-only": set(), "gone/model": set(),
            "x/medium": {"medium"}}
    catalog.append({"id": "x/medium", "reasoning": {"supported_efforts": ["high", "low"]}})
    zdr.append(_ep("x/medium"))
    result = {c.name: (c.status, c.detail) for c in check_models(FakeClient(catalog=catalog, zdr=zdr), reqs,
                                                                  today=date(2026, 11, 7))}
    assert result[DS] == ("ok", "2 endpoints ZDR elegíveis")
    assert result[GLM][0] == "warn" and "2026-11-20" in result[GLM][1]
    assert result["x/fp4-only"][0] == "fail"
    assert result["gone/model"][0] == "fail"
    assert result["x/medium"][0] == "fail" and "medium" in result["x/medium"][1]


def test_default_matrix_only_uses_efforts_every_model_accepts():
    reqs = model_requirements()
    assert all(efforts <= {"low", "high"} for efforts in reqs.values())


def test_last_run_and_month_cost(tmp_path):
    now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
    with Store(tmp_path / "insight.db") as st:
        assert check_last_run(st, now=now).status == "warn"
        run = st.start_run("daily")
        st.finish_run(run, ok=True, stats={})
        assert check_last_run(st, now=datetime.now(timezone.utc)).status == "ok"
        assert check_last_run(st, now=datetime.now(timezone.utc) + timedelta(hours=40)).status == "warn"
        st.record_llm_call(task="triage", requested_model=DS, status="ok", cost_usd=21.0)
        assert check_month_cost(st, 25.0, now=datetime.now(timezone.utc)).status == "warn"


def test_llm_smoke_reports_each_model():
    class FakeGateway:
        def structured(self, task, messages, model, models=None):
            if models[0] == "bad/model":
                raise RuntimeError("HTTP 400")
            return Smoke(ok=True, idioma="pt-BR")

    checks = llm_smoke(FakeGateway(), [DS, "bad/model"])
    assert [c.status for c in checks] == ["ok", "fail"]
    assert "[FAIL] fumaça bad/model" in render(checks)
