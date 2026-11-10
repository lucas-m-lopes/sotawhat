"""`sotawhat radar scan|report`. `scan` runs every day at the end of `run daily`: discovery and today's stars, no LLM.
`report` runs on demand; every Sunday `run weekly` does the same inside the weekly report."""
import json
import sys
import time
from datetime import date, datetime, timezone

import httpx

from sotawhat.radar.config import load_radar
from sotawhat.radar.discover import hn_repos, record, search_github
from sotawhat.radar.history import backfill
from sotawhat.radar.measure import snapshot


def _config(settings):
    return load_radar(settings.sotawhat_config_dir / "tools_radar.yaml")


def scan(store, cfg, client, token, today, now, sleep=time.sleep, history_limit=300) -> dict:
    """Discovery and today's counts; with a token, also the star history of up to `history_limit` repositories that
    have no count from a week ago (the new finds, or all of them the first time)."""
    errors = {}
    finds = search_github(client, token, cfg, today, sleep=sleep, errors=errors)
    finds += hn_repos(client, cfg, now, errors=errors)
    found = record(store, finds, today)
    counted = snapshot(store, client, token, cfg, today, errors=errors)
    history = backfill(store, client, token, today, limit=history_limit) if token else None
    if history and history["stopped"]:
        errors["histórico de estrelas"] = history["stopped"]
    store.meta_set("radar_scanned_at", now.isoformat(timespec="seconds"))
    store.meta_set("radar_errors", json.dumps(errors, ensure_ascii=False))
    return {**found, **counted, "history": history, "errors": errors}


def scan_line(out) -> str:
    history = out.get("history")
    return (f"radar: {out['found']} achados ({out['new']} novos) · {out['counted']} contados · {out['gone']} saíram"
            + (f" · histórico de {history['repos']} repositórios" if history else "")
            + (f" · {len(out['errors'])} erros" if out["errors"] else ""))


def scan_step(settings, store, client=None, today=None, now=None, sleep=time.sleep) -> str:
    """The daily step: never raises for a source (errors are kept in meta `radar_errors`)."""
    own = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=True)
    try:
        return scan_line(scan(store, _config(settings), client, settings.github_token, today or date.today(),
                              now or datetime.now(timezone.utc), sleep=sleep))
    finally:
        if own:
            client.close()


def backfill_step(settings, store, days=14, client=None, today=None) -> int:
    """`sotawhat radar backfill`: the star history of every tracked repository without a count from a week ago."""
    if not settings.github_token:
        print("[radar] GITHUB_TOKEN vazio no .env: sem token o GitHub dá 60 pedidos por hora, poucos para o histórico",
              file=sys.stderr)
        return 2
    own = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=True)
    try:
        out = backfill(store, client, settings.github_token, today or date.today(), days=days)
    finally:
        if own:
            client.close()
    print(f"[radar] histórico de {out['repos']} repositórios · {out['days']} dias de contagem · {out['gone']} sumiram"
          + (f" · parou: {out['stopped']}" if out["stopped"] else ""))
    return 0 if out["repos"] or not out["stopped"] else 1


def weekly_step(settings, store, gateway, client=None):
    """For `run_weekly(radar=...)`: (run_id, now, notes) -> the radar section of the weekly report."""
    from sotawhat.radar.report import run_radar

    def step(run_id, now, notes):
        own = client is None
        http = client or httpx.Client(timeout=30, follow_redirects=True)
        try:
            return run_radar(store, gateway, _config(settings), http, settings.github_token, now.date(), run_id, notes)
        finally:
            if own:
                http.close()
    return step


def main_radar(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.configfiles import ConfigError, load_config
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient
    from sotawhat.notify.telegram import TelegramError, TelegramNotifier
    from sotawhat.pipeline.daily import setup_logging
    from sotawhat.radar.report import section_markdown, send
    from sotawhat.store.db import Store

    settings = load_settings()
    setup_logging(settings.sotawhat_data_dir, date.today().isoformat(), settings.sotawhat_log_level)
    try:
        config = load_config(settings.sotawhat_config_dir)
        _config(settings)
    except ConfigError as exc:
        print(f"[config] {exc}", file=sys.stderr)
        return 2
    with Store(settings.db_path) as store:
        if ns.radar_action == "scan":
            print(f"[{scan_step(settings, store)}]")
            return 0
        if ns.radar_action == "backfill":
            return backfill_step(settings, store, days=ns.dias)
        gateway = None
        if settings.openrouter_api_key:
            gateway = LLMGateway(OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                                                  app_title=settings.openrouter_app_title),
                                 store=store, settings=settings, tasks=config.llm["tasks"],
                                 budget_day=settings.sotawhat_llm_budget_usd_run_weekly)
        run_id, now = store.start_run("radar"), datetime.now(timezone.utc)
        if gateway is not None:
            gateway.run_id = run_id
        notes = []
        try:
            radar = weekly_step(settings, store, gateway)(run_id, now, notes)
        except Exception as exc:  # noqa: BLE001 - the run is closed and reported
            store.finish_run(run_id, ok=False, stats={"notes": notes}, error=f"{type(exc).__name__}: {exc}")
            print(f"[radar] {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        store.finish_run(run_id, ok=True, stats={"picks": len(radar["picks"]), "judged": radar["judged"], "notes": notes})
        print("\n".join(section_markdown(radar)))
        notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
        if not ns.no_notify and notifier.configured and radar["picks"]:
            try:
                print(f"[telegram] {send(notifier, store, radar, run_id, radar['day'])} mensagens")
            except TelegramError as exc:
                print(f"[telegram] {exc}", file=sys.stderr)
    return 0
