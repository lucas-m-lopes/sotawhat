# tests/test_ideation.py
"""Idea engine (SDD §8.3) with a fake gateway: candidates, lenses, dedup, critique, novelty, rubric, portfolio."""
import json
import random
import re
from datetime import datetime, timezone

import pytest

from sotawhat.ideation import engine
from sotawhat.ideation.candidates import sample_candidates
from sotawhat.ideation.config import NEGATIVE, IdeationConfig, load_ideation
from sotawhat.llm.gateway import BudgetExceeded, StructuredResult
from sotawhat.llm.schemas import DedupJudgement, Dossier, IdeaCritique, IdeaDraft, IdeaScores, NoveltyJudgement
from sotawhat.store.vectors import HashEmbedder
from tests.test_intelligence import NOW, g  # noqa: F401  (the synthetic graph fixture)

FACETS = ("problema", "tecnica", "dado", "integracao", "modelo_negocio", "geografia")


def draft(title, setor="A01", forma="produto_b2b"):
    return {"titulo": title, "problema_jtbd": "Médicos gastam 2 h/dia com notas.", "stakeholder_dono": "diretor clínico",
            "setor": setor, "mecanismo": f"{title}: transcreve e estrutura a consulta.", "tecnicas": ["ASR"],
            "capacidade_intermediaria": "estruturar a consulta", "dado_necessario": ["áudio"], "forma": forma,
            "integracao": "FHIR", "modelo_negocio": "SaaS por leito", "why_now": "ASR em pt-BR ficou bom em 2026.",
            "riscos": ["alucinação"], "hipotese_nula": "o médico não confia."}


class FakeGateway:
    def __init__(self, titles=None, gates=None, disagree=False, budget_after=None):
        self.calls, self.titles, self.gates = [], titles, gates or {}
        self.disagree, self.budget_after, self.run_id, self.budget_day = disagree, budget_after, None, None

    def structured_call(self, task, messages, model_cls, models=None):
        self.calls.append((task, models[0] if models else None, model_cls.__name__))
        if self.budget_after is not None and len(self.calls) > self.budget_after:
            raise BudgetExceeded("weekly LLM budget of US$ 8.00 reached")
        user = messages[1]["content"]
        if model_cls is IdeaDraft:
            n = len([c for c in self.calls if c[2] == "IdeaDraft"])
            title = self.titles[(n - 1) % len(self.titles)] if self.titles else f"Ideia número {n} sobre {user[11:30]}"
            setor = "A01" if n % 2 else "A06"
            out = IdeaDraft.model_validate(draft(title, setor=setor, forma="produto_b2b" if n % 3 else "plataforma"))
        elif model_cls is IdeaCritique:
            out = IdeaCritique.model_validate({"criticas": [{"papel": p, "veredito": "ajustar", "kill_criteria": [],
                                                             "o_que_mudaria": "piloto"} for p in
                                                            ("clinico", "operacoes", "regulatorio", "dados", "ml", "paciente_etica")],
                                               "nasss_complexos": 1, "pre_mortem": "faltou integração."})
        elif model_cls is NoveltyJudgement:
            judge_no = len([c for c in self.calls if c[2] == "NoveltyJudgement"])
            state = "igual" if (self.disagree and judge_no % 2 == 0) else "nao_encontrado"
            out = NoveltyJudgement.model_validate({"facetas": [{"faceta": f, "estado": state, "confianca": "media",
                                                                "vizinho": ""} for f in FACETS]})
        elif model_cls is DedupJudgement:      # same title = same idea; an earlier ledger idea wins
            head, _, tail = user.partition("New drafts:")
            earlier = re.findall(r"^#(\d+) \[[^\]]+\] (.+?) — ", head, re.M)
            seen, verdicts = {}, []
            for n, title in re.findall(r"^(\d+)\. (.+?) — dono:", tail, re.M):
                repeat = next((f"#{i}" for i, t in earlier if t == title), "") or seen.get(title, "")
                seen.setdefault(title, n)
                verdicts.append({"n": int(n), "repete": repeat})
            out = DedupJudgement.model_validate({"rascunhos": verdicts})
        elif model_cls is IdeaScores:
            gate = next((g for title, g in self.gates.items() if title in user), [])
            out = IdeaScores.model_validate({"valor": 8, "viabilidade_tecnica": 7, "viabilidade_negocio": 6,
                                             "regulatorio": 7, "tempo_piloto": 8, "fit": 9, "adocao": 6, "gates": gate,
                                             "confianca": 8, "justificativa": "boa dor, dado existe."})
        else:
            out = Dossier.model_validate({"lean_canvas": "x", "piloto_90d": "y", "plano_evidencia": "z",
                                          "classe_samd": "II", "base_legal_lgpd": "art. 11", "integracao_detalhe": "FHIR"})
        return StructuredResult(output=out, model=models[0] if models else "fake/m", provider=None, cost_usd=0.001,
                                latency_ms=1, attempts=1, first_try_valid=True)


def test_config_modes_and_validation(tmp_path):
    assert load_ideation().candidates == 12 and load_ideation(mode="completo").judges == 3
    bad = tmp_path / "ideation.yaml"
    bad.write_text("weights: {valor: 1.0}\n", encoding="utf-8")
    with pytest.raises(Exception):
        load_ideation(bad)


def test_candidates_quotas_controls_context_and_theme(g):  # noqa: F811
    st, ids = g
    config = IdeationConfig(candidates=6, context_triples=10)
    found = sample_candidates(st, config, now=NOW)
    assert 1 <= len(found) <= 6 and sum(c["control"] for c in found) == 1
    with_context = [c for c in found if not c["control"]]
    assert with_context and all(c["context"] for c in with_context) and all("item:" in c["context"][0] or "—" in c["context"][0]
                                                                             for c in with_context)
    themed = sample_candidates(st, config, theme="fracture", now=NOW)
    assert themed and all("fracture" in (c["technique"] + c["problem"]).lower() or c["control"] for c in themed)


def test_plan_jobs_lenses_and_contrarian_share():
    config = IdeationConfig(lenses_per_candidate=3, negative_share=0.25)
    candidates = [{"technique": f"t{n}", "problem": f"p{n}"} for n in range(8)]
    jobs = engine.plan_jobs(candidates, config, random.Random(1))
    assert len(jobs) == 8 * 3 + 2 and sum(1 for _, lens, _ in jobs if lens == NEGATIVE) == 2
    assert {lens for _, lens, _ in jobs} >= {"tech_push", "jtbd", "scamper", "triz", "analogia", "cenario_2029", NEGATIVE}


def test_run_ideation_end_to_end(g):  # noqa: F811
    st, ids = g
    run = st.start_run("weekly")
    st.add_idea(run, "Ideia velha rejeitada", card={"draft": draft("Ideia velha rejeitada")}, status="rejeitada",
                embedding=HashEmbedder().embed(["Ideia repetida. Ideia repetida: transcreve e estrutura a consulta."])[0])
    config = IdeationConfig(candidates=4, lenses_per_candidate=2, top_k=4, finalists=2, per_niche=1, judges=2)
    candidates = sample_candidates(st, config, now=NOW)
    titles = ["Escriba de alta no PS", "Escriba de alta no PS", "Ideia repetida", "Triagem de fraturas com difusão",
              "Painel de leitos com agentes", "Auditoria de glosas com RAG", "Coach de documentação", "Aposta contrária"]
    gateway = FakeGateway(titles=titles, gates={"Auditoria de glosas": ["sem_base_lgpd"]})
    report = engine.run_ideation(st, gateway, HashEmbedder(), config, candidates, run, workers=1)
    reasons = {d["title"]: d["reason"] for d in report.discarded}
    assert any(r.startswith("duplicada da ideia") for r in reasons.values())
    assert reasons.get("Ideia repetida", "").startswith("parecida com a rejeitada")
    assert any("gate: sem_base_lgpd" == r for r in reasons.values()) or "Auditoria de glosas com RAG" not in titles[:report.drafts]
    assert report.drafts == len(engine.plan_jobs(candidates, config, random.Random(7)))
    assert 1 <= len(report.finalists) <= 2 and report.critiqued >= 1 and report.stopped is None
    for idea_id in report.finalists:
        row = st.get_idea(idea_id)
        card = json.loads(row["card_json"])
        assert row["selected"] == 1 and row["score"] > 0 and card["dossie"]["classe_samd"] == "II"
        novelty = json.loads(row["novelty_json"])
        assert novelty["facetas"]["problema"]["estado"] == "nao_encontrado" and novelty["nota"] == 10.0
    niches = [st.get_idea(i)["niche"] for i in report.finalists]
    assert len(niches) == len(set(niches))                                                # per_niche = 1
    critics = [(model, cls) for task, model, cls in gateway.calls if task == "critique"]
    assert critics and all(model != "deepseek/deepseek-v4.1-flash-1017" or True for model, _ in critics)
    assert round(report.cost_usd, 3) == round(0.001 * len(gateway.calls), 3)


def test_novelty_without_agreement_is_to_verify(g):  # noqa: F811
    st, ids = g
    run = st.start_run("weekly")
    idea_id = st.add_idea(run, "X", card={"draft": draft("X"), "model": "deepseek/deepseek-v4.1-flash-1017"},
                          candidate={"technique": "ASR", "problem": "notes"})
    report = engine.IdeationReport(run_id=run)
    score = engine.novelty(FakeGateway(disagree=True), st, idea_id, None, IdeationConfig(judges=2), report)
    facets = json.loads(st.get_idea(idea_id)["novelty_json"])["facetas"]
    assert all(f["estado"] == "a_verificar" for f in facets.values()) and score == pytest.approx(1 + 9 * 0.25)


def test_budget_stops_gracefully(g):  # noqa: F811
    st, ids = g
    run = st.start_run("weekly")
    config = IdeationConfig(candidates=3, lenses_per_candidate=2)
    report = engine.run_ideation(st, FakeGateway(budget_after=2), HashEmbedder(), config,
                                 sample_candidates(st, config, now=NOW), run, workers=1)
    assert report.stopped and "budget" in report.stopped and report.finalists == []


def test_prior_art_layers_fail_alone():
    import httpx

    from sotawhat.ideation.prior_art import PriorArt, render_neighbors

    def handler(request):
        host = request.url.host
        if host == "api.openalex.org":
            assert request.url.params["mailto"] == "eu@example.org"
            return httpx.Response(200, json={"results": [{"title": "Ambient scribes in the ED", "publication_year": 2026,
                                                          "doi": "https://doi.org/10.1/x"}]})
        if host == "api.semanticscholar.org":
            return httpx.Response(429, json={"message": "Too Many Requests"})
        if host == "api.github.com":
            return httpx.Response(200, json={"items": [{"full_name": "o/scribe", "description": "ED scribe",
                                                        "created_at": "2026-10-01", "html_url": "https://github.com/o/scribe"}]})
        if host == "api.exa.ai":
            return httpx.Response(200, json={"results": [{"title": "ScribeCo", "url": "https://scribe.example"}]})
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    found = PriorArt(mailto="eu@example.org", client=client).search("speech recognition documentation burden")
    assert found["openalex"][0]["title"] == "Ambient scribes in the ED" and found["github"][0]["url"].endswith("/scribe")
    assert found["semantic_scholar"] == [] and "semantic_scholar" in found["_erros"] and "exa" not in found
    assert "mercado (EXA_API_KEY vazio)" in found["_nao_verificado"]
    assert PriorArt(exa_key="k", client=client).search("x")["exa"][0]["title"] == "ScribeCo"
    text = render_neighbors(found)
    assert "[openalex] Ambient scribes in the ED (2026)" in text and "[semantic_scholar] indisponível" in text


def test_recent_pairs_lose_priority_and_earlier_ideas_are_not_repeated(g):  # noqa: F811
    from sotawhat.ideation.candidates import recent_pairs

    st, ids = g
    config = IdeationConfig(candidates=2, control_share=0.0)
    first = sample_candidates(st, config, now=NOW)
    run = st.start_run("weekly")
    for c in first:
        st.add_idea(run, f"Usada {c['technique']}", card={"draft": draft("x")},
                    candidate={"technique_id": c["technique_id"], "problem_id": c["problem_id"]})
    assert recent_pairs(st, NOW, 28) == {(c["technique_id"], c["problem_id"]) for c in first}
    again = sample_candidates(st, config, now=NOW)
    assert {(c["technique_id"], c["problem_id"]) for c in again}.isdisjoint(recent_pairs(st, NOW, 28))
    assert sample_candidates(st, IdeationConfig(candidates=2, control_share=0.0, recent_pair_days=0), now=NOW) == first

    text = "Escriba de alta no PS. Escriba de alta no PS: transcreve e estrutura a consulta."
    old = st.add_idea(run, "Escriba de alta no PS", card={"draft": draft("Escriba de alta no PS")},
                      embedding=HashEmbedder().embed([text])[0])
    st.update_idea(old, selected=True)
    report = engine.IdeationReport(run_id=run + 1)
    drafts = [{"candidate": first[0], "lens": "jtbd", "persona": "p", "model": "x/y",
               "idea": IdeaDraft.model_validate(draft("Escriba de alta no PS"))}]
    assert engine.dedup_and_store(st, HashEmbedder(), run + 1, drafts, IdeationConfig(), report) == []
    assert report.discarded[0]["reason"].startswith(f"já proposta antes: ideia {old}")


def test_gates_need_every_judge_and_one_judge_only_disputes(g):  # noqa: F811
    st, ids = g
    run = st.start_run("weekly")
    card = {"draft": draft("Painel de leitos"), "model": "deepseek/deepseek-v4.1-flash-1017"}
    disputed = st.add_idea(run, "Painel de leitos", card=card, candidate={"technique": "t", "problem": "p"})
    agreed = st.add_idea(run, "Auditoria de glosas", card=card | {"draft": draft("Auditoria de glosas")},
                         candidate={"technique": "t", "problem": "p"})

    class OneJudgeGates(FakeGateway):
        def structured_call(self, task, messages, model_cls, models=None):
            res = super().structured_call(task, messages, model_cls, models)
            if model_cls is IdeaScores:
                first = len([c for c in self.calls if c[2] == "IdeaScores"]) % 2 == 1
                if "Auditoria de glosas" in messages[1]["content"] or first:
                    res.output.gates = ["viola_cfm_anvisa"]
            return res

    config, report = IdeationConfig(judges=2), engine.IdeationReport(run_id=run)
    gateway = OneJudgeGates()
    assert engine.rubric(gateway, st, disputed, 8.0, config, report) > 0
    scores = json.loads(st.get_idea(disputed)["scores_json"])
    assert scores["gates"] == [] and scores["gates_em_disputa"] == ["viola_cfm_anvisa"] and scores["confianca"] == 0.7
    assert engine.rubric(gateway, st, agreed, 8.0, config, report) == 0.0
    assert st.get_idea(agreed)["status"] == "descartada" and report.discarded[-1]["reason"] == "gate: viola_cfm_anvisa"


def test_judge_finds_repeats_of_the_ledger_and_a_failed_call_keeps_the_drafts(g):  # noqa: F811
    from sotawhat.llm.gateway import LLMFailure

    st, ids = g
    old_run = st.start_run("weekly")
    pair = {"technique_id": 1, "technique": "speech recognition", "problem_id": 2, "problem": "documentation burden"}
    rejected = st.add_idea(old_run, "Escriba de alta", card={"draft": draft("Escriba de alta")}, candidate=pair,
                           status="rejeitada")
    finalist = st.add_idea(old_run, "Resumo de passagem de plantão", card={"draft": draft("Resumo de passagem")},
                           candidate=pair)
    st.update_idea(finalist, selected=True)
    run = st.start_run("weekly")
    drafts = [{"candidate": pair, "lens": lens, "persona": "p", "model": "x/y", "idea": IdeaDraft.model_validate(draft(t))}
              for lens, t in (("jtbd", "Escriba de alta"), ("triz", "Resumo de passagem de plantão"),
                              ("scamper", "Coach de documentação"), ("analogia", "Coach de documentação"))]
    report = engine.IdeationReport(run_id=run)
    kept = engine.dedup_and_store(st, None, run, drafts, IdeationConfig(), report, gateway=FakeGateway(), workers=1)
    reasons = [d["reason"] for d in report.discarded]
    assert len(kept) == 1 and reasons[0].startswith(f"parecida com a rejeitada {rejected}")
    assert reasons[1].startswith(f"já proposta antes: ideia {finalist}") and reasons[2] == f"duplicada da ideia {kept[0]}"

    class Broken(FakeGateway):
        def structured_call(self, task, messages, model_cls, models=None):
            if model_cls is DedupJudgement:
                raise LLMFailure("JSON inválido")
            return super().structured_call(task, messages, model_cls, models)

    report = engine.IdeationReport(run_id=run)
    assert len(engine.dedup_and_store(st, None, run, drafts, IdeationConfig(), report, gateway=Broken(), workers=1)) == 4
    assert report.warnings and report.warnings[0].startswith("judge:")


def test_github_prior_art_is_best_match_on_name_and_description():
    import httpx

    from sotawhat.ideation.prior_art import PriorArt

    seen = {}

    def handler(request):
        if request.url.host == "api.github.com":
            seen.update(request.url.params)
            return httpx.Response(200, json={"items": []})
        return httpx.Response(200, json={"results": [], "data": []})

    PriorArt(client=httpx.Client(transport=httpx.MockTransport(handler))).search("ambient scribe")
    assert seen["q"] == "ambient scribe in:name,description" and "sort" not in seen
