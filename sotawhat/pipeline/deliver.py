# sotawhat/pipeline/deliver.py
"""Daily digest (SDD §6.11): two ranked sections ("IA ∩ Saúde" and "Fronteira de IA") plus a one-line
radar, as Markdown + HTML files (always) and Telegram messages with 👍/👎/🧪 buttons. When nothing was
approved and nothing broke, nothing is sent."""
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from sotawhat import taxonomy as tx
from sotawhat.notify.telegram import LIMIT, esc, esc_attr

VOTES = {"up": "👍", "down": "👎", "test": "🧪"}
CODES = {"up": "u", "down": "d", "test": "t"}
ALERT_AFTER = 3


def item_key(item_id) -> str:
    return hashlib.sha1(item_id.encode("utf-8")).hexdigest()[:10]


def num(value, digits=2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


@dataclass
class Entry:
    item_id: str
    title: str
    url: str
    source: str
    profile: str
    total: float
    scores: dict
    summary: str
    why: str
    tags: dict
    sources: list
    section: str = "main"
    position: int = 0

    @property
    def key(self) -> str:
        return item_key(self.item_id)

    def row(self) -> dict:
        return {"key": self.key, "position": self.position, "item_id": self.item_id, "section": self.section}


@dataclass
class Digest:
    day: str
    stats_line: str
    main: list
    radar: list
    extra: list                                  # approved beyond main_limit: only in the files
    failing: list                                # [(source key, consecutive failures, error)]
    error: str | None = None
    notes: list = field(default_factory=list)
    frontier: list = field(default_factory=list)  # "Fronteira de IA": strong frontier AI, even without a health link

    @property
    def alerts(self) -> list:
        return [f for f in self.failing if f[1] >= ALERT_AFTER]

    @property
    def worth_sending(self) -> bool:
        return bool(self.main or self.frontier or self.radar or self.alerts or self.error)


def _entry(store, row) -> Entry:
    return Entry(item_id=row["item_id"], title=row["title"], url=row["canonical_url"] or "", source=row["source"],
                 profile=row["profile"] or "", total=row["total"] or 0.0,
                 scores=json.loads(row["scores_json"] or "{}"), summary=row["summary_pt"] or "",
                 why=row["why_it_matters_pt"] or "", tags=json.loads(row["tags_json"] or "{}"),
                 sources=store.cluster_sources(row["item_id"]), section=row["decision"])


def build_digest(store, report, rubric) -> Digest:
    entries = [_entry(store, row) for row in store.triage_rows(report.run_id)]
    main = sorted((e for e in entries if e.section == "main"),
                  key=lambda e: (-e.total, -e.scores.get("B", 0), e.title))
    frontier = sorted((e for e in entries if e.section == "frontier"),
                      key=lambda e: (-e.total, -e.scores.get("A", 0), e.title))
    extra, main = main[rubric.main_limit:], main[:rubric.main_limit]
    overflow, frontier = frontier[rubric.frontier_limit:], frontier[:rubric.frontier_limit]
    for e in overflow:                      # frontier items beyond the limit become the first radar lines
        e.section = "radar"
    radar = sorted(overflow + [e for e in entries if e.section == "radar" and e not in overflow],
                   key=lambda e: (-e.total, -e.scores.get("A", 0), e.title))[:rubric.radar_limit]
    for position, e in enumerate(main + frontier, 1):   # one numbering across both main sections
        e.position = position
    for position, e in enumerate(radar, 1):
        e.position = position
    t = report.triage
    triaged = t.triaged if t else 0
    stats_line = (f"coletados {sum(report.collected.values())} · novos {len(report.new_items)} · "
                  f"triados {triaged} · saúde {len(main)} · fronteira {len(frontier)} · radar {len(radar)} · "
                  f"custo US$ {num(report.cost_usd)}")
    notes = []
    if t is None or not t.llm:
        notes.append("triagem por LLM desligada (sem OPENROUTER_API_KEY ou --no-llm): itens aguardam o próximo run")
    if t and t.stopped:
        notes.append(f"triagem interrompida: {t.stopped}")
    if t and t.deferred and t.llm:
        notes.append(f"{t.deferred} itens ficaram para o próximo run")
    if t and t.errors:
        notes.append(f"{t.errors} itens com erro de LLM (nova tentativa no próximo run)")
    notes += list(t.warnings) if t else []
    if extra:
        notes.append(f"+{len(extra)} aprovados além do limite diário (só no arquivo do dia)")
    failing = [(key, count, err) for key, (count, err) in sorted(report.failing.items())]
    return Digest(day=report.day, stats_line=stats_line, main=main, radar=radar, extra=extra,
                  failing=failing, error=report.error, notes=notes, frontier=frontier)


def _tag_labels(e, limit=3) -> list:
    keys = (e.tags.get("domains") or [])[:2] + (e.tags.get("techniques") or [])[:2]
    labels = [tx.label(k) for k in keys][:limit]
    if e.tags.get("evidence_stage"):
        labels.append(f"{e.tags['evidence_stage']} {tx.label(e.tags['evidence_stage'])}")
    return labels


def _scores(e) -> str:
    return " ".join(f"{k}{e.scores[k]}" for k in "ABCD" if k in e.scores)


def _sources(e) -> str:
    return " + ".join(e.sources) if e.sources else e.source


# --- files --------------------------------------------------------------------
def render_markdown(d) -> str:
    out = [f"# sotawhat · {d.day}", "", d.stats_line, ""]
    out += [f"> {n}" for n in d.notes] + ([""] if d.notes else [])
    if d.error:
        out += [f"> ❌ erro no run: {d.error}", ""]
    for title, entries in (("IA ∩ Saúde", d.main), ("Fronteira de IA", d.frontier)):
        if not entries:
            continue
        out += [f"## {title}", ""]
        for e in entries:
            out += [f"### {e.position}. [{e.title}]({e.url})",
                    f"**{num(e.total)}** · {_scores(e)} · {_sources(e)} · {' · '.join(_tag_labels(e))}", "",
                    e.summary, "", f"**Por que importa:** {e.why}", "", f"`{e.item_id}`", ""]
    if d.radar:
        out += ["## Radar", ""]
        out += [f"{e.position}. [{e.title}]({e.url}) — {_sources(e)} · {_scores(e)}" for e in d.radar] + [""]
    if d.extra:
        out += ["## Também aprovados (além do limite diário)", ""]
        out += [f"- [{e.title}]({e.url}) — {num(e.total)} · {_sources(e)}" for e in d.extra] + [""]
    if d.failing:
        out += ["## Fontes com falha", ""]
        out += [f"- {key}: {err[:160]}" + (f" — **{count}ª falha seguida**" if count >= ALERT_AFTER else "")
                for key, count, err in d.failing] + [""]
    if not (d.main or d.frontier or d.radar):
        out += ["Nada relevante hoje.", ""]
    return "\n".join(out)


_CSS = """:root{--bg:#fbfaf7;--fg:#1f2328;--muted:#5d6670;--card:#fff;--line:#e3e0d8;--accent:#0b6e4f}
@media (prefers-color-scheme:dark){:root{--bg:#14171a;--fg:#e8e6e1;--muted:#a3abb3;--card:#1c2024;--line:#2c3237;--accent:#4cc39a}}
body{background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;max-width:46rem;margin:0 auto;padding:1rem}
h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem}.muted{color:var(--muted)}a{color:var(--accent)}
article{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.8rem 1rem;margin:.8rem 0}
article h3{font-size:1rem;margin:.2rem 0}.meta{color:var(--muted);font-size:.85rem}li{margin:.3rem 0}"""


def render_html(d) -> str:
    def a(e):
        return f'<a href="{esc_attr(e.url)}">{esc(e.title)}</a>'

    body = [f"<h1>sotawhat · {esc(d.day)}</h1>", f'<p class="muted">{esc(d.stats_line)}</p>']
    body += [f'<p class="muted">{esc(n)}</p>' for n in d.notes]
    if d.error:
        body.append(f"<p>❌ erro no run: {esc(d.error)}</p>")
    for title, entries in (("IA ∩ Saúde", d.main), ("Fronteira de IA", d.frontier)):
        if not entries:
            continue
        body.append(f"<h2>{title}</h2>")
        for e in entries:
            body.append(f'<article><h3>{e.position}. {a(e)}</h3><p class="meta"><b>{num(e.total)}</b> · '
                        f"{esc(_scores(e))} · {esc(_sources(e))} · {esc(' · '.join(_tag_labels(e)))}</p>"
                        f"<p>{esc(e.summary)}</p><p><b>Por que importa:</b> {esc(e.why)}</p></article>")
    if d.radar:
        body.append("<h2>Radar</h2><ol>" + "".join(
            f"<li>{a(e)} <span class=\"meta\">— {esc(_sources(e))} · {esc(_scores(e))}</span></li>" for e in d.radar)
            + "</ol>")
    if d.extra:
        body.append("<h2>Também aprovados</h2><ul>" + "".join(
            f"<li>{a(e)} <span class=\"meta\">— {num(e.total)}</span></li>" for e in d.extra) + "</ul>")
    if d.failing:
        body.append("<h2>Fontes com falha</h2><ul>" + "".join(
            f"<li>{esc(k)}: {esc(err[:160])}" + (f" — <b>{c}ª falha seguida</b>" if c >= ALERT_AFTER else "") + "</li>"
            for k, c, err in d.failing) + "</ul>")
    if not (d.main or d.frontier or d.radar):
        body.append("<p>Nada relevante hoje.</p>")
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>sotawhat {esc(d.day)}</title>'
            f"<style>{_CSS}</style></head><body>{''.join(body)}</body></html>")


def write_files(d, out_dir) -> tuple:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md, page = out_dir / f"{d.day}.md", out_dir / f"{d.day}.html"
    md.write_text(render_markdown(d), encoding="utf-8")
    page.write_text(render_html(d), encoding="utf-8")
    return md, page


# --- Telegram -----------------------------------------------------------------
def keyboard(rows, votes=None) -> dict:
    """rows: mappings with key/position/item_id. One item: 👍 👎 🧪. Several (radar): '1 👍' '1 👎' pairs."""
    votes = votes or {}

    def button(row, value, label):
        chosen = votes.get(row["item_id"]) == value
        return {"text": f"✅{label}" if chosen else label, "callback_data": f"f:{row['key']}:{CODES[value]}"}

    if len(rows) == 1:
        return {"inline_keyboard": [[button(rows[0], v, e) for v, e in VOTES.items()]]}
    buttons = [button(r, v, f"{r['position']} {VOTES[v]}") for r in rows for v in ("up", "down")]
    return {"inline_keyboard": [buttons[i:i + 4] for i in range(0, len(buttons), 4)]}


def _clip(text, n) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n - 1] + "…"


def telegram_messages(d) -> list:
    day = "/".join(reversed(d.day.split("-")))
    header = [f"🗞️ <b>sotawhat · {esc(day)}</b>", esc(d.stats_line)]
    header += [f"ℹ️ {esc(n)}" for n in d.notes]
    if d.error:
        header.append(f"❌ <b>erro no run:</b> {esc(d.error[:300])}")
    if d.alerts:
        header.append("⚠️ <b>Alertas</b>: " + "; ".join(f"{esc(k)} ({c}ª falha seguida)" for k, c, _ in d.alerts))
    others = [k for k, c, _ in d.failing if c < ALERT_AFTER]
    if others:
        header.append(f"⚠️ falha hoje: {esc(', '.join(others))}")
    messages = [{"text": "\n".join(header), "rows": [], "silent": False}]
    for prefix, entries in (("", d.main), ("🔭 ", d.frontier)):
        for e in entries:
            text = (f'{prefix}<b>{e.position}.</b> <a href="{esc_attr(e.url)}">{esc(_clip(e.title, 300))}</a>\n'
                    f"⭐ <b>{num(e.total)}</b> · {_scores(e)} · {esc(_sources(e))}\n"
                    f"🏷️ {esc(' · '.join(_tag_labels(e)))}\n{esc(_clip(e.summary, 700))}\n"
                    f"💡 <i>{esc(_clip(e.why, 450))}</i>")
            messages.append({"text": text[:LIMIT], "rows": [e.row()], "silent": True})
    if d.radar:
        lines = ["📡 <b>Radar</b> (mais IA, uma linha cada)"]
        lines += [f'{e.position}. <a href="{esc_attr(e.url)}">{esc(_clip(e.title, 200))}</a> — {esc(_sources(e))} '
                  f"· A{e.scores.get('A', '?')}" for e in d.radar]
        messages.append({"text": "\n".join(lines)[:LIMIT], "rows": [e.row() for e in d.radar], "silent": True})
    return messages


def send_digest(notifier, store, d, run_id, pause=0.4, sleep=time.sleep) -> int:
    """Send the header, one message per item of both main sections (🔭 marks "Fronteira de IA") and the
    radar; record every delivery so the buttons can be traced back to their items."""
    sent = 0
    for message in telegram_messages(d):
        ids = [store.record_delivery(run_id, d.day, r["item_id"], r["key"], r["section"], r["position"])
               for r in message["rows"]]
        result = notifier.send_message(message["text"], reply_markup=keyboard(message["rows"]) if message["rows"] else None,
                                       disable_notification=message["silent"])
        store.mark_delivered(ids, notifier.chat_id, result.get("message_id"))
        sent += 1
        if pause:
            sleep(pause)
    return sent
