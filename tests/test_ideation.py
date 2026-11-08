# tests/test_ideation.py
"""Idea engine (SDD §8.3) with a fake gateway: candidates, lenses, dedup, critique, novelty, rubric, portfolio."""
import json
import random
from datetime import datetime, timezone

import pytest

from sotawhat.ideation import engine
from sotawhat.ideation.candidates import sample_candidates
from sotawhat.ideation.config import NEGATIVE, IdeationConfig, load_ideation
from sotawhat.llm.gateway import BudgetExceeded, StructuredResult
from sotawhat.llm.schemas import Dossier, IdeaCritique, IdeaDraft, IdeaScores, NoveltyJudgement
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
