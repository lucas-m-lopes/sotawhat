# sotawhat/lessons/plan.py
"""The lesson plan (storyboard): the schema the LLM fills, the deterministic lint (gate G2), the planner with one
repair round, and the fact gate (G1): every sentence is checked against the source it cites, and a sentence
marked as canonical knowledge (-1) cannot carry a number, a date or a company. One revision round follows."""
import re
import unicodedata
from typing import Literal

from pydantic import Field

from sotawhat.lessons.pack import pack_prompt
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import _Portuguese

PLAN_PROMPT, FACTS_PROMPT = "lesson_plan_v1", "lesson_facts_v1"
_SLUG = re.compile(r"[^a-z0-9]+")
CHARS_PER_SECOND = 15.0       # pt-BR narration (Piper faber: 166 characters in 10.6 s)
PAUSE_S = 0.45                # between sentences
MIN_S, MAX_S = 150, 390       # 2.5–6.5 min
MAX_SCENE_S, MAX_THREE = 60, 3


class Term(_Portuguese):
    term: str = Field(description="o termo como aparece na tela (pode ficar em inglês)")
    gloss_pt: str = Field(description="glosa curta em português")


class Beat(_Portuguese):
    narration: str = Field(description="uma frase em pt-BR com 8 a 28 palavras")
    visual: str = Field(description="o que aparece, muda ou é destacado enquanto a frase é dita")
    source: int = Field(description="índice da fonte que sustenta a frase; -1 = conhecimento canônico")


class Scene(_Portuguese):
    title: str = Field(description="título curto da cena, mostrado na tela")
    mode: Literal["manim", "three"]
    why_3d: str = Field(description="vazio no manim; no three, por que o conteúdo é espacial")
    goal: str = Field(description="o que o aluno entende ao fim da cena")
    beats: list[Beat]
    labels: list[Term]


class QuizItem(_Portuguese):
    question: str
    options: list[str] = Field(description="3 ou 4 alternativas curtas")
    answer: int = Field(description="índice da alternativa correta")
    explanation: str = Field(description="por que a resposta está certa, em uma frase")
    source: int = Field(description="índice da fonte, ou -1")


class LessonPlan(_Portuguese):
    title: str = Field(description="título da aula, até 60 caracteres")
    process: str = Field(description="o processo mais complexo do tema, que a aula explica")
    objective: str = Field(description="o que você vai entender ao fim da aula, em uma frase")
    prerequisites: list[Term]
    scenes: list[Scene]
    quiz: list[QuizItem]


class FactProblem(_Portuguese):
    sentence: str = Field(description="id da frase, como c2f3")
    issue: str = Field(description="o que está errado e como corrigir, em português")


class FactCheck(_Portuguese):
    problems: list[FactProblem]


def beat_seconds(text) -> float:
    return len(text) / CHARS_PER_SECOND + PAUSE_S


def estimate_seconds(plan) -> float:
    return sum(beat_seconds(b.narration) for s in plan.scenes for b in s.beats)


def lint(plan, n_sources) -> list:
    """Gate G2: the problems of a plan, in Portuguese (they go back to the planner as they are)."""
    problems = []
    total = estimate_seconds(plan)
    if not MIN_S <= total <= MAX_S:
        problems.append(f"a narração dura ~{total:.0f} s; a aula deve ter entre {MIN_S} e {MAX_S} s")
    if not 5 <= len(plan.scenes) <= 10:
        problems.append(f"a aula tem {len(plan.scenes)} cenas; use de 6 a 9")
    if not 2 <= len(plan.prerequisites) <= 6:
        problems.append("liste de 3 a 5 pré-requisitos (termos que a primeira cena apresenta)")
    if sum(s.mode == "three" for s in plan.scenes) > MAX_THREE:
        problems.append(f"no máximo {MAX_THREE} cenas em 3D")
    for n, scene in enumerate(plan.scenes, 1):
        if not 2 <= len(scene.beats) <= 8:
            problems.append(f"cena {n} tem {len(scene.beats)} frases; use de 3 a 6")
        seconds = sum(beat_seconds(b.narration) for b in scene.beats)
        if seconds > MAX_SCENE_S:
            problems.append(f"cena {n} dura ~{seconds:.0f} s; divida em cenas de até 50 s")
        if scene.mode == "three" and len(scene.why_3d.strip()) < 10:
            problems.append(f"cena {n} é 3D sem justificativa espacial em why_3d; use manim ou justifique")
        for k, beat in enumerate(scene.beats, 1):
            words = len(beat.narration.split())
            if not 5 <= words <= 40:
                problems.append(f"c{n}f{k}: a frase tem {words} palavras; use de 8 a 28")
            if not -1 <= beat.source < n_sources:
                problems.append(f"c{n}f{k}: fonte {beat.source} não existe (use -1 a {n_sources - 1})")
    if not 3 <= len(plan.quiz) <= 5:
        problems.append(f"o quiz tem {len(plan.quiz)} perguntas; use de 3 a 5")
    for n, item in enumerate(plan.quiz, 1):
        if not 3 <= len(item.options) <= 4 or len(set(item.options)) != len(item.options):
            problems.append(f"quiz {n}: use 3 ou 4 alternativas diferentes")
        if not 0 <= item.answer < len(item.options):
            problems.append(f"quiz {n}: a resposta {item.answer} não é uma alternativa")
    return problems


def sanitize(plan, n_sources):
    """What can be fixed without the LLM after the repair round: out-of-range sources become canonical (-1) and
    broken quiz questions are dropped."""
    for scene in plan.scenes:
        for beat in scene.beats:
            if not -1 <= beat.source < n_sources:
                beat.source = -1
    plan.quiz = [q for q in plan.quiz if 3 <= len(q.options) <= 4 and 0 <= q.answer < len(q.options)
                 and len(set(q.options)) == len(q.options)]
    return plan


def make_plan(gateway, pack, models=None):
    """-> (plan, remaining lint problems). One repair round when the lint finds problems."""
    messages = [{"role": "system", "content": load_prompt(PLAN_PROMPT)},
                {"role": "user", "content": pack_prompt(pack)}]
    plan = gateway.structured("lesson_plan", messages, LessonPlan, models=models)
    problems = lint(plan, len(pack.sources))
    if problems:
        messages += [{"role": "assistant", "content": plan.model_dump_json()},
                     {"role": "user", "content": "Corrija estes problemas e devolva o plano inteiro:\n- "
                                                 + "\n- ".join(problems)}]
        plan = gateway.structured("lesson_plan", messages, LessonPlan, models=models)
    plan = sanitize(plan, len(pack.sources))
    return plan, lint(plan, len(pack.sources))


def sentences(plan) -> list:
    """[(id, beat)] with ids like c2f3 (scene 2, sentence 3)."""
    return [(f"c{n}f{k}", beat) for n, scene in enumerate(plan.scenes, 1) for k, beat in enumerate(scene.beats, 1)]


def check_facts(gateway, plan, pack) -> list:
    """Gate G1 -> [FactProblem]."""
    lines = [f"{sid} [fonte {b.source}] {b.narration}" for sid, b in sentences(plan)]
    lines += [f"quiz{n} [fonte {item.source}] {item.question} → {item.options[item.answer]}"
              for n, item in enumerate(plan.quiz, 1) if 0 <= item.answer < len(item.options)]
    user = "Frases:\n" + "\n".join(lines) + "\n\n" + pack_prompt(pack)
    out = gateway.structured("lesson_facts", [{"role": "system", "content": load_prompt(FACTS_PROMPT)},
                                              {"role": "user", "content": user}], FactCheck)
    known = {sid for sid, _ in sentences(plan)} | {f"quiz{n}" for n in range(1, len(plan.quiz) + 1)}
    return [p for p in out.problems if p.sentence in known]


def revise_plan(gateway, plan, pack, problems, models=None):
    """One revision round for the fact problems -> (plan, lint problems)."""
    messages = [{"role": "system", "content": load_prompt(PLAN_PROMPT)},
                {"role": "user", "content": pack_prompt(pack)},
                {"role": "assistant", "content": plan.model_dump_json()},
                {"role": "user", "content": "A checagem de fatos encontrou estes problemas. Reescreva só o necessário "
                                            "(ou retire a afirmação) e devolva o plano inteiro:\n- "
                                            + "\n- ".join(f"{p.sentence}: {p.issue}" for p in problems)}]
    plan = sanitize(gateway.structured("lesson_plan", messages, LessonPlan, models=models), len(pack.sources))
    return plan, lint(plan, len(pack.sources))


def slug(text) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return _SLUG.sub("-", plain).strip("-")[:50] or "aula"
