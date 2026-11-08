# sotawhat/pipeline/accounts.py
"""`sotawhat instagram import following.json` (P5, SDD §7.2): the list of Instagram accounts to scan.

1. Reads the Accounts Center export ("Seguidores e seguindo", JSON format).
2. Fetches the profile of every account not yet in the YAML (name, bio, privacy) through Apify
   (`resultsType: details`, US$ 0,0027 each). Without `--yes` it only prints the plan and the cost.
3. Classifies them in batches of 20 (IA/ML, saúde/medtech or fora do escopo) with a cheap model.
4. Writes config/instagram_accounts.yaml: public in-scope accounts enabled (up to `--max`), the others
   disabled; an account already in the file keeps your choice. You review the file; nothing else changes."""
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import AccountBatch
from sotawhat.sources.instagram import ACTOR, USERNAME, load_accounts

PRICE = 0.0027          # US$ per Apify result (Free plan, measured 2026-11-08)
HEADER = """# config/instagram_accounts.yaml - contas do Instagram varridas no run diário (P5, SDD §7.2).
# Gerado por `sotawhat instagram import following.json`; revise à vontade:
#   enabled: true  -> entra na varredura diária (Apify, só contas públicas)
#   category: ia | saude | fora  (ia vai para o perfil geral, saude para o médico)
# Reimportar mantém o que você decidiu aqui e só classifica as contas novas.
"""


def parse_following(path) -> list:
    """Usernames, in the export's order, from following.json (old and new Accounts Center layouts)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = data.get("relationships_following", []) if isinstance(data, dict) else data
    names = []
    for entry in entries if isinstance(entries, list) else []:
        candidates = [s.get("value") or "" for s in entry.get("string_list_data") or []]
        candidates += [urlsplit(s.get("href") or "").path.strip("/").split("/")[-1] for s in entry.get("string_list_data") or []]
        candidates.append(entry.get("title") or "")
        name = next((c for c in candidates if c and USERNAME.match(c)), None)
        if name and name not in names:
            names.append(name)
    return names


def fetch_profiles(apify, names, max_usd) -> dict:
    """username -> {"full_name", "bio", "private", "followers", "category_name"}."""
    raw = apify.run(ACTOR, {"directUrls": [f"https://www.instagram.com/{n}/" for n in names], "resultsType": "details"},
                    max_usd=max_usd, max_items=len(names))
    out = {}
    for p in raw:
        name = p.get("username")
        if name:
            out[name] = {"full_name": p.get("fullName") or "", "bio": (p.get("biography") or "")[:400],
                         "private": bool(p.get("private")), "followers": p.get("followersCount"),
                         "category_name": p.get("businessCategoryName") or ""}
    return out


def classify(gateway, profiles, batch=20, notes=None) -> dict:
    """username -> (category, reason). An account the model skips stays "fora" with no reason."""
    system, out, names = load_prompt("accounts_v1"), {}, list(profiles)
    for start in range(0, len(names), batch):
        chunk = names[start:start + batch]
        user = "\n".join(f"- @{n} | {profiles[n]['full_name']} | {profiles[n]['category_name']} | {profiles[n]['bio']}"
                         for n in chunk)
        try:
            res = gateway.structured_call("accounts", [{"role": "system", "content": system},
                                                       {"role": "user", "content": user}], AccountBatch)
        except (BudgetExceeded, InsufficientCredits) as exc:
            if notes is not None:
                notes.append(f"classificação interrompida: {exc}")
            break
        except LLMFailure as exc:
            if notes is not None:
                notes.append(f"lote {start // batch + 1}: {exc}")
            continue
        for verdict in res.output.contas:
            name = verdict.usuario.lstrip("@")
            if name in chunk:
                out[name] = (verdict.categoria, verdict.motivo)
    return out


def build_accounts(existing, names, profiles, verdicts, max_enabled) -> list:
    """Existing entries first (your choices stay), then the new ones; in-scope public accounts are
    enabled until `max_enabled` accounts are on."""
    known = {a["username"]: a for a in existing}
    accounts = list(existing)
    enabled = sum(1 for a in existing if a.get("enabled"))
    for name in names:
        if name in known:
            continue
        profile = profiles.get(name, {})
        category, reason = verdicts.get(name, ("fora", "sem perfil ou sem classificação"))
        on = category in ("ia", "saude") and not profile.get("private") and enabled < max_enabled
        enabled += on
        entry = {"username": name, "category": category, "enabled": on,
                 "name": profile.get("full_name", ""), "reason": reason}
        if profile.get("private"):
            entry["note"] = "privada: só pela captura manual"
        accounts.append(entry)
    return accounts


def write_accounts(path, accounts) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump({"updated": date.today().isoformat(), "accounts": accounts}, sort_keys=False,
                          allow_unicode=True, width=120)
    path.write_text(HEADER + body, encoding="utf-8")


def run_import(settings, following, apify, gateway, notifier=None, max_enabled=50, limit=None, yes=False, out=print) -> int:
    """The whole `sotawhat instagram import`, with its dependencies given (the tests never read the real .env)."""
    path = Path(settings.sotawhat_config_dir) / "instagram_accounts.yaml"
    names = parse_following(following)
    existing = load_accounts(path)
    known = {a["username"] for a in existing}
    new = [n for n in names if n not in known][:limit or None]
    cost = len(new) * PRICE
    out(f"{len(names)} contas seguidas · {len(new)} novas para classificar · busca dos perfis no Apify ≈ US$ {cost:.2f} "
        "(plano Free: US$ 5/mês)")
    if not new:
        out(f"nada novo: {path} já tem todas as contas")
        return 0
    if not yes:
        out("nada foi feito: rode de novo com --yes para buscar os perfis e classificar")
        return 0
    if not apify.configured:
        out("[apify] APIFY_TOKEN vazio no .env")
        return 2
    profiles = fetch_profiles(apify, new, max_usd=round(cost * 1.2 + 0.05, 2))
    notes = []
    verdicts = classify(gateway, profiles, notes=notes) if gateway is not None else {}
    accounts = build_accounts(existing, new, profiles, verdicts, max_enabled)
    write_accounts(path, accounts)
    fresh = [a for a in accounts if a["username"] in set(new)]
    counts = {c: sum(1 for a in fresh if a["category"] == c) for c in ("ia", "saude", "fora")}
    enabled = sum(1 for a in accounts if a.get("enabled"))
    line = (f"{len(fresh)} contas classificadas: IA {counts['ia']}, saúde {counts['saude']}, fora {counts['fora']} · "
            f"{enabled} habilitadas na varredura diária")
    for note in notes + ([] if gateway is not None else ["sem OPENROUTER_API_KEY: tudo ficou como 'fora'"]):
        out(f"[aviso] {note}")
    out(f"{line}\n[arquivo] {path} (revise e mude `enabled` à vontade)")
    if notifier is not None and notifier.configured:
        try:
            notifier.send_message(f"📷 Instagram: {line}. Revise config/instagram_accounts.yaml.", disable_notification=True)
        except Exception:  # noqa: BLE001 - the file is what matters
            pass
    return 0


def main_instagram(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.configfiles import ConfigError, load_config
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient
    from sotawhat.notify.telegram import TelegramNotifier
    from sotawhat.pipeline.daily import setup_logging
    from sotawhat.sources.apify import ApifyClient, ApifyError
    from sotawhat.store.db import Store

    settings = load_settings()
    setup_logging(settings.sotawhat_data_dir, date.today().isoformat(), settings.sotawhat_log_level)
    try:
        config = load_config(settings.sotawhat_config_dir)
    except ConfigError as exc:
        print(f"[config] {exc}", file=sys.stderr)
        return 2
    with Store(settings.db_path) as store:
        gateway = None
        if settings.openrouter_api_key:
            gateway = LLMGateway(OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                                                  app_title=settings.openrouter_app_title),
                                 store=store, settings=settings, tasks=config.llm["tasks"])
        try:
            return run_import(settings, ns.file, ApifyClient(settings.apify_token), gateway,
                              TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id),
                              max_enabled=ns.max, limit=ns.limit, yes=ns.yes)
        except (ApifyError, ConfigError, OSError, ValueError) as exc:
            print(f"[instagram] {exc}", file=sys.stderr)
            return 1
