# sotawhat/doctor.py
"""`sotawhat doctor [--llm]`: configuration, keys, models, last run and spend (SDD §6.12)."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel

from sotawhat.llm.tasks import resolve

TASKS = ("triage", "segment", "vision", "extract", "synth")
_BAD_QUANT = {"fp4", "mxfp4", "nvfp4", "int4", "fp6"}


@dataclass
class Check:
    name: str
    status: str   # "ok" | "warn" | "fail"
    detail: str


class Smoke(BaseModel):
    ok: bool
    idioma: str


def model_requirements(settings=None) -> dict:
    """model -> set of reasoning efforts it must accept, over every task chain."""
    needs = {}
    for task in TASKS:
        spec = resolve(task, settings)
        for model in spec.models:
            needs.setdefault(model, set())
            if spec.reasoning:
                needs[model].add(spec.reasoning)
    return needs


def check_settings(settings) -> list:
    checks = [Check("OPENROUTER_API_KEY", "ok" if settings.openrouter_api_key else "fail",
                    "definida" if settings.openrouter_api_key else "ausente no .env")]
    private = settings.openrouter_zdr and settings.openrouter_data_collection == "deny"
    checks.append(Check("privacidade LLM", "ok" if private else "warn",
                        f"zdr={settings.openrouter_zdr} data_collection={settings.openrouter_data_collection}"))
    telegram = bool(settings.telegram_bot_token and settings.telegram_chat_id)
    checks.append(Check("Telegram", "ok" if telegram else "warn",
                        "configurado" if telegram else "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes"))
    return checks


def check_openrouter_key(client) -> Check:
    try:
        info = client.key_info() or {}
    except Exception as exc:  # noqa: BLE001
        return Check("chave OpenRouter", "fail", str(exc))
    usage = info.get("usage_monthly", info.get("usage")) or 0.0
    limit = info.get("limit")
    if limit is None:
        return Check("chave OpenRouter", "warn",
                     f"válida, SEM limite de gasto (uso no mês US$ {usage:.2f}); defina um limite mensal na chave")
    remaining = info.get("limit_remaining")
    low = remaining is not None and remaining < 0.2 * limit
    rest = f"US$ {remaining:.2f}" if remaining is not None else "?"
    return Check("chave OpenRouter", "warn" if low else "ok",
                 f"limite US$ {limit:.2f} · restante {rest} · uso no mês US$ {usage:.2f}")


def check_models(client, requirements, today=None) -> list:
    today = today or date.today()
    try:
        catalog = {m["id"]: m for m in client.models()}
        zdr = client.zdr_endpoints()
    except Exception as exc:  # noqa: BLE001
        return [Check("catálogo OpenRouter", "fail", str(exc))]
    eligible = {}
    for ep in zdr:
        if ep.get("quantization") in _BAD_QUANT or "structured_outputs" not in (ep.get("supported_parameters") or []):
            continue
        eligible[ep.get("model_id")] = eligible.get(ep.get("model_id"), 0) + 1
    checks = []
    for model, efforts in requirements.items():
        meta = catalog.get(model)
        if meta is None:
            checks.append(Check(model, "fail", "não existe mais no catálogo do OpenRouter"))
            continue
        reasoning = meta.get("reasoning") or {}
        supported = reasoning.get("supported_efforts")
        bad = sorted(e for e in efforts if (supported and e not in supported)
                     or (e == "none" and reasoning.get("mandatory")))
        if bad:
            checks.append(Check(model, "fail", f"não aceita raciocínio {bad} (aceita {supported})"))
            continue
        count = eligible.get(model, 0)
        if count == 0:
            checks.append(Check(model, "fail", "nenhum endpoint ZDR elegível (≥ fp8 + saída estruturada)"))
            continue
        expires = meta.get("expiration_date")
        if expires and date.fromisoformat(expires[:10]) - today <= timedelta(days=30):
            checks.append(Check(model, "warn", f"expira em {expires[:10]}; {count} endpoints ZDR elegíveis"))
            continue
        checks.append(Check(model, "ok", f"{count} endpoints ZDR elegíveis"))
    return checks


def check_telegram(notifier) -> Check:
    try:
        me = notifier.get_me()
    except Exception as exc:  # noqa: BLE001
        return Check("bot do Telegram", "fail", str(exc))
    return Check("bot do Telegram", "ok", f"@{me.get('username', '?')}")


def check_last_run(store, now=None, max_age_hours=36) -> Check:
    now = now or datetime.now(timezone.utc)
    row = store.last_run("daily")
    if row is None:
        return Check("último run diário", "warn", "nenhum run registrado ainda")
    if not row["ok"]:
        return Check("último run diário", "fail", f"falhou em {row['finished_at']}: {row['error']}")
    age = (now - datetime.fromisoformat(row["finished_at"])).total_seconds() / 3600
    if age > max_age_hours:
        return Check("último run diário", "warn", f"último sucesso há {age:.0f} h; o agendamento está ativo?")
    return Check("último run diário", "ok", f"concluído há {age:.0f} h")


def check_month_cost(store, budget_month, now=None) -> Check:
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    spent = store.llm_cost_since(start)
    status = "warn" if spent >= 0.8 * budget_month else "ok"
    return Check("custo LLM no mês", status, f"US$ {spent:.4f} de US$ {budget_month:.2f}")


def llm_smoke(gateway, models) -> list:
    prompt = [{"role": "user", "content": 'Responda apenas com o JSON {"ok": true, "idioma": "pt-BR"}.'}]
    checks = []
    for model in models:
        try:
            out = gateway.structured("smoke", prompt, Smoke, models=(model,))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check(f"fumaça {model}", "fail", f"{type(exc).__name__}: {exc}"))
            continue
        checks.append(Check(f"fumaça {model}", "ok" if out.ok else "warn", f"JSON válido · idioma={out.idioma}"))
    return checks


def render(checks) -> str:
    tag = {"ok": "OK  ", "warn": "WARN", "fail": "FAIL"}
    return "\n".join(f"[{tag[c.status]}] {c.name}: {c.detail}" for c in checks)


def main_doctor(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient
    from sotawhat.notify.telegram import TelegramNotifier
    from sotawhat.store.db import Store

    settings = load_settings()
    checks = check_settings(settings)
    client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url)
    if settings.openrouter_api_key:
        checks.append(check_openrouter_key(client))
    checks += check_models(client, model_requirements(settings))
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if notifier.configured:
        checks.append(check_telegram(notifier))
    with Store(settings.db_path) as store:
        checks.append(check_last_run(store))
        checks.append(check_month_cost(store, settings.sotawhat_llm_budget_usd_month))
        if ns.llm:
            if settings.openrouter_api_key:
                primaries = list(dict.fromkeys(resolve(t, settings).models[0] for t in TASKS))
                checks += llm_smoke(LLMGateway(client, store=store, settings=settings), primaries)
            else:
                checks.append(Check("fumaça LLM", "fail", "sem OPENROUTER_API_KEY"))
    print(render(checks))
    return 1 if any(c.status == "fail" for c in checks) else 0
