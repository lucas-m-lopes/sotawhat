# sotawhat/doctor.py
"""`sotawhat doctor [--llm]`: configuration, keys, models, last run and spend (SDD §6.12)."""
import imaplib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel

from sotawhat.llm.tasks import resolve

TASKS = ("triage", "segment", "vision", "extract", "synth", "resolve", "ideate", "critique", "judge")
_BAD_QUANT = {"fp4", "mxfp4", "nvfp4", "int4", "fp6"}


@dataclass
class Check:
    name: str
    status: str   # "ok" | "warn" | "fail"
    detail: str


class Smoke(BaseModel):
    ok: bool
    idioma: str


def model_requirements(settings=None, llm_config=None) -> dict:
    """model -> set of reasoning efforts it must accept, over every task chain and bake-off candidate."""
    overrides = (llm_config or {}).get("tasks")
    chains = [(task, resolve(task, settings, overrides).models) for task in TASKS]
    chains += [(task, tuple(models)) for task, models in ((llm_config or {}).get("bakeoff") or {}).items()]
    needs = {}
    for task, models in chains:
        reasoning = resolve(task, settings, overrides).reasoning
        for model in models:
            needs.setdefault(model, set())
            if reasoning:
                needs[model].add(reasoning)
    return needs


def check_config(config_dir):
    from sotawhat.configfiles import ConfigError, load_config

    try:
        config = load_config(config_dir)
    except ConfigError as exc:
        return Check("config/*.yaml", "fail", str(exc)), None
    present = [n for n in ("rubric.yaml", "mute.yaml", "llm.yaml") if (Path(config_dir) / n).exists()]
    status = "ok" if len(present) == 3 else "warn"
    return Check("config/*.yaml", status, f"{', '.join(present) or 'nenhum arquivo'} (padrões do código no resto)"), config


def check_embeddings(settings) -> Check:
    if settings.embeddings_backend == "hash":
        return Check("embeddings", "warn", "backend hash (só para testes): novidade e classificador fracos")
    cache = settings.models_dir / "fastembed"
    try:
        from fastembed import TextEmbedding

        hf = next(m["sources"]["hf"] for m in TextEmbedding.list_supported_models()
                  if m["model"] == settings.embeddings_model)
    except StopIteration:
        return Check("embeddings", "fail", f"{settings.embeddings_model} não é suportado pelo fastembed")
    except Exception as exc:  # noqa: BLE001
        return Check("embeddings", "fail", f"fastembed indisponível: {exc}")
    if (cache / f"models--{hf.replace('/', '--')}").exists():
        return Check("embeddings", "ok", f"{settings.embeddings_model} em cache")
    return Check("embeddings", "warn", f"{settings.embeddings_model} ainda não baixado: o próximo run baixa ~1,2 GB "
                                       f"para {cache}")


def check_classifiers(store, embed_model, min_ratings, profiles) -> list:
    from sotawhat.store.classifier import NEGATIVE, POSITIVE

    checks = []
    for profile in profiles:
        votes = sum(1 for v in store.item_votes(profile=profile).values() if v in POSITIVE | NEGATIVE)
        row = store.latest_classifier(profile, embed_model)
        if row is None:
            checks.append(Check(f"classificador {profile}", "ok",
                                f"{votes}/{min_ratings} votos; até lá o LLM vê todos os itens"))
            continue
        m = json.loads(row["metrics_json"] or "{}")
        checks.append(Check(f"classificador {profile}", "ok",
                            f"{row['version']}: {m.get('n')} votos · F1 {m.get('f1', '?')} · AUC {m.get('auc', '?')}"))
    return checks


def check_feedback(store, now=None) -> Check:
    from sotawhat.pipeline.feedback import LAST_PULL_KEY, listener_active

    now = now or datetime.now(timezone.utc)
    if listener_active(store, now):
        return Check("votos do Telegram", "ok", "`feedback listen` ativo")
    last = store.meta_get(LAST_PULL_KEY)
    if not last:
        return Check("votos do Telegram", "warn", "nenhuma coleta de votos ainda")
    age = (now - datetime.fromisoformat(last)).total_seconds() / 3600
    if age > 20:
        return Check("votos do Telegram", "warn", f"última coleta há {age:.0f} h; o Telegram descarta votos após "
                                                  "24 h (rode o run diário ou `sotawhat feedback listen`)")
    return Check("votos do Telegram", "ok", f"última coleta há {age:.0f} h")


def check_golden(path) -> Check:
    from sotawhat.evals.golden import load_golden

    labeled = len(load_golden(path))
    if labeled >= 50:
        return Check("golden set", "ok", f"{labeled} itens rotulados")
    if labeled:
        return Check("golden set", "warn", f"{labeled} itens rotulados (meta ≥ 50 para o bake-off)")
    return Check("golden set", "warn", "nenhum item rotulado: `sotawhat eval golden draft`")


def check_settings(settings) -> list:
    checks = [Check("OPENROUTER_API_KEY", "ok" if settings.openrouter_api_key else "fail",
                    "definida" if settings.openrouter_api_key else "ausente no .env")]
    private = settings.openrouter_zdr and settings.openrouter_data_collection == "deny"
    checks.append(Check("privacidade LLM", "ok" if private else "warn",
                        f"zdr={settings.openrouter_zdr} data_collection={settings.openrouter_data_collection}"))
    if not (settings.telegram_bot_token and settings.telegram_chat_id):
        checks.append(Check("Telegram", "warn", "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes"))
    elif not re.fullmatch(r"-?\d+", settings.telegram_chat_id.strip()):
        checks.append(Check("Telegram", "fail", "TELEGRAM_CHAT_ID precisa ser o número do chat, não um nome: "
                                                "mande /start ao bot e veja o número sugerido abaixo"))
    else:
        checks.append(Check("Telegram", "ok", "configurado"))
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
    detail = f"limite US$ {limit:.2f} · restante {rest} · uso no mês US$ {usage:.2f}"
    if "limit_reset" in info and not info["limit_reset"]:
        # without a reset the limit is a total for the life of the key: the runs stop once it is spent
        return Check("chave OpenRouter", "warn", f"{detail} · o limite NÃO renova (defina renovação mensal na chave)")
    return Check("chave OpenRouter", "warn" if low else "ok", detail + f" · renova: {info.get('limit_reset') or '?'}")


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


def _private_chats(notifier) -> list:
    """Private chats that wrote to the bot in the last 24 h, as 'id (name)'. No offset: nothing is consumed."""
    try:
        updates = notifier.get_updates(timeout=0)
    except Exception:  # noqa: BLE001 - e.g. the vote listener holds getUpdates (409)
        return []
    found = {}
    for update in updates:
        chat = (update.get("message") or {}).get("chat") or {}
        if chat.get("type") == "private":
            found[chat["id"]] = f"{chat['id']} ({chat.get('first_name', '?')})"
    return list(found.values())


def check_telegram(notifier) -> Check:
    try:
        me = notifier.get_me()
    except Exception as exc:  # noqa: BLE001
        return Check("bot do Telegram", "fail", str(exc))
    bot = f"@{me.get('username', '?')}"
    try:
        chat = notifier.get_chat()
    except Exception as exc:  # noqa: BLE001
        found = _private_chats(notifier)
        hint = (f"use TELEGRAM_CHAT_ID={found[0]}" if found else
                "abra o bot no Telegram, toque em Iniciar e rode `sotawhat doctor` de novo")
        return Check("bot do Telegram", "fail", f"{bot}: o chat {notifier.chat_id} não responde ({exc}); {hint}")
    name = f" ({chat['first_name']})" if chat.get("first_name") else ""
    return Check("bot do Telegram", "ok", f"{bot} → chat {chat.get('type', '?')}{name}")


def check_model_pins(settings, llm_config) -> Check:
    """SOTAWHAT_MODEL_<TASK> in .env beats config/llm.yaml (and so the bake-off winner) for the primary model."""
    tasks = (llm_config or {}).get("tasks") or {}
    hidden = []
    for task in TASKS:
        pin, chosen = settings.model_override(task), ((tasks.get(task) or {}).get("models") or [None])[0]
        if pin and chosen and pin != chosen:
            hidden.append(f"SOTAWHAT_MODEL_{task.upper()}={pin} passa por cima de config/llm.yaml ({chosen})")
    if hidden:
        return Check("modelos fixados no .env", "warn", "; ".join(hidden) + ": apague a linha no .env para usar o llm.yaml")
    return Check("modelos fixados no .env", "ok", "nenhum conflito com config/llm.yaml")


def check_email(settings, factory=None) -> Check:
    """Optional e-mail copy: off without DIGEST_EMAIL_TO; otherwise a real SMTP login that sends nothing."""
    from sotawhat.notify.email import EmailError, EmailNotifier
    name = "e-mail do digest"
    if not settings.digest_email_to:
        return Check(name, "ok", "desligado (DIGEST_EMAIL_TO vazio)")
    if not (settings.smtp_login and settings.smtp_secret):
        return Check(name, "fail", "DIGEST_EMAIL_TO definido, mas faltam GMAIL_ADDRESS e GMAIL_APP_PASSWORD "
                                   "(ou SMTP_USER e SMTP_PASSWORD)")
    mailer = (factory or EmailNotifier)(settings.smtp_host, settings.smtp_port, settings.smtp_login,
                                        settings.smtp_secret)
    try:
        mailer.check_login()
    except EmailError as exc:
        return Check(name, "fail", str(exc))
    return Check(name, "ok", f"login SMTP ok em {settings.smtp_host}:{settings.smtp_port} → {settings.digest_email_to}")


def check_github(settings, get=None) -> Check:
    """GITHUB_TOKEN (P2): search runs with 10 requests/min without it, 30 with it."""
    if not settings.github_token:
        return Check("GitHub", "warn", "GITHUB_TOKEN vazio: a busca de repositórios roda com o limite anônimo (10/min)")
    get = get or httpx.get
    try:
        r = get("https://api.github.com/rate_limit", headers={"Authorization": f"Bearer {settings.github_token}",
                                                              "User-Agent": "sotawhat/3.0"}, timeout=20)
    except httpx.HTTPError as exc:
        return Check("GitHub", "warn", f"não respondeu: {type(exc).__name__}")
    if r.status_code == 401:
        return Check("GitHub", "fail", "GITHUB_TOKEN recusado (inválido ou expirado): gere outro fine-grained token")
    res = r.json().get("resources", {})
    search, core = res.get("search", {}), res.get("core", {})
    return Check("GitHub", "ok", f"busca {search.get('remaining')}/{search.get('limit')} por minuto · "
                                 f"API {core.get('remaining')}/{core.get('limit')} por hora")


def check_hf(settings, get=None) -> Check:
    if not settings.hf_token:
        return Check("Hugging Face", "warn", "HF_TOKEN vazio: a Hub API roda com o limite anônimo")
    get = get or httpx.get
    try:
        r = get("https://huggingface.co/api/whoami-v2", headers={"Authorization": f"Bearer {settings.hf_token}"},
                timeout=20)
    except httpx.HTTPError as exc:
        return Check("Hugging Face", "warn", f"não respondeu: {type(exc).__name__}")
    if r.status_code == 401:
        return Check("Hugging Face", "fail", "HF_TOKEN recusado: gere outro token de leitura")
    return Check("Hugging Face", "ok", f"conta {r.json().get('name', '?')}")


def check_gmail(settings, imap_factory=None) -> Check:
    """The newsletter query (P2) over 30 days: zero usually means the Gmail filter/label is missing."""
    name = "newsletters do Gmail"
    if not (settings.gmail_address and settings.gmail_app_password):
        return Check(name, "warn", "desligado (GMAIL_ADDRESS/GMAIL_APP_PASSWORD vazios)")
    from sotawhat.sources.gmail import _gmail_imap

    query = re.sub(r"newer_than:\d+[dmy]", "newer_than:30d", settings.gmail_query)
    if "newer_than:" not in query:
        query += " newer_than:30d"
    imap = (imap_factory or _gmail_imap)()
    try:
        imap.login(settings.gmail_address, "".join(settings.gmail_app_password.split()))
        _, boxes = imap.list()
        box = next((b.decode("utf-8", "replace").split(' "/" ')[-1] for b in boxes if b"\\All" in b), "INBOX")
        imap.select(box, readonly=True)
        _, data = imap.uid("SEARCH", "X-GM-RAW", f'"{query}"')
        count = len((data[0] or b"").split()) if data else 0
    except imaplib.IMAP4.error as exc:
        detail = str(exc).replace(settings.gmail_app_password, "***")
        return Check(name, "fail", f"login IMAP recusado ({detail}); confira a senha de app em GMAIL_APP_PASSWORD")
    except OSError as exc:
        return Check(name, "warn", f"IMAP não respondeu: {type(exc).__name__}")
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001
            pass
    if not count:
        return Check(name, "warn", f"`{settings.gmail_query}` não achou nada em 30 dias: crie no Gmail um filtro que "
                                   "aplique a label newsletters/ai às newsletters sem RSS (ou ajuste GMAIL_QUERY)")
    return Check(name, "ok", f"{count} mensagens em 30 dias para `{settings.gmail_query}`")


def check_neo4j(settings, store, factory=None) -> Check:
    """The Neo4j mirror (P3, D16): optional, so being off is a warning; configured but silent is a failure."""
    name = "espelho Neo4j"
    if not settings.neo4j_password:
        return Check(name, "warn", "desligado (NEO4J_PASSWORD vazio); a interface funciona sem ele")
    if factory is None:
        from sotawhat.graph.neo4j_sync import Neo4jMirror
        factory = Neo4jMirror.from_settings
    mirror = factory(settings)
    try:
        if not mirror.ping():
            return Check(name, "fail", f"não responde em {settings.neo4j_uri}: rode `sotawhat graph up`")
        counts = mirror.counts()
    finally:
        mirror.close()
    synced = store.meta_get("graph_synced_at")
    age = ""
    if synced:
        hours = (datetime.now(timezone.utc) - datetime.fromisoformat(synced)).total_seconds() / 3600
        age = f" · última sincronização há {hours:.0f} h"
    return Check(name, "ok", f"{counts['nodes']} nós · {counts['relationships']} relações{age}")


def check_graph(store, max_backlog=50) -> Check:
    from sotawhat.graph.query import stats

    s = stats(store)
    entities = sum(n for t, n in s["entities"].items() if t not in ("domain", "problem_type", "technique_family"))
    if not entities and not s["extracted"]:
        return Check("grafo", "warn", "vazio: rode `sotawhat graph extract` para extrair os itens já aprovados")
    detail = f"{entities} entidades · {s['relations']} relações · {s['extracted']} itens extraídos"
    if s["pending_extraction"] > max_backlog:
        return Check("grafo", "warn", f"{detail} · {s['pending_extraction']} aprovados sem extração "
                                      "(rode `sotawhat graph extract`)")
    return Check("grafo", "ok", detail + (f" · {s['pending_extraction']} na fila" if s["pending_extraction"] else ""))


def check_web(port, connect=None) -> Check:
    import socket

    connect = connect or socket.create_connection
    try:
        connect(("127.0.0.1", port), timeout=0.5).close()
    except OSError:
        return Check("interface", "warn", f"fora do ar: rode `sotawhat serve` (porta {port}) ou agende com "
                                          "`scripts\\schedule_daily.ps1 -Web`")
    return Check("interface", "ok", f"no ar em http://127.0.0.1:{port}/")


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


def check_last_weekly(store, now=None, max_age_days=8) -> Check:
    now = now or datetime.now(timezone.utc)
    row = store.last_run("weekly")
    if row is None:
        return Check("último run semanal", "warn", "nenhum ainda: rode `sotawhat run weekly` ou agende com "
                                                 "`scripts\\schedule_daily.ps1 -Weekly` (domingo, 20:00)")
    if not row["ok"]:
        return Check("último run semanal", "fail", f"falhou em {row['finished_at']}: {row['error']}")
    age = (now - datetime.fromisoformat(row["finished_at"])).total_seconds() / 86400
    stats = json.loads(row["stats_json"] or "{}")
    ideation = stats.get("ideation") or {}
    detail = (f"concluído há {age:.0f} d · {len(ideation.get('finalists') or [])} ideias · US$ {row['cost_usd'] or 0:.3f}"
              + (f" · interrompido: {ideation['stopped']}" if ideation.get("stopped") else ""))
    if age > max_age_days:
        return Check("último run semanal", "warn", f"{detail}; o agendamento semanal está ativo?")
    return Check("último run semanal", "warn" if ideation.get("stopped") else "ok", detail)


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

    from sotawhat.profiles import PROFILES

    settings = load_settings()
    checks = check_settings(settings)
    config_check, config = check_config(settings.sotawhat_config_dir)
    checks.append(config_check)
    llm_config = config.llm if config else None
    checks.append(check_model_pins(settings, llm_config))
    client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url)
    if settings.openrouter_api_key:
        checks.append(check_openrouter_key(client))
    checks += check_models(client, model_requirements(settings, llm_config))
    checks.append(check_embeddings(settings))
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if notifier.configured:
        checks.append(check_telegram(notifier))
    checks.append(check_email(settings))
    checks += [check_github(settings), check_hf(settings), check_gmail(settings)]
    with Store(settings.db_path) as store:
        checks.append(check_last_run(store))
        checks.append(check_last_weekly(store))
        checks.append(check_month_cost(store, settings.sotawhat_llm_budget_usd_month))
        min_ratings = config.rubric.classifier_min_ratings if config else 100
        checks += check_classifiers(store, settings.embeddings_model, min_ratings, list(PROFILES))
        if notifier.configured:
            checks.append(check_feedback(store))
        checks.append(check_golden("tests/evals/triage/golden_v1.jsonl"))
        checks.append(check_graph(store))
        checks.append(check_neo4j(settings, store))
        if ns.llm:
            if settings.openrouter_api_key:
                overrides = llm_config["tasks"] if llm_config else None
                primaries = list(dict.fromkeys(resolve(t, settings, overrides).models[0] for t in TASKS))
                checks += llm_smoke(LLMGateway(client, store=store, settings=settings, tasks=overrides), primaries)
            else:
                checks.append(Check("fumaça LLM", "fail", "sem OPENROUTER_API_KEY"))
    checks.append(check_web(settings.sotawhat_web_port))
    print(render(checks))
    return 1 if any(c.status == "fail" for c in checks) else 0
