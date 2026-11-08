# sotawhat/pipeline/daily.py
"""`sotawhat run daily` (SDD §6.1): feedback -> collect -> normalize -> exact dedup -> SQLite ->
triage (stage A + LLM) -> digest files + Telegram. Extraction and the graph arrive in P3."""
import html
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import date

from sotawhat.items import to_item
from sotawhat.notify.telegram import esc, esc_attr
from sotawhat.pipeline.collect import collect, filter_relevant
from sotawhat.profiles import PROFILES

ALERT_AFTER = 3   # consecutive failures before a source is flagged as an alert
log = logging.getLogger("sotawhat.daily")


@dataclass
class DailyReport:
    run_id: int
    day: str
    collected: dict = field(default_factory=dict)   # profile -> unique items collected
    new_items: list = field(default_factory=list)   # Items never seen before
    failing: dict = field(default_factory=dict)     # source key -> (consecutive failures, last error)
    ok: bool = True
    error: str | None = None
    cost_usd: float = 0.0
    triage: object = None                           # TriageStats, when the triage stage ran


def _dedupe(items):
    by_id = {}
    for it in items:
        kept = by_id.setdefault(it.id, it)
        if kept is not it:
            kept.concepts += [c for c in it.concepts if c not in kept.concepts]
    return list(by_id.values())


def _record_health(store, sources, errors, report):
    for src in sources:
        keyed = [(src.name, errors.get(src.name))]
        feed_errors = getattr(src, "feed_errors", {})
        keyed += [(f"{src.name}/{label}", feed_errors.get(label)) for label, _ in getattr(src, "feeds", [])]
        for key, err in keyed:
            if err:
                report.failing[key] = (store.record_source_error(key, err), err)
            else:
                store.record_source_ok(key)


def run_daily(store, sources_by_profile, limit=10, today=None, triage=None) -> DailyReport:
    """triage: optional callable (store, run_id) -> TriageStats, run after collection."""
    day = (today or date.today()).isoformat()
    report = DailyReport(run_id=store.start_run("daily"), day=day)
    try:
        for name, sources in sources_by_profile.items():
            profile = PROFILES[name]
            errors = {}
            results = collect(sources, profile["keywords"], limit,
                              on_source_error=lambda src, msg: errors.setdefault(src.name, msg))
            if profile.get("require_any"):
                results = filter_relevant(results, profile["require_any"])
            items = _dedupe([to_item(r, profile=name) for r in results])
            new_ids = set(store.upsert_items(items, report.run_id))
            report.collected[name] = len(items)
            report.new_items += [it for it in items if it.id in new_ids]
            _record_health(store, sources, errors, report)
            log.info("%s: %d collected, %d new", name, len(items), len(new_ids))
        if triage is not None:
            report.triage = triage(store, report.run_id)
    except Exception as exc:  # noqa: BLE001 - the run must always be closed and reported
        log.exception("daily run failed")
        report.ok = False
        report.error = f"{type(exc).__name__}: {exc}"
    stats = {"collected": report.collected, "new": len(report.new_items), "failing": sorted(report.failing)}
    if report.triage is not None:
        stats["triage"] = report.triage.as_dict()
    store.finish_run(report.run_id, ok=report.ok, stats=stats, error=report.error)
    row = store.conn.execute("SELECT cost_usd FROM runs WHERE id = ?", (report.run_id,)).fetchone()
    report.cost_usd = row[0]
    return report


def render_summary(report, max_items=10) -> str:
    """P0 summary: still used for the console when the LLM triage is off."""
    lines = [f"{'✅' if report.ok else '❌'} <b>sotawhat · run diário {report.day}</b>",
             f"coletados {sum(report.collected.values())} · novos {len(report.new_items)} · "
             f"custo LLM US$ {report.cost_usd:.2f}"]
    for name, count in report.collected.items():
        fresh = sum(1 for it in report.new_items if it.profile == name)
        lines.append(f"• {esc(name)}: {count} coletados, {fresh} novos")
    if report.error:
        lines.append(f"❌ erro: {esc(report.error)}")
    if report.failing:
        lines += ["", "⚠️ <b>Fontes com falha</b>"]
        for key, (count, err) in sorted(report.failing.items()):
            flag = f" — <b>alerta: {count}ª falha seguida</b>" if count >= ALERT_AFTER else ""
            lines.append(f"• {esc(key)}: {esc(err[:120])}{flag}")
    if report.new_items:
        lines += ["", f"<b>Novos</b> (até {max_items})"]
        for it in report.new_items[:max_items]:
            lines.append(f'• <a href="{esc_attr(it.url)}">{esc(it.title[:140])}</a> — {esc(it.source)}')
    return "\n".join(lines)


def to_plain(text) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def setup_logging(data_dir, day, level="INFO"):
    """One log file per day under data/logs (RNF6); tokens never reach it (no request bodies are logged)."""
    folder = data_dir / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(folder / f"{day}.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger("sotawhat")
    root.handlers = [handler]
    root.setLevel(level)
    return folder / f"{day}.log"


def main_daily(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.configfiles import ConfigError, load_config
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient
    from sotawhat.notify.email import EmailError
    from sotawhat.notify.email import from_settings as mailer_from
    from sotawhat.notify.telegram import TelegramError, TelegramNotifier
    from sotawhat.pipeline import feedback
    from sotawhat.pipeline.deliver import build_digest, render_markdown, send_digest, send_email, write_files
    from sotawhat.pipeline.triage import run_triage
    from sotawhat.profiles import build_sources
    from sotawhat.store.classifier import refresh
    from sotawhat.store.db import Store
    from sotawhat.store.vectors import get_embedder

    settings = load_settings()
    day = date.today().isoformat()
    setup_logging(settings.sotawhat_data_dir, day, settings.sotawhat_log_level)
    try:
        config = load_config(settings.sotawhat_config_dir)
    except ConfigError as exc:
        print(f"[config] {exc}", file=sys.stderr)
        return 2
    sources = {name: build_sources(name, crossref_mailto=settings.crossref_mailto) for name in PROFILES}
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    use_llm = bool(settings.openrouter_api_key) and not getattr(ns, "no_llm", False)
    with Store(settings.db_path) as store:
        if notifier.configured and not feedback.listener_active(store):
            try:
                log.info("feedback %s", feedback.pull(store, notifier, settings.allowed_user_id))
            except TelegramError as exc:
                log.warning("feedback pull: %s", exc)
        embedder = get_embedder(settings)
        gateway = None
        if use_llm:
            client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                                      app_title=settings.openrouter_app_title)
            gateway = LLMGateway(client, store=store, settings=settings, tasks=config.llm["tasks"])

        def triage(st, run_id):
            if gateway is not None:
                gateway.run_id = run_id
            try:
                gates = refresh(st, list(PROFILES), embedder.name, settings.models_dir,
                                config.rubric.classifier_min_ratings)
            except Exception:  # noqa: BLE001 - without a classifier the LLM simply sees every item
                log.exception("classifier refresh")
                gates = {}
            return run_triage(st, run_id, gateway, config.rubric, config.mutes, embedder, gates)

        report = run_daily(store, sources, limit=ns.limit, triage=triage)
        digest = build_digest(store, report, config.rubric)
        md_path, _ = write_files(digest, settings.sotawhat_data_dir / "digests")
        print(render_markdown(digest) if report.triage and report.triage.llm else to_plain(render_summary(report)))
        print(f"\n[digest] {md_path}")
        if not ns.no_notify and notifier.configured and digest.worth_sending:
            try:
                send_digest(notifier, store, digest, report.run_id)
            except TelegramError as exc:
                print(f"[telegram] {exc}", file=sys.stderr)
                log.error("telegram: %s", exc)
        if not ns.no_notify and settings.email_enabled and digest.worth_sending:
            try:
                send_email(mailer_from(settings), digest, settings.digest_email_to)
                print(f"[e-mail] digest enviado para {settings.digest_email_to}")
            except EmailError as exc:
                print(f"[e-mail] {exc}", file=sys.stderr)
                log.error("e-mail: %s", exc)
    return 0 if report.ok else 1
