# sotawhat/pipeline/daily.py
"""`sotawhat run daily` (SDD §6.1): feedback -> collect -> normalize -> exact dedup -> SQLite ->
triage (stage A + LLM) -> digest files + Telegram + e-mail -> graph stage (P3: extraction, entity
resolution, taxonomy categories, Neo4j mirror), in a `graph` run of its own so the digest never waits."""
import html
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime

from sotawhat.items import to_item
from sotawhat.notify import brand
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


def run_daily(store, sources_by_profile, limit=10, today=None, triage=None, on_start=None) -> DailyReport:
    """triage: optional callable (store, run_id) -> TriageStats, run after collection. on_start(run_id) runs
    before collecting (P2: LLM calls made while collecting, like newsletter segmentation, belong to this run)."""
    day = (today or date.today()).isoformat()
    report = DailyReport(run_id=store.start_run("daily"), day=day)
    if on_start is not None:
        on_start(report.run_id)
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
            again = [it.id for it in items if it.source.startswith("manual:") and it.id not in new_ids]
            if again:                         # sent to the bot but already known: it is yours now (P5)
                log.info("%s: %d sent by hand were known; %d back to the triage", name, len(again),
                         store.requeue_manual(again))
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


def daily_due(store, not_before, now=None) -> tuple[bool, str]:
    """`run daily --catch-up HH:MM`, the logon trigger of the scheduled task. A restart while logged off
    (Windows Update at 03:15 on 2026-11-11) skips the 07:00 run, and StartWhenAvailable does not cover "user
    not logged on". Due only after HH:MM (local) while no daily of today (local date) has finished ok: a failed
    run, or one killed half-way, runs again. Two instances never overlap (the task ignores a new one)."""
    now = now or datetime.now().astimezone()
    if now.time() < not_before:
        return False, f"antes das {not_before:%H:%M}: o gatilho das {not_before:%H:%M} roda o daily"
    rows = store.conn.execute("SELECT id, started_at FROM runs WHERE kind = 'daily' AND ok = 1 "
                              "ORDER BY id DESC LIMIT 20").fetchall()
    for row in rows:
        started = datetime.fromisoformat(row["started_at"]).astimezone(now.tzinfo)
        if started.date() == now.date():
            return False, f"o daily de hoje já rodou (run {row['id']}, às {started:%H:%M})"
    return True, f"o daily de hoje não rodou: rodando agora ({now:%H:%M})"


@dataclass
class GraphReport:
    run_id: int
    extraction: object = None      # ExtractionStats
    categories: int = 0            # new 'tag' mentions (triage categories)
    mirror: object = None          # SyncStats, when the Neo4j mirror synced
    mirror_note: str | None = None
    ok: bool = True
    error: str | None = None
    cost_usd: float = 0.0


def run_graph_stage(store, gateway, resolver, mirror=None, limit=None, concurrency=4, now=None) -> GraphReport:
    """Extraction (when there is a gateway), triage categories of every approved item, then the Neo4j mirror.
    A missing or failing mirror is a note; anything else unexpected closes the `graph` run as failed."""
    from sotawhat.pipeline.extract import run_extraction

    report = GraphReport(run_id=store.start_run("graph"))
    try:
        if gateway is not None:
            gateway.run_id = report.run_id
        report.extraction = run_extraction(store, report.run_id, gateway, resolver, limit=limit,
                                           concurrency=concurrency, now=now)
        for row in store.approved_items():
            report.categories += resolver.link_categories(row["item_id"], json.loads(row["tags_json"] or "{}"),
                                                          row["fetched_at"])
        if mirror is None:
            report.mirror_note = "espelho Neo4j desligado (NEO4J_PASSWORD vazio)"
        elif not mirror.ping():
            report.mirror_note = "Neo4j fora do ar; a próxima sincronização aplica o atraso"
        else:
            try:
                report.mirror = mirror.sync(store)
            except Exception as exc:  # noqa: BLE001 - SQLite already holds the graph; the mirror catches up later
                log.warning("neo4j sync: %s", exc)
                report.mirror_note = f"falha ao sincronizar o Neo4j ({type(exc).__name__}: {exc})"
    except Exception as exc:  # noqa: BLE001 - the graph run must always be closed and reported
        log.exception("graph stage failed")
        report.ok = False
        report.error = f"{type(exc).__name__}: {exc}"
    stats = {"extraction": report.extraction.as_dict() if report.extraction else None,
             "categories": report.categories, "mirror": report.mirror.as_dict() if report.mirror else None,
             "mirror_note": report.mirror_note}
    store.finish_run(report.run_id, ok=report.ok, stats=stats, error=report.error)
    report.cost_usd = store.conn.execute("SELECT cost_usd FROM runs WHERE id = ?", (report.run_id,)).fetchone()[0]
    return report


def render_graph_line(report) -> str:
    x = report.extraction
    parts = [f"grafo: {x.extracted if x else 0} itens extraídos"]
    if x:
        parts += [f"+{x.new_entities} entidades", f"{x.mentions} menções", f"{x.relations} relações"]
        if x.merges:
            parts.append(f"{x.merges} fusões")
        if x.errors:
            parts.append(f"{x.errors} com erro")
        if x.deferred:
            parts.append(f"{x.deferred} na fila")
    if report.mirror is not None:
        parts.append(f"Neo4j sincronizado ({report.mirror.items} itens)")
    elif report.mirror_note:
        parts.append(report.mirror_note)
    parts.append(f"US$ {report.cost_usd:.3f}".replace(".", ","))
    if report.error:
        parts.append(f"ERRO: {report.error}")
    return " · ".join(parts)


def _graph_parts(settings, store, gateway, embedder, config):
    from sotawhat.graph.neo4j_sync import Neo4jMirror
    from sotawhat.graph.resolve import Resolver, make_judge

    resolver = Resolver(store, embedder=embedder, judge=make_judge(gateway) if gateway is not None else None,
                        aliases=config.aliases)
    return resolver, Neo4jMirror.from_settings(settings)


def main_graph_extract(ns, settings) -> int:
    """`sotawhat graph extract [--limit N]`: the graph stage on its own (e.g. the first backfill)."""
    from sotawhat.configfiles import ConfigError, load_config
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient
    from sotawhat.store.db import Store
    from sotawhat.store.vectors import get_embedder

    setup_logging(settings.sotawhat_data_dir, date.today().isoformat(), settings.sotawhat_log_level)
    try:
        config = load_config(settings.sotawhat_config_dir)
    except ConfigError as exc:
        print(f"[config] {exc}", file=sys.stderr)
        return 2
    with Store(settings.db_path) as store:
        gateway = None
        if settings.openrouter_api_key:
            client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                                      app_title=settings.openrouter_app_title)
            gateway = LLMGateway(client, store=store, settings=settings, tasks=config.llm["tasks"])
        else:
            print("sem OPENROUTER_API_KEY: só as categorias da triagem entram no grafo", file=sys.stderr)
        resolver, mirror = _graph_parts(settings, store, gateway, get_embedder(settings), config)
        try:
            report = run_graph_stage(store, gateway, resolver, mirror, limit=getattr(ns, "limit", None))
        finally:
            if mirror is not None:
                mirror.close()
    print(render_graph_line(report))
    return 0 if report.ok else 1


def render_summary(report, max_items=10) -> str:
    """P0 summary: still used for the console when the LLM triage is off."""
    lines = [f"{'✅' if report.ok else '❌'} {brand.RUN} <b>{brand.NAME} · run diário {brand.br_date(report.day)}</b>",
             f"{brand.STATS} coletados {sum(report.collected.values())} · novos {len(report.new_items)} · "
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
        lines += ["", f"{brand.NEW} <b>Novos</b> (até {max_items})"]
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
    from sotawhat.pipeline.media import Transcriber, make_describer, whisper_available
    from sotawhat.pipeline.triage import run_triage
    from sotawhat.profiles import build_sources
    from sotawhat.sources.apify import ApifyClient
    from sotawhat.sources.gmail import make_segmenter
    from sotawhat.store.classifier import refresh
    from sotawhat.store.db import Store
    from sotawhat.store.vectors import get_embedder

    settings = load_settings()
    day = date.today().isoformat()
    setup_logging(settings.sotawhat_data_dir, day, settings.sotawhat_log_level)
    if getattr(ns, "catch_up", None) is not None:      # the logon trigger: only a daily missed today
        with Store(settings.db_path) as store:
            due, why = daily_due(store, ns.catch_up)
        log.info("catch-up: %s", why)
        print(f"[catch-up] {why}")
        if not due:
            return 0
    try:
        config = load_config(settings.sotawhat_config_dir)
    except ConfigError as exc:
        print(f"[config] {exc}", file=sys.stderr)
        return 2
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
        segmenter = make_segmenter(gateway) if gateway is not None else None
        apify = ApifyClient(settings.apify_token)
        describer = None
        if gateway is not None:                  # P5: what Instagram posts show (and say, if faster-whisper is in)
            describer = make_describer(gateway, transcriber=Transcriber(settings.models_dir) if whisper_available() else None)
        sources = {name: build_sources(name, settings=settings, segmenter=segmenter, store=store, apify=apify,
                                       describer=describer) for name in PROFILES}

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

        report = run_daily(store, sources, limit=ns.limit, triage=triage,
                           on_start=lambda run_id: setattr(gateway, "run_id", run_id) if gateway else None)
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
        if not ns.no_notify and notifier.configured:     # aulas 3D: the quiz again, 2+ days after each lesson
            try:
                from sotawhat.lessons.deliver import requiz_due
                if (sent := requiz_due(store, notifier)):
                    print(f"[aulas] re-quiz de {sent} aula(s)")
            except Exception as exc:  # noqa: BLE001 - the re-quiz never stops the daily run
                log.warning("re-quiz: %s", exc)
        if not getattr(ns, "no_llm", False):     # the graph stage comes after the digest, never before it
            resolver, mirror = _graph_parts(settings, store, gateway, embedder, config)
            try:
                graph_report = run_graph_stage(store, gateway, resolver, mirror)
            finally:
                if mirror is not None:
                    mirror.close()
            print(f"[{render_graph_line(graph_report)}]")
            log.info("graph %s", render_graph_line(graph_report))
        try:                                     # the tools radar: discovery and today's stars, no LLM
            from sotawhat.radar.commands import scan_step

            line = scan_step(settings, store)
            print(f"[{line}]")
            log.info(line)
        except Exception as exc:  # noqa: BLE001 - the radar never stops the daily run
            log.warning("radar: %s", exc)
    return 0 if report.ok else 1
