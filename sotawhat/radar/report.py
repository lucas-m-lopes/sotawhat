"""The week of the radar (`run weekly`, or `sotawhat radar report`): measures, judge, picks and the section of the
weekly report. Markdown and HTML go to the files and the e-mail. On Telegram each tool is one message with 🧪 testar ·
👍 · 👎 · 🗄️ depois; its delivery is "tool:<owner/repo>", so the votes reach the `feedback` table through
`sotawhat feedback`."""
import json
import time
from dataclasses import asdict
from datetime import date, timedelta

from sotawhat.notify import brand
from sotawhat.notify.telegram import LIMIT, esc
from sotawhat.radar.judge import judge
from sotawhat.radar.measure import downloads, find_packages, latest_release, readme
from sotawhat.radar.score import rank, week_metrics

TOOL_PREFIX = "tool:"


def _packages(store, client, token, m) -> None:
    """Looks the packages up once and keeps them in radar_repos.packages_json."""
    row = store.conn.execute("SELECT packages_json FROM radar_repos WHERE full_name = ?", (m.key,)).fetchone()
    if row is not None and row["packages_json"] is not None:
        m.packages = json.loads(row["packages_json"])
        return
    m.packages = find_packages(client, token, m.name)
    with store._lock:
        store.conn.execute("UPDATE radar_repos SET packages_json = ? WHERE full_name = ?", (json.dumps(m.packages), m.key))
        store.conn.commit()


def _test_from(release_at, days):
    return (date.fromisoformat(release_at) + timedelta(days=days)).isoformat() if release_at else None


def choose(judged, verdicts, cfg) -> list:
    """The report: in score order, relevance ≥ `min_relevance`, a known front, at most `per_front` per front and
    `report_top` in all."""
    lim, per_front, picks = cfg.limits, {}, []
    for m in judged:
        v = verdicts.get(m.key)
        if v is None or v.frente not in cfg.fronts or v.relevancia < lim["min_relevance"]:
            continue
        if per_front.get(v.frente, 0) >= lim["per_front"]:
            continue
        per_front[v.frente] = per_front.get(v.frente, 0) + 1
        picks.append(m)
        if len(picks) >= lim["report_top"]:
            break
    return picks


def card(rank_, m, v, cfg) -> dict:
    return {"rank": rank_, "key": m.key, "name": m.name, "url": m.url, "front": v.frente, "front_label": cfg.label(v.frente),
            "kind": v.tipo, "relevance": v.relevancia, "what": v.o_que_faz, "why": v.por_que_serve, "risks": v.riscos,
            "score": m.score, "stars": m.stars, "week": m.week, "prev_week": m.prev_week, "estimated": m.estimated,
            "downloads": m.downloads, "prev_downloads": m.prev_downloads, "hn_points": m.hn_points,
            "hn_title": m.hn_title, "license": m.license, "language": m.language, "release_at": m.release_at,
            "test_from": _test_from(m.release_at, cfg.limits["test_after_days"])}


def run_radar(store, gateway, cfg, client, token, today, run_id, notes=None) -> dict:
    """The radar section of a weekly run (saved in radar_picks): measures, downloads of the leading candidates, the
    judge and the picks."""
    notes = [] if notes is None else notes
    metrics = week_metrics(store, today)
    for m in rank(metrics, cfg)[:cfg.limits["judge_top"] * 2]:      # downloads only for the leading candidates
        _packages(store, client, token, m)
        for package in m.packages:
            got = downloads(client, package, today)
            if got is not None:
                m.downloads, m.prev_downloads = (m.downloads or 0) + got[0], (m.prev_downloads or 0) + got[1]
    pool = rank(metrics, cfg)
    judged = pool[:cfg.limits["judge_top"]]
    for m in judged:
        m.release_at = latest_release(client, token, m.name)
    readmes = {m.key: readme(client, token, m.name) for m in judged} if gateway is not None else {}
    with store._lock:
        store.conn.executemany("UPDATE radar_repos SET release_at = ? WHERE full_name = ?",
                               [(m.release_at, m.key) for m in judged])
        store.conn.commit()
    if gateway is None:
        notes.append("radar: sem OPENROUTER_API_KEY, nada foi julgado")
        verdicts = {}
    else:
        verdicts = judge(gateway, judged, readmes, cfg, notes=notes)
    picks = choose(judged, verdicts, cfg)
    cards = {m.key: card(n, m, verdicts[m.key], cfg) for n, m in enumerate(picks, 1)}
    with store._lock:
        store.conn.execute("DELETE FROM radar_picks WHERE run_id = ?", (run_id,))
        store.conn.executemany(
            "INSERT INTO radar_picks(run_id, day, full_name, rank, front, score, metrics_json, verdict_json, card_json)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            [(run_id, today.isoformat(), m.key, cards[m.key]["rank"] if m.key in cards else None,
              verdicts[m.key].frente if m.key in verdicts else None, m.score, json.dumps(asdict(m), ensure_ascii=False),
              verdicts[m.key].model_dump_json() if m.key in verdicts else None,
              json.dumps(cards[m.key], ensure_ascii=False) if m.key in cards else None) for m in judged])
        store.conn.commit()
    tracked = store.conn.execute("SELECT COUNT(*) FROM radar_repos").fetchone()[0]
    return {"day": today.isoformat(), "tracked": tracked, "measured": len(metrics), "eligible": len(pool),
            "judged": len(judged), "verdicts": len(verdicts), "estimated": any(m.estimated for m in picks),
            "picks": list(cards.values()), "notes": notes}


# --- rendering ----------------------------------------------------------------------------------------------------
def _int(value) -> str:
    return f"{value:,}".replace(",", ".")


def signal_line(p) -> str:
    parts = [f"★ {_int(p['stars'])}"]
    if p["week"] is not None:
        parts.append(f"+{_int(p['week'])} na semana" + (" (estimativa)" if p["estimated"] else ""))
    if p["downloads"] is not None:
        change = ""
        if p["prev_downloads"]:
            change = f" ({(p['downloads'] - p['prev_downloads']) / p['prev_downloads']:+.0%})".replace(".", ",")
        parts.append(f"{_int(p['downloads'])} downloads na semana{change}")
    if p["hn_points"]:
        parts.append(f"HN {p['hn_points']} pts")
    return " · ".join(parts)


def test_line(p) -> str:
    if p["test_from"]:
        return f"a partir de {p['test_from']} (release de {p['release_at']}; regra das 2 semanas)"
    return "sem release: fixe um commit com mais de 2 semanas"


def footer(radar) -> str:
    text = (f"{radar['tracked']} repositórios acompanhados · {radar['eligible']} com sinal na semana · "
            f"{radar['judged']} julgados")
    if radar.get("estimated"):
        text += " · as estrelas da semana são estimativas até o retrato diário completar 7 dias"
    return text


def _front(p) -> str:
    return f"{brand.front(p.get('front'))} {p['front_label']}"


def section_markdown(radar) -> list:
    out = [f"## {brand.TOOLS} Ferramentas em alta (radar do GitHub)", ""]
    out += [f"> {n}" for n in radar["notes"]] + ([""] if radar["notes"] else [])
    if not radar["picks"]:
        out += ["Nada passou pelo radar desta vez.", ""]
    for p in radar["picks"]:
        out += [f"### {p['rank']}. [{p['name']}]({p['url']}) · {_front(p)}",
                f"{signal_line(p)} · relevância {p['relevance']}/5 · {p['kind']} · {p['license'] or 'licença ?'}", "",
                f"- **O que faz:** {p['what']}", f"- **Por que serve:** {p['why']}"]
        if p["risks"]:
            out.append(f"- **Riscos:** {'; '.join(p['risks'])}")
        out += [f"- **Testar:** {test_line(p)}", ""]
    return out + [f"_{footer(radar)}_", ""]


def section_html(radar, s, card_tag="div") -> list:
    body = [f"<h2 {s['h2']}>{brand.TOOLS} Ferramentas em alta (radar do GitHub)</h2>"]
    body += [f"<p {s['warn']}>{esc(n)}</p>" for n in radar["notes"]]
    if not radar["picks"]:
        body.append(f"<p {s['p']}>Nada passou pelo radar desta vez.</p>")
    for p in radar["picks"]:
        rows = [("O que faz", p["what"]), ("Por que serve", p["why"])] + \
            ([("Riscos", "; ".join(p["risks"]))] if p["risks"] else []) + [("Testar", test_line(p))]
        body.append(f"<{card_tag} {s['card']}><p {s['title']}>{p['rank']}. <a href=\"{esc(p['url'])}\">{esc(p['name'])}</a>"
                    f" · {esc(_front(p))}</p><p {s['meta']}>{esc(signal_line(p))} · relevância {p['relevance']}/5 · "
                    f"{esc(p['kind'])} · {esc(p['license'] or 'licença ?')}</p>"
                    + "".join(f"<p {s['p']}><b>{esc(label)}:</b> {esc(text)}</p>" for label, text in rows)
                    + f"</{card_tag}>")
    body.append(f"<p {s['muted']}>{esc(footer(radar))}</p>")
    return body


def messages(radar) -> list:
    """A header, then one message per tool (the buttons go on these). -> [{"text", "tool"}]."""
    if not radar or not radar["picks"]:
        return []
    head = [f"{brand.TOOLS} <b>Ferramentas em alta</b> · {len(radar['picks'])} do radar do GitHub", esc(footer(radar))]
    head += [f"⚠️ {esc(n[:300])}" for n in radar["notes"][:2]]
    out = [{"text": "\n".join(head)[:LIMIT], "tool": None}]
    for p in radar["picks"]:
        lines = [f"{brand.front(p.get('front'))} <b>{p['rank']}. {esc(p['name'])}</b> · {esc(p['front_label'])}",
                 f"📈 {esc(signal_line(p))} · relevância {p['relevance']}/5", f"🔧 {esc(p['what'][:400])}",
                 f"💡 {esc(p['why'][:500])}"]
        if p["risks"]:
            lines.append(f"⚠️ {esc('; '.join(p['risks'])[:400])}")
        lines += [f"🧪 testar {esc(test_line(p))}", esc(p["url"])]
        out.append({"text": "\n".join(lines)[:LIMIT], "tool": p["key"]})
    return out


def send(notifier, store, radar, run_id, day, pause=0.4, sleep=time.sleep) -> int:
    """Every tool message is a delivery "tool:<owner/repo>" with the 🧪 👍 👎 🗄️ buttons."""
    from sotawhat.pipeline.deliver import item_key, tool_keyboard

    sent = 0
    for message in messages(radar):
        markup, delivery = None, None
        if message["tool"] is not None:
            item_id = TOOL_PREFIX + message["tool"]
            row = {"key": item_key(item_id), "item_id": item_id}
            delivery = store.record_delivery(run_id, day, item_id, row["key"], "tool", sent)
            markup = tool_keyboard(row)
        result = notifier.send_message(message["text"], reply_markup=markup, disable_notification=message["tool"] is not None)
        if delivery is not None:
            store.mark_delivered([delivery], notifier.chat_id, result.get("message_id"))
        sent += 1
        if pause:
            sleep(pause)
    return sent


def tool_votes(store) -> dict:
    """The latest vote per tool (owner/repo in lower case -> up | down | test | archive)."""
    rows = store.conn.execute("SELECT target_id, value FROM feedback WHERE target_type = 'tool' ORDER BY id").fetchall()
    return {r[0]: r[1] for r in rows}


def radar_view(store, history_days=30) -> dict:
    """The interface's view: the picks of the latest radar run, each with its vote and its star counts of the last
    `history_days`."""
    conn = store.conn
    tracked = conn.execute("SELECT COUNT(*) FROM radar_repos").fetchone()[0]
    days = conn.execute("SELECT COUNT(DISTINCT day) FROM radar_stars").fetchone()[0]
    base = {"tracked": tracked, "days": days, "scanned_at": store.meta_get("radar_scanned_at"), "picks": []}
    last = conn.execute("SELECT run_id, day FROM radar_picks WHERE card_json IS NOT NULL ORDER BY run_id DESC LIMIT 1"
                        ).fetchone()
    if last is None:
        return {**base, "run_id": None, "day": None}
    votes, since = tool_votes(store), (date.fromisoformat(last["day"]) - timedelta(days=history_days)).isoformat()
    picks = []
    for row in conn.execute("SELECT full_name, card_json FROM radar_picks WHERE run_id = ? AND card_json IS NOT NULL"
                            " ORDER BY rank", (last["run_id"],)):
        history = conn.execute("SELECT day, stars FROM radar_stars WHERE full_name = ? AND day >= ? ORDER BY day",
                               (row["full_name"], since)).fetchall()
        picks.append({**json.loads(row["card_json"]), "vote": votes.get(row["full_name"]),
                      "history": [[d, s] for d, s in history]})
    return {**base, "run_id": last["run_id"], "day": last["day"], "picks": picks}
