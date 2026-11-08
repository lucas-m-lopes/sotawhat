# tests/test_weekly.py
"""`run weekly` and `ideate` (SDD §6.1, §8): labels, meta-review, report files, Telegram idea votes, CLI."""
import json
import re
from types import SimpleNamespace

from sotawhat.cli import parse_args
from sotawhat.ideation.config import IdeationConfig, load_ideation
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure, StructuredResult
from sotawhat.llm.schemas import CommunityLabel, MetaReview
from sotawhat.pipeline import weekly
from sotawhat.pipeline.deliver import item_key
from sotawhat.pipeline.feedback import handle_update
from sotawhat.store.vectors import HashEmbedder
from tests.test_feedback import FakeBot
from tests.test_ideation import FakeGateway
from tests.test_intelligence import NOW, g  # noqa: F401  (the synthetic graph fixture)

SMALL = IdeationConfig(candidates=3, lenses_per_candidate=2, top_k=3, finalists=2, per_niche=2, judges=2)


def _result(out):
    return StructuredResult(output=out, model="fake/m", provider=None, cost_usd=0.001, latency_ms=1, attempts=1,
                            first_try_valid=True)


class WeeklyGateway(FakeGateway):
    """FakeGateway plus the two weekly outputs; `fail_labels` makes every label call fail."""

    def __init__(self, fail_labels=None, **kwargs):
        super().__init__(**kwargs)
        self.fail_labels, self.users = fail_labels, []

    def structured_call(self, task, messages, model_cls, models=None):
        if model_cls is CommunityLabel:
            self.calls.append((task, None, "CommunityLabel"))
            if self.fail_labels:
                raise self.fail_labels
            return _result(CommunityLabel(rotulo=f"Grupo {len(self.calls)}", resumo="Reúne técnicas & problemas."))
        if model_cls is MetaReview:
            self.calls.append((task, None, "MetaReview"))
            self.users.append(messages[1]["content"])
            return _result(MetaReview(regras=["prefere operações de UTI", " ", "rejeita wearable próprio"]))
        return super().structured_call(task, messages, model_cls, models)


class FakeMirror:
    def __init__(self, up=True):
        self.up, self.synced = up, 0

    def ping(self):
        return self.up

    def sync(self, store):
        self.synced += 1


def test_scale_keeps_the_mode_and_sets_n():
    config = weekly.scale(load_ideation(mode="completo"), 4)
    assert (config.candidates, config.finalists, config.top_k, config.judges, config.lenses_per_candidate) == (4, 4, 6, 3, 5)


def test_run_weekly_end_to_end(g, tmp_path):  # noqa: F811
    st, ids = g
    old = st.start_run("weekly")
    for n, (value, note) in enumerate([("down", "já existe"), ("up", None), ("test", None), ("archive", None)]):
        idea = st.add_idea(old, f"Antiga {n}", card={"draft": {}}, lens="jtbd", niche="A01|C?|produto_b2b")
        st.vote_idea(idea, value, "web", note=note)
    gateway, mirror = WeeklyGateway(), FakeMirror()
    report = weekly.run_weekly(st, gateway, HashEmbedder(), SMALL, mirror=mirror, now=NOW, workers=1)
    assert report.ok and report.kind == "weekly" and mirror.synced == 1
    assert report.trends and report.trends[0]["name"] in ("speech recognition", "agentic RAG")
    assert len(report.communities) == 2 and report.communities[0]["label"].startswith("Grupo")
    stored = st.latest_communities()
    assert [r["label"] for r in stored] == [c["label"] for c in report.communities]
    assert st.entity_community(ids["missed fracture"]) == st.entity_community(ids["diffusion model"])
    assert report.rules == ["prefere operações de UTI", "rejeita wearable próprio"]
    assert json.loads(st.meta_get("ideation_rules")) == report.rules and "reason: já existe" in gateway.users[0]
    assert report.ideation is not None and 1 <= len(report.ideation.finalists) <= 2
    run = st.conn.execute("SELECT * FROM runs WHERE id = ?", (report.run_id,)).fetchone()
    assert run["kind"] == "weekly" and run["ok"] == 1 and json.loads(run["stats_json"])["ideation"]["finalists"]
    saved = st.latest_weekly_report()
    assert saved["run_id"] == report.run_id and saved["payload"]["ideas"][0]["dossie"]["classe_samd"] == "II"
    payload = report.payload
    assert payload["stats"]["cost_usd"] == round(0.001 * len([c for c in gateway.calls
                                                              if c[2] not in ("CommunityLabel", "MetaReview")]), 4)

    md, page = weekly.write_files(payload, tmp_path / "weekly")
    assert md.name == "2026-11-08-semana.md" and page.exists()
    text = md.read_text(encoding="utf-8")
    for section in ("## Ideias", "## Em alta", "## Mapa da semana", "## Lacunas", "## Regras do meta-review"):
        assert section in text
    assert "Piloto de 90 dias" in text and re.search(r"A0[16] (documentação clínica|emergência/triagem)", text)
    assert "não encontrado: problema, técnica, dado, integração, modelo de negócio, geografia/BR" in text
    assert "speech recognition (técnica)" in text or "agentic RAG (técnica)" in text
    html = page.read_text(encoding="utf-8")
    assert "<article" in html and "técnicas &amp; problemas" in html and "<script" not in html
    subject, plain, mail = weekly.render_email(payload)
    assert subject.startswith("sotawhat · semana 2026-11-08 ·") and 'style="' in mail and "<style" not in mail


def test_idea_votes_on_telegram(g):  # noqa: F811
    st, ids = g
    report = weekly.run_weekly(st, WeeklyGateway(), HashEmbedder(), SMALL, now=NOW, kind="ideate", workers=1)
    bot = FakeBot()
    sent = weekly.send_weekly(bot, st, report.payload, report.run_id, pause=0)
    finalists = report.ideation.finalists
    assert sent == 1 + len(finalists) and bot.sent[0][1] is None
    text, markup, silent = bot.sent[1]
    assert silent and [b["text"] for b in markup["inline_keyboard"][0]] == ["👍 explorar", "👎", "🧪 testar", "🗄️ engavetar"]
    key = item_key(f"idea:{finalists[0]}")
    assert markup["inline_keyboard"][0][3]["callback_data"] == f"f:{key}:a"
    vote = {"update_id": 3, "callback_query": {"id": "c1", "from": {"id": 42}, "data": f"f:{key}:a",
                                               "message": {"message_id": 102, "chat": {"id": 42}}}}
    assert handle_update(st, bot, vote, "42") == "vote"
    assert st.get_idea(finalists[0])["status"] == "engavetada" and bot.answers == ["ideia: engavetada"]
    assert bot.edits[0][2]["inline_keyboard"][0][3]["text"] == "✅🗄️ engavetar"
    feedback = st.conn.execute("SELECT * FROM feedback WHERE target_type = 'idea'").fetchone()
    assert (feedback["target_id"], feedback["value"], feedback["channel"]) == (str(finalists[0]), "archive", "telegram")


def test_archive_is_only_for_ideas(g):  # noqa: F811
    st, ids = g
    run = st.start_run("daily")
    st.record_delivery(run, "2026-11-08", "pmid:1", item_key("pmid:1"), "main", 1)
    bot = FakeBot()
    vote = {"update_id": 4, "callback_query": {"id": "c2", "from": {"id": 42}, "data": f"f:{item_key('pmid:1')}:a"}}
    assert handle_update(st, bot, vote, "42") == "ignored" and bot.answers == ["opção só vale para ideias"]
    assert st.item_votes() == {}


def test_ideate_skips_labels_and_meta_review_and_names_the_file(g, tmp_path):  # noqa: F811
    st, ids = g
    st.meta_set("ideation_rules", json.dumps(["evita wearables"]))
    gateway = WeeklyGateway()
    report = weekly.run_weekly(st, gateway, HashEmbedder(), SMALL, now=NOW, kind="ideate", theme="fracture", workers=1)
    assert report.ok and report.rules == ["evita wearables"] and report.communities == [] and report.trends == []
    assert not [c for c in gateway.calls if c[2] in ("CommunityLabel", "MetaReview")]
    assert report.payload["ideas"] and all("fracture" in (i["candidate"]["technique"] + i["candidate"]["problem"]).lower()
                                           for i in report.payload["ideas"])
    md, _ = weekly.write_files(report.payload, tmp_path)
    assert md.name == f"2026-11-08-ideias-{report.run_id}.md" and "tema “fracture”" in md.read_text(encoding="utf-8")
    none = weekly.run_weekly(st, gateway, HashEmbedder(), SMALL, now=NOW, kind="ideate", theme="xyzzy", workers=1)
    assert none.ok and none.ideation is None and "para o tema 'xyzzy'" in none.notes[0]


def test_failures_degrade_gracefully(g):  # noqa: F811
    st, ids = g
    report = weekly.run_weekly(st, WeeklyGateway(fail_labels=LLMFailure("schema inválido")), HashEmbedder(), SMALL,
                               mirror=FakeMirror(up=False), now=NOW, workers=1)
    assert report.ok and "Neo4j fora do ar" in report.notes[0]
    assert report.communities[0]["label"].count(" · ") == 2 and any("rótulo da comunidade 0" in n for n in report.notes)
    stopped = weekly.run_weekly(st, WeeklyGateway(fail_labels=BudgetExceeded("weekly LLM budget"), budget_after=0),
                                HashEmbedder(), SMALL, now=NOW, workers=1)
    labels = [c for c in stopped.notes if c.startswith("rótulos das comunidades interrompidos")]
    assert stopped.ok and len(labels) == 1 and stopped.ideation.stopped and stopped.payload["ideas"] == []
    assert "ideação interrompida" in weekly.render_markdown(stopped.payload)
    off = weekly.run_weekly(st, None, HashEmbedder(), SMALL, now=NOW, workers=1)
    assert off.ok and off.ideation is None and "OPENROUTER_API_KEY" in off.notes[-1] and off.communities


def test_telegram_text_is_clipped_before_escaping():
    idea = {"id": 9, "title": "A & B " * 80, "lens": "jtbd", "score": 7.5, "draft": {"setor": "A06", "forma": "plataforma",
            "problema_jtbd": "<" * 900, "mecanismo": "m", "why_now": "w", "hipotese_nula": "h"},
            "facets": {}, "dossie": None}
    payload = {"kind": "ideate", "day": "2026-11-08", "theme": None, "trends": [], "communities": [], "ideas": [idea],
               "stats": {"drafts": 3, "cost_usd": 0.01, "stopped": None}, "notes": [], "error": None}
    messages = weekly.telegram_messages(payload)
    text = messages[1]["text"]
    assert messages[1]["idea"] == 9 and len(text) < 4096 and "&l…" not in text and text.count("&lt;") == 399


def test_deliver_report_files_telegram_and_email(g, tmp_path):  # noqa: F811
    st, ids = g
    report = weekly.run_weekly(st, WeeklyGateway(), HashEmbedder(), SMALL, now=NOW, kind="ideate", workers=1)
    sent = []
    mailer = SimpleNamespace(send=lambda to, subject, text, html: sent.append((to, subject)))
    settings = SimpleNamespace(sotawhat_data_dir=tmp_path, email_enabled=True, digest_email_to="eu@example.org")
    bot = FakeBot()
    bot.configured = True
    done = weekly.deliver_report(settings, st, report, notifier=bot, mailer=mailer, pause=0)
    assert done["files"][0].exists() and done["telegram"] == 1 + len(report.ideation.finalists)
    assert done["email"] == "enviado" and sent[0][0] == "eu@example.org"
    quiet = weekly.deliver_report(settings, st, report, notify=False, notifier=bot, mailer=mailer)
    assert quiet["telegram"] is None and len(sent) == 1


def test_cli_parses_weekly_and_ideate():
    ns = parse_args(["run", "weekly", "--modo", "completo", "--no-notify"])
    assert (ns.command, ns.kind, ns.modo, ns.no_notify) == ("run", "weekly", "completo", True)
    ns = parse_args(["ideate", "--tema", "UTI", "--n", "4"])
    assert (ns.command, ns.tema, ns.n, ns.modo, ns.no_notify) == ("ideate", "UTI", 4, "economico", False)
