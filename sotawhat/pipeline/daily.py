# sotawhat/pipeline/daily.py
"""`sotawhat run daily`, P0 scope: collect -> normalize -> exact dedup -> SQLite -> Telegram summary.

Triage, extraction and the real digest arrive in P1 (SDD §11).
"""
import html
import re
import sys
from dataclasses import dataclass, field
from datetime import date

from sotawhat.digest import collect, filter_relevant
from sotawhat.items import to_item
from sotawhat.notify.telegram import esc, esc_attr
from sotawhat.profiles import PROFILES

ALERT_AFTER = 3   # consecutive failures before a source is flagged as an alert


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


def run_daily(store, sources_by_profile, limit=10, vault=None, today=None) -> DailyReport:
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
            if vault:
                from sotawhat.obsidian import write_notes
                write_notes(results, vault=vault, profile_name=name, tags=profile["tags"],
                            keywords=profile["keywords"], added=day)
    except Exception as exc:  # noqa: BLE001 - the run must always be closed and reported
        report.ok = False
        report.error = f"{type(exc).__name__}: {exc}"
    stats = {"collected": report.collected, "new": len(report.new_items), "failing": sorted(report.failing)}
    store.finish_run(report.run_id, ok=report.ok, stats=stats, error=report.error)
    row = store.conn.execute("SELECT cost_usd FROM runs WHERE id = ?", (report.run_id,)).fetchone()
    report.cost_usd = row[0]
    return report


def render_summary(report, max_items=10) -> str:
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


def main_daily(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.notify.telegram import TelegramError, TelegramNotifier
    from sotawhat.profiles import build_sources
    from sotawhat.store.db import Store

    settings = load_settings()
    sources = {name: build_sources(name, crossref_mailto=settings.crossref_mailto) for name in PROFILES}
    with Store(settings.db_path) as store:
        report = run_daily(store, sources, limit=ns.limit, vault=ns.vault)
    text = render_summary(report)
    print(to_plain(text))
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if not ns.no_notify and notifier.configured:
        try:
            notifier.send(text)
        except TelegramError as exc:
            print(f"[telegram] {exc}", file=sys.stderr)
    return 0 if report.ok else 1
