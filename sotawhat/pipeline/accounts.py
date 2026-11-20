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
BATCH = 40              # profiles per Apify run: 65 took 662 s on 2026-11-10, past the client's 600 s wait
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


def _profile(p) -> dict:
    return {"full_name": p.get("fullName") or "", "bio": (p.get("biography") or "")[:400],
            "private": bool(p.get("private")), "followers": p.get("followersCount"),
            "category_name": p.get("businessCategoryName") or ""}


def profiles_of(items) -> dict:
    """username -> {"full_name", "bio", "private", "followers", "category_name"} from the scraper's results."""
    return {p["username"]: _profile(p) for p in items if p.get("username")}


def fetch_profiles(apify, names, batch=BATCH, cache=None, save=None, out=print) -> dict:
    """The profiles of `names`, `batch` per Apify run (about 10 s each, so a run stays inside the client's wait).
    Names already in `cache` are not fetched again, and after each run the cache is handed to `save`, so an import
    that stops resumes where it was; a run that outlives the wait keeps what it fetched."""
    profiles, todo = dict(cache or {}), [n for n in names if n not in (cache or {})]
    for start in range(0, len(todo), batch):
        chunk = todo[start:start + batch]
        raw = apify.run(ACTOR, {"directUrls": [f"https://www.instagram.com/{n}/" for n in chunk], "resultsType": "details"},
                        max_usd=round(len(chunk) * PRICE * 1.2 + 0.05, 2), max_items=len(chunk), partial=True)
        profiles.update(profiles_of(raw))
        if save is not None:
            save(profiles)
        if len(todo) > batch:
            out(f"[apify] perfis {start + len(chunk)}/{len(todo)}")
    return {n: profiles[n] for n in names if n in profiles}


def read_cache(path) -> dict:
    if path is None or not Path(path).exists():
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_cache(path, profiles) -> None:
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(profiles, ensure_ascii=False), encoding="utf-8")


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


def run_import(settings, following, apify, gateway, notifier=None, max_enabled=50, limit=None, yes=False, out=print,
               cache_path=None, salvage=None) -> int:
    """The whole `sotawhat instagram import`, with its dependencies given (the tests never read the real .env).
    `cache_path` keeps every profile fetched, so a stopped import resumes without paying twice; `salvage` (an Apify
    run id) adds the profiles that an earlier, aborted run had already fetched."""
    path = Path(settings.sotawhat_config_dir) / "instagram_accounts.yaml"
    names = parse_following(following)
    existing = load_accounts(path)
    known = {a["username"] for a in existing}
    new = [n for n in names if n not in known][:limit or None]
    cache = read_cache(cache_path)
    if salvage:
        if not apify.configured:
            out("[apify] APIFY_TOKEN vazio no .env")
            return 2
        saved = profiles_of(apify.items(salvage))
        cache.update(saved)
        write_cache(cache_path, cache)
        out(f"[apify] {len(saved)} perfis recuperados do run {salvage}")
    todo = [n for n in new if n not in cache]
    cost = len(todo) * PRICE
    out(f"{len(names)} contas seguidas · {len(new)} novas para classificar"
        + (f" ({len(new) - len(todo)} perfis já buscados)" if len(todo) < len(new) else "")
        + f" · busca dos perfis no Apify ≈ US$ {cost:.2f} (plano Free: US$ 5/mês)")
    if not new:
        out(f"nada novo: {path} já tem todas as contas")
        return 0
    if not yes:
        out("nada foi feito: rode de novo com --yes para buscar os perfis e classificar")
        return 0
    if todo and not apify.configured:
        out("[apify] APIFY_TOKEN vazio no .env")
        return 2
    profiles = fetch_profiles(apify, new, cache=cache, save=lambda p: write_cache(cache_path, p), out=out)
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
        if ns.instagram_action == "salvos":
            try:
                return run_saved(settings, ns, store, config, ApifyClient(settings.apify_token), gateway)
            except (ApifyError, ConfigError, OSError, ValueError) as exc:
                print(f"[salvos] {exc}", file=sys.stderr)
                return 1
        if not ns.file:
            print("instagram import precisa do following.json", file=sys.stderr)
            return 2
        try:
            return run_import(settings, ns.file, ApifyClient(settings.apify_token), gateway,
                              TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id),
                              max_enabled=ns.max, limit=ns.limit, yes=ns.yes,
                              cache_path=settings.sotawhat_data_dir / "state" / "instagram_profiles.json",
                              salvage=getattr(ns, "recuperar", None))
        except (ApifyError, ConfigError, OSError, ValueError) as exc:
            print(f"[instagram] {exc}", file=sys.stderr)
            return 1


def run_saved(settings, ns, store, config, apify, gateway, out=print, triage_runner=None, describer=None) -> int:
    """`sotawhat instagram salvos [ZIP] [--yes] [--max-usd X] [--colecao NOME] [--limit N]`: the first sweep of your
    saved posts (sources/instagram_saved.py). Without --yes, the inventory only."""
    from collections import Counter

    from sotawhat.configfiles import ConfigError
    from sotawhat.sources import instagram_saved as saved
    from sotawhat.sources.apify import ApifyError

    export = Path(ns.file) if ns.file else next(iter(reversed(saved.exports_in(saved.folder(settings)))), None)
    if export is None or not export.exists():
        out(f"nenhuma exportação em {saved.folder(settings)}: na Central de Contas, peça “Baixar suas informações” só "
            "com “Itens salvos”, desde o início, em JSON, e salve o zip nessa pasta")
        return 2
    posts = saved.parse_export(export)
    if not posts:
        out(f"{export.name} não tem posts salvos: a exportação precisa de “Itens salvos”, em JSON")
        return 1
    state = saved.SavedState(saved.state_path(settings))
    try:
        accounts = load_accounts(settings.sotawhat_config_dir / "instagram_accounts.yaml")
    except ConfigError:
        accounts = []
    usage = None
    if apify.configured:
        try:
            usage = apify.usage()
        except ApifyError:
            usage = None
    out(f"[salvos] {export.name}")
    out(saved.render_inventory(saved.inventory(posts, state, store, accounts, ns.colecao), usage, ns.colecao))
    max_usd = ns.max_usd if getattr(ns, "max_usd", None) is not None else settings.instagram_saved_max_usd
    if not ns.yes:
        out(f"\nNada foi gasto. Para ler: sotawhat instagram salvos \"{export}\" --yes [--max-usd {max_usd:.2f}]")
        return 0
    if not apify.configured:
        out("APIFY_TOKEN vazio no .env: os posts são lidos pelo Apify")
        return 2
    if gateway is None:
        out("OPENROUTER_API_KEY vazia no .env: o filtro e a triagem usam LLM")
        return 2
    run_id = store.start_run("salvos")
    gateway.run_id = run_id
    notes = []
    if describer is None:
        from sotawhat.pipeline.media import Transcriber, make_describer, whisper_available

        describer = make_describer(gateway, transcriber=Transcriber(settings.models_dir) if whisper_available() else None)
    if triage_runner is None:
        from sotawhat.store.vectors import get_embedder
        from sotawhat.pipeline.triage import run_triage

        embedder = get_embedder(settings)

        def triage_runner(rid):
            totals = Counter()
            for _ in range(10):            # 300 items a pass; what errs is retried, three times at most
                stats = run_triage(store, rid, gateway, config.rubric, config.mutes, embedder, gates=None,
                                   prompt_version=config.digest.triage_prompt, sources=(saved.BACKLOG,))
                for key in ("triaged", "main", "frontier", "radar", "rejected", "muted", "duplicates", "errors"):
                    totals[key] += getattr(stats, key)
                if stats.stopped:
                    notes.append(f"triagem interrompida: {stats.stopped}")
                    break
                if stats.candidates == 0 or (stats.triaged == 0 and not stats.errors):
                    break
            return dict(totals)

    report = saved.sweep(store, posts, state, apify, saved.make_classifier(gateway, notes), describer, triage_runner,
                         run_id, max_usd=max_usd, limit=ns.limit, collection=ns.colecao, out=out)
    state.exports.setdefault(saved.fingerprint(export), {"file": export.name, "at": saved.utcnow(), "posts": len(posts),
                                                         "sweep": True})
    state.save()
    stats = {k: (dict(v) if isinstance(v, Counter) else v) for k, v in report.items()}
    store.finish_run(run_id, not str(report["stopped"] or "").startswith("Apify"), stats, error=report["stopped"])
    out(f"[salvos] lidos {report['read']} · fora do tema {report['fora']} · importados {report['imported']} · "
        f"indisponíveis {report['missing']} · Apify US$ {saved.money(report['usd'])}")
    t = report["triage"]
    if t:
        out(f"[triagem] IA ∩ saúde {t.get('main', 0)} · fronteira {t.get('frontier', 0)} · radar {t.get('radar', 0)} · "
            f"rejeitados {t.get('rejected', 0)} · duplicados {t.get('duplicates', 0)} · erros {t.get('errors', 0)}")
    for note in notes:
        out(f"[aviso] {note}")
    if report["stopped"]:
        out(f"[parou] {report['stopped']}. Rode de novo para continuar: o que já foi lido não é pago outra vez.")
    out("Os aprovados entram no grafo no próximo run diário (extração de entidades) e nas perguntas quando o índice "
        "for refeito; o acervo não vai para o digest.")
    return 0
