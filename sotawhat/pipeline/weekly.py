# sotawhat/pipeline/weekly.py
"""`sotawhat run weekly` and `sotawhat ideate` (SDD §6.1 stages 8–10, §8).

run weekly: Neo4j mirror sync (when it answers), intelligence (trends, labeled communities, gaps), the
meta-review of the reader's idea decisions, the idea engine (economic mode) and the weekly report: Markdown
and HTML files in data/weekly, Telegram (a header plus one message with four buttons per idea) and an
e-mail copy.
ideate: the idea engine alone, on demand (`--tema`, `--n`, `--modo`), with the same report restricted to
the ideas. Both stop gracefully at SOTAWHAT_LLM_BUDGET_USD_RUN_WEEKLY."""
import json
import logging
import sys
import time
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from pathlib import Path

from sotawhat import taxonomy as tx
from sotawhat.graph import intelligence as intel
from sotawhat.graph.query import TYPE_LABELS
from sotawhat.ideation.ledger import idea_card
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import CommunityLabel, MetaReview
from sotawhat.notify.telegram import LIMIT, esc
from sotawhat.pipeline.deliver import _CSS, _MAIL, _clip, idea_keyboard, item_key, num

log = logging.getLogger("sotawhat.weekly")
AXIS_LABELS = {"valor": "valor", "viabilidade_tecnica": "técnica", "viabilidade_negocio": "negócio",
               "novidade": "novidade", "regulatorio": "regulatório", "tempo_piloto": "piloto", "fit": "fit",
               "adocao": "adoção"}
FACET_LABELS = {"problema": "problema", "tecnica": "técnica", "dado": "dado", "integracao": "integração",
                "modelo_negocio": "modelo de negócio", "geografia": "geografia/BR"}
STATE_LABELS = {"nao_encontrado": "não encontrado", "parcial": "parcial", "igual": "igual", "a_verificar": "a verificar"}
GAP_TITLES = (("recent_technique", "Técnicas recentes sem ligação com problemas frequentes"),
              ("community_bridge", "Pontes entre comunidades que quase não se tocam"),
              ("serendipity", "Serendipidade (pares distantes)"))


@dataclass
class WeeklyReport:
    run_id: int
    day: str
    kind: str = "weekly"
    theme: str | None = None
    trends: list = field(default_factory=list)
    communities: list = field(default_factory=list)
    gaps: dict = field(default_factory=dict)
    rules: list = field(default_factory=list)
    ideation: object = None
    ok: bool = True
    error: str | None = None
    cost_usd: float = 0.0
    notes: list = field(default_factory=list)
    payload: dict = field(default_factory=dict)


def scale(config, n):
    """`--n N`: N finalists out of N candidates (each candidate goes through every lens of its turn, so there
    are at least 3N drafts), with critique, prior art and judges for N + 2 of them."""
    n = max(1, n)
    return replace(config, candidates=n, finalists=n, top_k=n + 2)


# --- intelligence -------------------------------------------------------------------
def _fallback_label(group) -> str:
    return " · ".join(name for _, name, _ in group["top"][:3])


def label_communities(gateway, store, groups, run_id, top=8, notes=None) -> list:
    """Stores every community with its members. The `top` most important get an LLM label and summary. A
    failed call keeps the label made of the three main names; a budget stop ends the labeling."""
    labeled, assignments, labels = [], {}, {}
    system = load_prompt("community_v1")
    for group in groups:
        for entity_id in group["members"]:
            assignments[entity_id] = group["community"]
        label, summary = _fallback_label(group), ""
        if gateway is not None and group["community"] < top:
            members = group["members"][:8]
            titles = [r[0] for r in store.conn.execute(
                "SELECT i.title FROM entity_mentions m JOIN items i ON i.id = m.item_id "
                f"WHERE m.entity_id IN ({','.join('?' * len(members))}) GROUP BY i.id "
                "ORDER BY MAX(i.fetched_at) DESC LIMIT 8", members)]
            user = ("Main entities: " + ", ".join(f"{n} ({t})" for _, n, t in group["top"]) + "\nRecent items:\n"
                    + "\n".join(f"- {t[:160]}" for t in titles))
            try:
                res = gateway.structured_call("synth", [{"role": "system", "content": system},
                                                        {"role": "user", "content": user}], CommunityLabel)
                label, summary = res.output.rotulo.strip() or label, res.output.resumo.strip()
            except (BudgetExceeded, InsufficientCredits) as exc:
                if notes is not None:
                    notes.append(f"rótulos das comunidades interrompidos: {str(exc)[:160]}")
                gateway = None
            except LLMFailure as exc:
                if notes is not None:
                    notes.append(f"rótulo da comunidade {group['community']}: {str(exc)[:160]}")
        labels[group["community"]] = (label, summary, group["size"], group["members"][0])
        labeled.append({"community": group["community"], "label": label, "summary": summary, "size": group["size"],
                        "top": [name for _, name, _ in group["top"][:6]], "types": group["types"]})
    store.save_communities(run_id, assignments, labels)
    return labeled


def meta_review(gateway, store, min_decisions=4, notes=None) -> list:
    """Turns the reader's latest idea decisions (and their reasons) into ≤ 10 rules for the generators, kept
    in meta.ideation_rules. Below `min_decisions` decisions, or when the call fails, the stored rules stay."""
    stored = json.loads(store.meta_get("ideation_rules", "[]"))
    rows = store.conn.execute(
        "SELECT i.title, i.lens, i.niche, f.value, f.note FROM feedback f "
        "JOIN ideas i ON i.id = CAST(f.target_id AS INTEGER) WHERE f.target_type = 'idea' "
        "ORDER BY f.id DESC LIMIT 60").fetchall()
    if gateway is None or len(rows) < min_decisions:
        return stored
    user = ("Current rules:\n" + ("".join(f"- {r}\n" for r in stored) or "(none)\n") + "\nDecisions, newest first:\n"
            + "\n".join(f"- {r['value']}: {r['title']} (lens {r['lens']}, niche {r['niche']})"
                        + (f" — reason: {r['note']}" if r["note"] else "") for r in rows))
    try:
        res = gateway.structured_call("synth", [{"role": "system", "content": load_prompt("metareview_v1")},
                                                {"role": "user", "content": user}], MetaReview)
    except (BudgetExceeded, InsufficientCredits, LLMFailure) as exc:
        if notes is not None:
            notes.append(f"meta-review: {str(exc)[:160]}")
        return stored
    rules = [r.strip() for r in res.output.regras if r.strip()][:10]
    store.meta_set("ideation_rules", json.dumps(rules, ensure_ascii=False))
    return rules


# --- payload --------------------------------------------------------------------------
def build_payload(report, store) -> dict:
    ideation = report.ideation
    return {"kind": report.kind, "day": report.day, "run_id": report.run_id, "theme": report.theme,
            "trends": report.trends[:12], "communities": report.communities[:8],
            "gaps": {k: v[:5] for k, v in (report.gaps or {}).items()}, "rules": report.rules,
            "ideas": [idea_card(store.get_idea(i)) for i in (ideation.finalists if ideation else [])],
            "discarded": (ideation.discarded if ideation else [])[:20],
            "stats": {"candidates": ideation.candidates if ideation else 0, "drafts": ideation.drafts if ideation else 0,
                      "kept": len(ideation.kept) if ideation else 0, "critiqued": ideation.critiqued if ideation else 0,
                      "cost_usd": round(report.cost_usd, 4), "stopped": ideation.stopped if ideation else None},
            "notes": report.notes + (ideation.warnings[:5] if ideation else []), "error": report.error}


def _title(payload) -> str:
    what = "relatório semanal" if payload["kind"] == "weekly" else "ideação sob demanda"
    return f"sotawhat · {what} · {payload['day']}" + (f" · tema “{payload['theme']}”" if payload.get("theme") else "")


def _stats_line(payload) -> str:
    s = payload["stats"]
    return (f"{s['candidates']} candidatos · {s['drafts']} rascunhos · {s['kept']} após dedup · {s['critiqued']} "
            f"criticadas · {len(payload['ideas'])} finalistas · US$ {num(s['cost_usd'], 3)}")


def _axes(idea) -> str:
    return " · ".join(f"{AXIS_LABELS.get(k, k)} {num(v, 1)}" for k, v in idea["axes"].items())


def _facets(idea) -> str:
    """Facets grouped by verdict: "não encontrado: problema, técnica; parcial: dado"."""
    groups = {}
    for facet, verdict in idea["facets"].items():
        groups.setdefault(verdict["estado"], []).append(FACET_LABELS.get(facet, facet))
    return "; ".join(f"{STATE_LABELS.get(state, state)}: {', '.join(names)}"
                     for state, names in sorted(groups.items(), key=lambda kv: list(STATE_LABELS).index(kv[0])
                                                if kv[0] in STATE_LABELS else 9))


def _type(name) -> str:
    return TYPE_LABELS.get(name, name)


def _sector(draft) -> str:
    code = draft.get("setor", "")
    return f"{code} {tx.label(code)}" if code else "?"


def _notes(payload) -> list:
    out = list(payload["notes"])
    if payload["stats"]["stopped"]:
        out.append(f"ideação interrompida: {payload['stats']['stopped']}")
    if payload.get("error"):
        out.append(f"erro no run: {payload['error']}")
    return out


def _rows(idea) -> list:
    """(label, text) lines of an idea card, shared by the Markdown and HTML renderers."""
    d = idea["draft"]
    rows = [("Problema", d.get("problema_jtbd", "")), ("Dono", d.get("stakeholder_dono", "")),
            ("Como funciona", d.get("mecanismo", "")),
            ("Dados e integração", f"{', '.join(d.get('dado_necessario', []))} · {d.get('integracao', '')}"),
            ("Modelo de negócio", d.get("modelo_negocio", "")), ("Por que agora", d.get("why_now", "")),
            ("Hipótese nula", d.get("hipotese_nula", ""))]
    if idea["axes"]:
        rows.append(("Eixos", f"{_axes(idea)} · confiança {num(idea['confidence'] or 0, 2)}"))
    if idea.get("disputed_gates"):
        rows.append(("Gates em disputa (só um juiz; confira)", ", ".join(idea["disputed_gates"])))
    if idea["facets"]:
        rows.append(("Novidade por faceta", _facets(idea)))
    for layer, neighbors in idea["neighbors"].items():
        rows.append((f"Vizinhos ({layer})", "; ".join(f"{x['title'][:90]} ({x.get('year') or '?'})" for x in neighbors)))
    if idea["unverified"]:
        rows.append(("Não verificado", "; ".join(idea["unverified"])))
    if idea.get("dossie"):
        dz = idea["dossie"]
        rows += [("Piloto de 90 dias", dz["piloto_90d"]), ("Plano de evidência", dz["plano_evidencia"]),
                 ("SaMD e LGPD", f"{dz['classe_samd']} · {dz['base_legal_lgpd']}")]
    if idea["kill"]:
        rows.append(("Critérios de descarte dos críticos", "; ".join(idea["kill"])))
    if idea.get("pre_mortem"):
        rows.append(("Pré-mortem", idea["pre_mortem"]))
    return rows


def _meta(idea) -> str:
    d = idea["draft"]
    return f"lente {idea['lens']} · {idea['persona']} · {_sector(d)} · {d.get('forma', '?')} · idea:{idea['id']}"


def render_markdown(payload) -> str:
    out = [f"# {_title(payload)}", "", _stats_line(payload), ""]
    notes = _notes(payload)
    out += [f"> {n}" for n in notes] + ([""] if notes else []) + ["## Ideias", ""]
    if not payload["ideas"]:
        out += ["Nenhuma ideia passou pelos filtros desta vez.", ""]
    for n, idea in enumerate(payload["ideas"], 1):
        out += [f"### {n}. {idea['title']}", f"**{num(idea['score'])}** · {_meta(idea)}", ""]
        out += [f"- **{label}:** {text}" for label, text in _rows(idea)] + [""]
    if payload["trends"]:
        out += ["## Em alta (7 dias contra os 28 anteriores)", ""]
        out += [f"- {t['name']} ({_type(t['type'])}): {t['recent']} itens na semana, {t['baseline']} antes"
                + (" · **novo**" if t["new"] else "") for t in payload["trends"]] + [""]
    if payload["communities"]:
        out += ["## Mapa da semana (comunidades do grafo)", ""]
        out += [f"- **{c['label']}** ({c['size']} entidades): {c['summary'] or ', '.join(c['top'])}"
                for c in payload["communities"]] + [""]
    if any(payload["gaps"].values()):
        out += ["## Lacunas", ""]
        out += [f"- **{title}:** " + "; ".join(f"{c['technique']} × {c['problem']}" for c in payload["gaps"][name])
                for name, title in GAP_TITLES if payload["gaps"].get(name)] + [""]
    if payload["rules"]:
        out += ["## Regras do meta-review (entram nos prompts de geração)", ""] + [f"- {r}" for r in payload["rules"]] + [""]
    if payload["discarded"]:
        out += ["## Descartadas e por quê", ""] + [f"- {d['title']}: {d['reason']}" for d in payload["discarded"]] + [""]
    return "\n".join(out)


def _html(payload, s, card="div") -> list:
    """Body blocks; `s` maps a role (h1, h2, muted, warn, card, title, meta, p, li) to an attribute string."""
    body = [f"<h1 {s['h1']}>{esc(_title(payload))}</h1>", f"<p {s['muted']}>{esc(_stats_line(payload))}</p>"]
    body += [f"<p {s['warn']}>{esc(n)}</p>" for n in _notes(payload)]
    body.append(f"<h2 {s['h2']}>Ideias</h2>")
    if not payload["ideas"]:
        body.append(f"<p {s['p']}>Nenhuma ideia passou pelos filtros desta vez.</p>")
    for n, idea in enumerate(payload["ideas"], 1):
        body.append(f"<{card} {s['card']}><p {s['title']}>{n}. {esc(idea['title'])}</p>"
                    f"<p {s['meta']}><b>{num(idea['score'])}</b> · {esc(_meta(idea))}</p>"
                    + "".join(f"<p {s['p']}><b>{esc(label)}:</b> {esc(text)}</p>" for label, text in _rows(idea))
                    + f"</{card}>")
    if payload["trends"]:
        body.append(f"<h2 {s['h2']}>Em alta (7 dias contra os 28 anteriores)</h2><ul>" + "".join(
            f"<li {s['li']}>{esc(t['name'])} <span {s['meta']}>({esc(_type(t['type']))}) {t['recent']} na semana, "
            f"{t['baseline']} antes{' · novo' if t['new'] else ''}</span></li>" for t in payload["trends"]) + "</ul>")
    if payload["communities"]:
        body.append(f"<h2 {s['h2']}>Mapa da semana</h2><ul>" + "".join(
            f"<li {s['li']}><b>{esc(c['label'])}</b> <span {s['meta']}>({c['size']} entidades)</span> "
            f"{esc(c['summary'] or ', '.join(c['top']))}</li>" for c in payload["communities"]) + "</ul>")
    if any(payload["gaps"].values()):
        body.append(f"<h2 {s['h2']}>Lacunas</h2><ul>" + "".join(
            f"<li {s['li']}><b>{esc(title)}:</b> "
            + esc("; ".join(f"{c['technique']} × {c['problem']}" for c in payload["gaps"][name])) + "</li>"
            for name, title in GAP_TITLES if payload["gaps"].get(name)) + "</ul>")
    if payload["rules"]:
        body.append(f"<h2 {s['h2']}>Regras do meta-review</h2><ul>"
                    + "".join(f"<li {s['li']}>{esc(r)}</li>" for r in payload["rules"]) + "</ul>")
    if payload["discarded"]:
        body.append(f"<h2 {s['h2']}>Descartadas e por quê</h2><ul>" + "".join(
            f"<li {s['li']}>{esc(d['title'])} <span {s['meta']}>— {esc(d['reason'])}</span></li>"
            for d in payload["discarded"]) + "</ul>")
    return body


_PAGE = {"h1": "", "h2": "", "muted": 'class="muted"', "warn": 'class="muted"', "card": "", "title": 'class="t"',
         "meta": 'class="meta"', "p": "", "li": ""}


def render_html(payload) -> str:
    body = "".join(_html(payload, _PAGE, card="article"))
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(_title(payload))}</title>'
            f"<style>{_CSS}.t{{font-weight:600;margin:.2rem 0}}</style></head><body>{body}</body></html>")


def render_email(payload) -> tuple:
    """(subject, plain text, HTML with inline styles only). Votes stay in Telegram and in the interface."""
    s = {role: f'style="{_MAIL[role]}"' for role in ("h1", "h2", "muted", "warn", "card", "title", "meta", "p", "li")}
    body = _html(payload, s) + [f"<p {s['muted']}>Vote 👍 explorar · 👎 · 🧪 testar · 🗄️ engavetar nas mensagens do "
                                "Telegram ou na interface (http://127.0.0.1:8765); este e-mail é uma cópia do relatório.</p>"]
    html = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
            f'<body style="{_MAIL["body"]}">' + "".join(body) + "</body></html>")
    what = "semana" if payload["kind"] == "weekly" else "ideias"
    subject = f"sotawhat · {what} {payload['day']} · {len(payload['ideas'])} ideias" + (" ⚠️" if _notes(payload) else "")
    return subject, render_markdown(payload), html


def file_stem(payload) -> str:
    return f"{payload['day']}-semana" if payload["kind"] == "weekly" else f"{payload['day']}-ideias-{payload['run_id']}"


def write_files(payload, out_dir) -> tuple:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md, page = out_dir / f"{file_stem(payload)}.md", out_dir / f"{file_stem(payload)}.html"
    md.write_text(render_markdown(payload), encoding="utf-8")
    page.write_text(render_html(payload), encoding="utf-8")
    return md, page


# --- Telegram ---------------------------------------------------------------------------
def telegram_messages(payload) -> list:
    """A header, then one message per idea (the buttons go on these). Text is clipped before escaping, so an
    HTML entity is never cut in half."""
    s = payload["stats"]
    head = [f"💡 <b>{esc(_title(payload))}</b>",
            esc(f"{len(payload['ideas'])} ideias de {s['drafts']} rascunhos · US$ {num(s['cost_usd'], 3)}")]
    if payload["trends"]:
        head.append("📈 em alta: " + esc(_clip(", ".join(t["name"] for t in payload["trends"][:8]), 400)))
    if payload["communities"]:
        head.append("🗺️ mapa: " + esc(_clip(" | ".join(c["label"] for c in payload["communities"][:6]), 500)))
    head += [f"⚠️ {esc(_clip(n, 300))}" for n in _notes(payload)[:3]]
    messages = [{"text": "\n".join(head)[:LIMIT], "idea": None}]
    for n, idea in enumerate(payload["ideas"], 1):
        d = idea["draft"]
        lines = [f"<b>{n}. {esc(_clip(idea['title'], 200))}</b>",
                 f"⭐ <b>{num(idea['score'])}</b> · lente {esc(idea['lens'])} · {esc(_sector(d))} · {esc(d.get('forma', '?'))}",
                 f"🩺 {esc(_clip(d.get('problema_jtbd', ''), 400))}", f"⚙️ {esc(_clip(d.get('mecanismo', ''), 600))}",
                 f"⏱️ {esc(_clip(d.get('why_now', ''), 250))}", f"🛑 {esc(_clip(d.get('hipotese_nula', ''), 250))}"]
        if idea["facets"]:
            lines.append(f"🔎 {esc(_clip(_facets(idea), 300))}")
        if idea.get("dossie"):
            lines.append(f"🧪 piloto: {esc(_clip(idea['dossie']['piloto_90d'], 350))}")
        messages.append({"text": "\n".join(lines), "idea": idea["id"]})
    return messages


def send_weekly(notifier, store, payload, run_id, pause=0.4, sleep=time.sleep) -> int:
    """Every idea message is a delivery with item_id "idea:<id>", so its buttons (callback f:<key>:u|d|t|a)
    reach the idea ledger through `sotawhat feedback`."""
    sent = 0
    for message in telegram_messages(payload):
        markup, delivery = None, None
        if message["idea"] is not None:
            item_id = f"idea:{message['idea']}"
            row = {"key": item_key(item_id), "item_id": item_id}
            delivery = store.record_delivery(run_id, payload["day"], item_id, row["key"], "idea", sent)
            markup = idea_keyboard(row)
        result = notifier.send_message(message["text"], reply_markup=markup, disable_notification=message["idea"] is not None)
        if delivery is not None:
            store.mark_delivered([delivery], notifier.chat_id, result.get("message_id"))
        sent += 1
        if pause:
            sleep(pause)
    return sent


# --- runs ---------------------------------------------------------------------------------
def run_weekly(store, gateway, embedder, ideation_config, searcher=None, mirror=None, now=None, theme=None,
               mode="economico", kind="weekly", seed=None, workers=4) -> WeeklyReport:
    """kind "weekly": the whole Sunday job; kind "ideate": the idea engine only (no mirror sync, no labels and
    no meta-review: the stored rules are used). The seed defaults to the run id, so lenses, personas and the
    serendipity pairs change from one run to the next."""
    from sotawhat.ideation.candidates import sample_candidates
    from sotawhat.ideation.engine import run_ideation

    now = now or datetime.now(timezone.utc)
    report = WeeklyReport(run_id=store.start_run(kind), day=now.date().isoformat(), kind=kind, theme=theme)
    seed = report.run_id if seed is None else seed
    if gateway is not None:
        gateway.run_id = report.run_id
    try:
        if kind == "weekly":
            if mirror is not None:
                try:
                    if mirror.ping():
                        mirror.sync(store)
                    else:
                        report.notes.append("Neo4j fora do ar: espelho não sincronizado (rode sotawhat graph sync)")
                except Exception as exc:  # noqa: BLE001 - the mirror is optional
                    report.notes.append(f"Neo4j: {type(exc).__name__}: {str(exc)[:120]}")
            report.trends = intel.trends(store, now=now)
            graph = intel.build_graph(store, now=now)
            groups = intel.communities(store, now=now, graph=graph)
            report.communities = label_communities(gateway, store, groups, report.run_id, notes=report.notes)
            report.gaps = intel.gaps(store, now=now, graph=graph, groups=groups)
            report.rules = meta_review(gateway, store, notes=report.notes)
        else:
            report.rules = json.loads(store.meta_get("ideation_rules", "[]"))
        if gateway is None:
            report.notes.append("ideação desligada: OPENROUTER_API_KEY vazio")
        else:
            candidates = sample_candidates(store, ideation_config, theme=theme, now=now, seed=seed)
            if not candidates:
                report.notes.append("nenhum par técnica × problema no grafo" + (f" para o tema {theme!r}" if theme else ""))
            else:
                report.ideation = run_ideation(store, gateway, embedder, ideation_config, candidates, report.run_id,
                                               searcher=searcher, mode=mode, seed=seed, workers=workers)
    except Exception as exc:  # noqa: BLE001 - the run must always be closed and reported
        log.exception("%s run failed", kind)
        report.ok, report.error = False, f"{type(exc).__name__}: {exc}"
    stats = {"trends": len(report.trends), "communities": len(report.communities), "theme": theme, "mode": mode,
             "ideation": report.ideation.as_dict() if report.ideation else None, "notes": report.notes}
    store.finish_run(report.run_id, ok=report.ok, stats=stats, error=report.error)
    report.cost_usd = store.conn.execute("SELECT cost_usd FROM runs WHERE id = ?", (report.run_id,)).fetchone()[0] or 0.0
    if report.ideation is not None and not report.cost_usd:
        report.cost_usd = report.ideation.cost_usd                  # a gateway that records no calls (tests)
    report.payload = build_payload(report, store)
    store.save_weekly_report(report.run_id, report.day, report.payload)
    return report


def deliver_report(settings, store, report, notify=True, notifier=None, mailer=None, pause=0.4) -> dict:
    """Files always; Telegram and e-mail unless `notify` is off. -> {"files", "telegram", "email"}."""
    from sotawhat.notify.email import EmailError
    from sotawhat.notify.email import from_settings as mailer_from
    from sotawhat.notify.telegram import TelegramError, TelegramNotifier

    payload = report.payload
    md, page = write_files(payload, settings.sotawhat_data_dir / "weekly")
    done = {"files": (md, page), "telegram": None, "email": None}
    if not notify:
        return done
    notifier = notifier or TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if notifier.configured:
        try:
            done["telegram"] = send_weekly(notifier, store, payload, report.run_id, pause=pause)
        except TelegramError as exc:
            done["telegram"] = f"erro: {exc}"
    if settings.email_enabled:
        try:
            subject, text, html = render_email(payload)
            (mailer or mailer_from(settings)).send(settings.digest_email_to, subject, text, html)
            done["email"] = "enviado"
        except EmailError as exc:
            done["email"] = f"erro: {exc}"
    return done


def _main(ns, kind) -> int:
    from sotawhat.config import load_settings
    from sotawhat.configfiles import ConfigError, load_config
    from sotawhat.graph.neo4j_sync import Neo4jMirror
    from sotawhat.ideation.config import load_ideation
    from sotawhat.ideation.prior_art import PriorArt
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient
    from sotawhat.pipeline.daily import setup_logging
    from sotawhat.store.db import Store
    from sotawhat.store.vectors import get_embedder

    settings = load_settings()
    setup_logging(settings.sotawhat_data_dir, date.today().isoformat(), settings.sotawhat_log_level)
    mode = getattr(ns, "modo", None) or "economico"
    try:
        config = load_config(settings.sotawhat_config_dir)
        ideation_config = load_ideation(settings.sotawhat_config_dir / "ideation.yaml", mode=mode)
    except ConfigError as exc:
        print(f"[config] {exc}", file=sys.stderr)
        return 2
    if getattr(ns, "n", None):
        ideation_config = scale(ideation_config, ns.n)
    mirror = None
    if kind == "weekly":
        try:
            mirror = Neo4jMirror.from_settings(settings)
        except Exception as exc:  # noqa: BLE001 - a missing driver or a bad URI must not stop the run
            print(f"[neo4j] {exc}", file=sys.stderr)
    with Store(settings.db_path) as store:
        gateway = None
        if settings.openrouter_api_key:
            client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                                      app_title=settings.openrouter_app_title)
            gateway = LLMGateway(client, store=store, settings=settings, tasks=config.llm.get("tasks"),
                                 budget_day=settings.sotawhat_llm_budget_usd_run_weekly)
        searcher = PriorArt(store=store, mailto=settings.openalex_email or settings.crossref_mailto,
                            github_token=settings.github_token, exa_key=settings.exa_api_key)
        started = time.monotonic()
        try:
            report = run_weekly(store, gateway, get_embedder(settings), ideation_config, searcher=searcher,
                                mirror=mirror, theme=getattr(ns, "tema", None), mode=mode, kind=kind)
        finally:
            if mirror is not None:
                mirror.close()
        log.info("%s run %s: %.0f s, US$ %.4f", kind, report.run_id, time.monotonic() - started, report.cost_usd)
        done = deliver_report(settings, store, report, notify=not getattr(ns, "no_notify", False))
    print(render_markdown(report.payload))
    print(f"\n[relatório] {done['files'][0]}")
    for channel in ("telegram", "email"):
        if done[channel] is not None:
            print(f"[{channel}] {done[channel]}")
    return 0 if report.ok else 1


def main_weekly(ns) -> int:
    return _main(ns, "weekly")


def main_ideate(ns) -> int:
    return _main(ns, "ideate")
