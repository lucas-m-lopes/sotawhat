# sotawhat/ideation/engine.py
"""The idea pipeline (SDD §8.3, stages 2–8), economic mode by default.

2. independent generation: one call per (candidate, lens, persona), model families in rotation; the
   contrarian lens covers part of every batch;
3. dedup (cosine within the batch) and memory of rejections (cosine to rejected ideas); every idea,
   kept or not, goes to the ledger with its reason;
4–5. for the `top_k` kept ideas, picked round-robin over niches: a six-role critique by a model of
   another family;
6. prior art by layers, plus a facet matrix from `judges` judges of different families; a facet without
   agreement is "a_verificar";
7. rubric by the same judges (axes 1–10, conservative aggregation, union of gates, confidence ×0.1),
   with the novelty axis from the facet matrix; any gate discards the idea;
8. portfolio selection (score, ≤ `per_niche` per niche, ≥ `min_contrarian` contrarian ideas) and a dossier
   for every finalist.
Budget errors stop the run gracefully; a failing call skips only its own step."""
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field

import numpy as np

from sotawhat import taxonomy as tx
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import Dossier, IdeaCritique, IdeaDraft, IdeaScores, NoveltyJudgement
from sotawhat.ideation.config import NEGATIVE
from sotawhat.ideation.prior_art import render_neighbors

LENS_TEXT = {
    "tech_push": "Tech-push: start from what the technique newly makes possible and find the hospital job it unlocks.",
    "jtbd": "Jobs-to-be-done / How Might We: start from the problem and its owner; phrase three \"How might we…\" "
            "questions in your head and develop the best one.",
    "scamper": "SCAMPER with the operator \"{op}\": apply it to how the problem is handled today.",
    "triz": "TRIZ: state the contradiction explicitly (improving X worsens Y) and resolve it with two inventive principles.",
    "errc": "ERRC (Blue Ocean) against the incumbent solution: what to eliminate, reduce, raise and create.",
    "analogia": "Cross-sector analogy: borrow a working mechanism from a distant sector (logistics, aviation, retail, "
                "energy, finance) at a controlled distance, and say which one.",
    "cenario_2029": "Adjacent possible: picture how this works in a Rede D'Or hospital in 2029, then work back to "
                    "what can be piloted now.",
    NEGATIVE: "Contrarian / null hypothesis: argue why the obvious product for this pair would fail, then propose the "
              "idea that survives that critique, even if it is an unpopular bet.",
}
SCAMPER = ("substituir", "combinar", "adaptar", "modificar", "dar outro uso", "eliminar", "inverter")
FACET_SCORE = {"nao_encontrado": 1.0, "parcial": 0.5, "igual": 0.0, "a_verificar": 0.25}
AXES = ("valor", "viabilidade_tecnica", "viabilidade_negocio", "regulatorio", "tempo_piloto", "fit", "adocao")


class Stop(Exception):
    """Budget or credits ran out: the run ends gracefully with what it has."""


@dataclass
class IdeationReport:
    run_id: int
    mode: str = "economico"
    candidates: int = 0
    drafts: int = 0
    kept: list = field(default_factory=list)
    critiqued: int = 0
    finalists: list = field(default_factory=list)
    discarded: list = field(default_factory=list)      # [{"id", "title", "reason"}]
    cost_usd: float = 0.0
    stopped: str | None = None
    warnings: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def family(model) -> str:
    return (model or "").split("/")[0]


def _call(gateway, task, system, user, model_cls, model, report):
    try:
        res = gateway.structured_call(task, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                                      model_cls, models=(model,) if model else None)
    except (BudgetExceeded, InsufficientCredits) as exc:
        raise Stop(str(exc)) from None
    except LLMFailure as exc:
        report.warnings.append(f"{task}: {str(exc)[:160]}")
        return None
    report.cost_usd += res.cost_usd
    return res


def _memory(store) -> tuple:
    rules = json.loads(store.meta_get("ideation_rules", "[]"))
    liked = [r["title"] for r in store.conn.execute(
        "SELECT title FROM ideas WHERE status IN ('curtida', 'testar', 'construida') ORDER BY id DESC LIMIT 6")]
    rejected = [(r["title"], r["note"] or "sem motivo") for r in store.conn.execute(
        "SELECT i.title, f.note FROM ideas i LEFT JOIN feedback f ON f.target_type = 'idea' AND f.target_id = i.id "
        "AND f.value = 'down' WHERE i.status = 'rejeitada' ORDER BY i.id DESC LIMIT 10")]
    return rules, liked, rejected


def system_for_lens(lens, persona, rules=(), liked=(), rejected=(), rng=None) -> str:
    text = LENS_TEXT[lens].format(op=(rng or random).choice(SCAMPER)) if lens == "scamper" else LENS_TEXT[lens]
    blocks = {"{{LENS}}": text, "{{PERSONA}}": persona,
              "{{RULES}}": "".join(f"- {r}\n" for r in rules),
              "{{LIKED}}": ("\n## Ideas the reader liked (do not repeat them)\n" + "".join(f"- {t}\n" for t in liked))
              if liked else "",
              "{{REJECTED}}": ("\n## Ideas the reader rejected, with the reason (avoid what they share)\n"
                               + "".join(f"- {t} — {why}\n" for t, why in rejected)) if rejected else ""}
    prompt = load_prompt("ideate_v1")
    for token, value in blocks.items():
        prompt = prompt.replace(token, value)
    return prompt


def candidate_message(candidate) -> str:
    facts = candidate.get("context") or []
    body = "\n".join(f"- {f}" for f in facts) if facts else "(sem contexto do grafo: candidato de controle)"
    return (f"Technique: {candidate['technique']} ({candidate.get('technique_type', 'technique')})\n"
            f"Problem: {candidate['problem']}\nWhy now (from the graph): {candidate.get('why_now', '?')}\n"
            f"Sampler: {candidate.get('sampler', '?')}\n\nFacts from the reader's graph:\n{body}")


def plan_jobs(candidates, config, rng) -> list:
    lenses = list(config.lenses)
    jobs = []
    for n, candidate in enumerate(candidates):
        start = (n * config.lenses_per_candidate) % len(lenses)
        chosen = [lenses[(start + k) % len(lenses)] for k in range(min(config.lenses_per_candidate, len(lenses)))]
        jobs += [(candidate, lens, rng.choice(config.personas)) for lens in chosen]
    negatives = max(1, round(len(candidates) * config.negative_share)) if candidates else 0
    for candidate in rng.sample(candidates, min(negatives, len(candidates))):
        jobs.append((candidate, NEGATIVE, rng.choice(config.personas)))
    return jobs


def generate(gateway, store, candidates, config, report, rng, workers=4) -> list:
    rules, liked, rejected = _memory(store)
    jobs = plan_jobs(candidates, config, rng)
    drafts = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for n, (candidate, lens, persona) in enumerate(jobs):
            model = config.generators[n % len(config.generators)]
            system = system_for_lens(lens, persona, rules, liked, rejected, rng)
            futures[pool.submit(_call, gateway, "ideate", system, candidate_message(candidate), IdeaDraft, model,
                                report)] = (candidate, lens, persona, model)
        for future in as_completed(futures):
            candidate, lens, persona, model = futures[future]
            if future.cancelled():
                continue
            try:
                res = future.result()
            except Stop as exc:
                report.stopped = str(exc)
                for other in futures:
                    other.cancel()
                continue
            if res is not None:
                drafts.append({"candidate": candidate, "lens": lens, "persona": persona, "model": res.model or model,
                               "idea": res.output})
    report.drafts = len(drafts)
    return drafts


def niche_of(store, draft) -> str:
    row = store.get_entity(draft["candidate"]["technique_id"])
    family_key = (row["category"] if row is not None and row["category"] else "C?")
    return f"{draft['idea'].setor}|{family_key}|{draft['idea'].forma}"


def _vectors(embedder, texts):
    if embedder is None or not texts:
        return [None] * len(texts)
    matrix = np.asarray(embedder.embed(texts), dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return list(matrix / norms)


def _closest(vector, others, threshold):
    for other_id, title, other in others:
        if other is not None and other.shape == vector.shape and float(vector @ other) >= threshold:
            return other_id, title
    return None


def dedup_and_store(store, embedder, run_id, drafts, config, report) -> list:
    """Discards a draft that repeats another draft of the batch, an idea the reader rejected, or an idea
    already delivered or decided in an earlier run (finalist, explorar, testar, engavetada, construída)."""
    texts = [f"{d['idea'].titulo}. {d['idea'].mecanismo}" for d in drafts]
    vectors = _vectors(embedder, texts)
    rejected = [(r["id"], r["title"], store.idea_embedding(r["id"])) for r in store.list_ideas(status="rejeitada", limit=500)]
    earlier = [(r["id"], r["title"], store.idea_embedding(r["id"])) for r in store.conn.execute(
        "SELECT id, title FROM ideas WHERE COALESCE(run_id, -1) != ? AND (selected = 1 OR status IN "
        "('curtida', 'testar', 'engavetada', 'construida')) ORDER BY id DESC LIMIT 500", (run_id,))]
    kept_vectors, kept = [], []
    for draft, vector in zip(drafts, vectors):
        idea, reason = draft["idea"], None
        if vector is not None:
            for other_id, other_vector in kept_vectors:
                if float(vector @ other_vector) >= config.dedup_cosine:
                    reason = f"duplicada da ideia {other_id}"
                    break
            if reason is None and (hit := _closest(vector, rejected, config.rejected_cosine)):
                reason = f"parecida com a rejeitada {hit[0]} ({hit[1][:60]})"
            if reason is None and (hit := _closest(vector, earlier, config.dedup_cosine)):
                reason = f"já proposta antes: ideia {hit[0]} ({hit[1][:60]})"
        idea_id = store.add_idea(run_id, idea.titulo, card={"draft": idea.model_dump(), "model": draft["model"]},
                                 lens=draft["lens"], persona=draft["persona"], niche=niche_of(store, draft),
                                 candidate={k: v for k, v in draft["candidate"].items() if k != "context"}
                                 | {"context": draft["candidate"].get("context", [])[:12]},
                                 embedding=vector, status="descartada" if reason else "nova")
        if reason:
            store.update_idea(idea_id, discard_reason=reason)
            report.discarded.append({"id": idea_id, "title": idea.titulo, "reason": reason})
        else:
            kept_vectors.append((idea_id, vector)) if vector is not None else None
            kept.append(idea_id)
    report.kept = kept
    return kept


def preselect(store, idea_ids, top_k) -> list:
    by_niche = {}
    for idea_id in idea_ids:
        by_niche.setdefault(store.get_idea(idea_id)["niche"], []).append(idea_id)
    queues, picked = list(by_niche.values()), []
    while len(picked) < top_k and any(queues):
        for queue in queues:
            if queue and len(picked) < top_k:
                picked.append(queue.pop(0))
    return picked


def _idea_text(row) -> str:
    card = json.loads(row["card_json"])
    draft = card["draft"]
    return (f"Título: {draft['titulo']}\nProblema: {draft['problema_jtbd']}\nDono: {draft['stakeholder_dono']}\n"
            f"Setor: {draft['setor']} {tx.label(draft['setor'])}\nMecanismo: {draft['mecanismo']}\n"
            f"Técnicas: {', '.join(draft['tecnicas'])}\nCapacidade: {draft['capacidade_intermediaria']}\n"
            f"Dados: {', '.join(draft['dado_necessario'])}\nForma: {draft['forma']} · integração {draft['integracao']}\n"
            f"Modelo de negócio: {draft['modelo_negocio']}\nPor que agora: {draft['why_now']}\n"
            f"Riscos: {'; '.join(draft['riscos'])}\nHipótese nula: {draft['hipotese_nula']}")


def _other_family(models, generator) -> str:
    return next((m for m in models if family(m) != family(generator)), models[0])


def critique(gateway, store, idea_ids, config, report) -> None:
    system = load_prompt("critique_v1")
    for idea_id in idea_ids:
        row = store.get_idea(idea_id)
        critic = _other_family(config.judge_models, json.loads(row["card_json"]).get("model", ""))
        res = _call(gateway, "critique", system, _idea_text(row), IdeaCritique, critic, report)
        if res is not None:
            store.update_idea(idea_id, critique=res.output.model_dump() | {"modelo": res.model})
            report.critiqued += 1


def _judges(config, generator) -> list:
    ordered = [m for m in config.judge_models if family(m) != family(generator)] + \
              [m for m in config.judge_models if family(m) == family(generator)]
    return ordered[:max(1, config.judges)]


def novelty(gateway, store, idea_id, searcher, config, report) -> float:
    row = store.get_idea(idea_id)
    candidate = json.loads(row["candidate_json"] or "{}")
    found = searcher.search(f"{candidate.get('technique', '')} {candidate.get('problem', '')}".strip()) if searcher else {}
    user = f"{_idea_text(row)}\n\nPrior art:\n{render_neighbors(found) if found else '(busca desligada)'}"
    verdicts = []
    for judge in _judges(config, json.loads(row["card_json"]).get("model", "")):
        res = _call(gateway, "judge", load_prompt("novelty_v1"), user, NoveltyJudgement, judge, report)
        if res is not None:
            verdicts.append({f.faceta: f for f in res.output.facetas})
    facets = {}
    for facet in ("problema", "tecnica", "dado", "integracao", "modelo_negocio", "geografia"):
        states = [v[facet].estado for v in verdicts if facet in v]
        agreed = states and all(s == states[0] for s in states) and (len(states) >= 2 or config.judges == 1)
        facets[facet] = {"estado": states[0] if agreed else "a_verificar",
                         "vizinhos": sorted({v[facet].vizinho for v in verdicts if facet in v and v[facet].vizinho})}
    score = 1 + 9 * sum(FACET_SCORE[f["estado"]] for f in facets.values()) / len(facets)
    store.update_idea(idea_id, novelty={"camadas": {k: v for k, v in found.items()}, "facetas": facets,
                                        "nota": round(score, 2)})
    return score


def rubric(gateway, store, idea_id, novelty_score, config, report):
    row = store.get_idea(idea_id)
    critique_json = json.loads(row["critique_json"] or "{}")
    novelty_json = json.loads(row["novelty_json"] or "{}")
    user = (f"{_idea_text(row)}\n\nCritique:\n{json.dumps(critique_json, ensure_ascii=False)[:3000]}\n\n"
            f"Prior art facets:\n{json.dumps(novelty_json.get('facetas', {}), ensure_ascii=False)}")
    scores = []
    for judge in _judges(config, json.loads(row["card_json"]).get("model", "")):
        res = _call(gateway, "judge", load_prompt("score_v1"), user, IdeaScores, judge, report)
        if res is not None:
            scores.append(res.output)
    if not scores:
        return None
    axes = {}
    for axis in AXES:
        values = [getattr(s, axis) for s in scores]
        axes[axis] = min(values) if max(values) - min(values) > 3 else sum(values) / len(values)
    axes["novidade"] = round(novelty_score, 2)
    gates = sorted({g for s in scores for g in s.gates})
    confidence = min(s.confianca for s in scores) / 10
    vetoes = sum(1 for c in critique_json.get("criticas", []) if c.get("veredito") == "descartar")
    if critique_json.get("nasss_complexos", 0) >= 3:
        confidence = max(0.5, confidence - 0.1)          # NASSS gate: three or more complex domains demote
    total = sum(config.weights[axis] * value for axis, value in axes.items()) * confidence
    if vetoes >= 3:
        total *= 0.8
    final = 0.0 if gates else round(total, 2)
    store.update_idea(idea_id, scores={"eixos": axes, "gates": gates, "confianca": confidence, "vetos": vetoes,
                                       "justificativas": [s.justificativa for s in scores]}, score=final)
    if gates:
        store.update_idea(idea_id, status="descartada", discard_reason="gate: " + ", ".join(gates))
        report.discarded.append({"id": idea_id, "title": row["title"], "reason": "gate: " + ", ".join(gates)})
    return final


def select(store, scored, config) -> list:
    ranked = sorted((i for i, s in scored.items() if s and s > 0), key=lambda i: -scored[i])
    chosen, per_niche = [], {}
    for idea_id in ranked:
        niche = store.get_idea(idea_id)["niche"]
        if per_niche.get(niche, 0) >= config.per_niche:
            continue
        chosen.append(idea_id)
        per_niche[niche] = per_niche.get(niche, 0) + 1
        if len(chosen) >= config.finalists:
            break
    contrarian = [i for i in chosen if store.get_idea(i)["lens"] == NEGATIVE]
    if len(contrarian) < config.min_contrarian:
        extra = next((i for i in ranked if i not in chosen and store.get_idea(i)["lens"] == NEGATIVE), None)
        if extra is not None:
            if len(chosen) >= config.finalists:
                chosen.pop()
            chosen.append(extra)
    return chosen


def dossier(gateway, store, idea_id, config, report) -> None:
    row = store.get_idea(idea_id)
    res = _call(gateway, "synth", load_prompt("dossier_v1"), _idea_text(row), Dossier, config.judge_models[0], report)
    if res is not None:
        card = json.loads(row["card_json"])
        card["dossie"] = res.output.model_dump()
        store.update_idea(idea_id, card=card)


def run_ideation(store, gateway, embedder, config, candidates, run_id, searcher=None, mode="economico",
                 seed=7, workers=4) -> IdeationReport:
    report = IdeationReport(run_id=run_id, mode=mode, candidates=len(candidates))
    rng = random.Random(seed)
    try:
        drafts = generate(gateway, store, candidates, config, report, rng, workers=workers)
        if report.stopped:
            raise Stop(report.stopped)
        kept = dedup_and_store(store, embedder, run_id, drafts, config, report)
        top = preselect(store, kept, config.top_k)
        critique(gateway, store, top, config, report)
        scored = {}
        for idea_id in top:
            scored[idea_id] = rubric(gateway, store, idea_id, novelty(gateway, store, idea_id, searcher, config, report),
                                     config, report)
        finalists = select(store, scored, config)
        for idea_id in finalists:
            dossier(gateway, store, idea_id, config, report)
            store.update_idea(idea_id, selected=True)
        report.finalists = finalists
    except Stop as exc:
        report.stopped = str(exc)
    return report
