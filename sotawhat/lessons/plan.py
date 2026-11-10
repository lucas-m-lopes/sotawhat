# sotawhat/lessons/plan.py
"""The lesson plan: the schema the LLM fills, the deterministic lint (gate G2), the planner with one repair round,
and the fact gate (G1): every sentence is checked against the source it cites, and a sentence marked as canonical
knowledge (-1) cannot carry a number, a date or a company. One revision round follows.

Two formats: `MotionPlan` (HyperFrames engine, every lesson made since 2026-11-10: each scene names the kit
template that shows it, and one worked example with its numbers travels through the lesson) and `LessonPlan`
(the Manim engine of lessons 1–5, kept so they can still be resumed). `load_plan` reads either."""
import json
import re
import unicodedata
from typing import Literal

from pydantic import Field

from sotawhat.lessons.pack import pack_prompt
from sotawhat.lessons.storyboard import TEMPLATES, TEMPLATES_3D
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import _Portuguese

PLAN_PROMPT, MOTION_PROMPT, FACTS_PROMPT = "lesson_plan_v2", "lesson_plan_v3", "lesson_facts_v1"
_STAGE = re.compile(r"\blimp(a|e|amos)\s+a\s+tela\b", re.I)   # "Limpa a tela." was read aloud in lesson 4
_READ_ONLY = re.compile(r"[:;()—–\"“”/]")     # punctuation that reads well but sounds bad
_SLUG = re.compile(r"[^a-z0-9]+")
CHARS_PER_SECOND = 15.0       # pt-BR narration (Piper faber: 166 characters in 10.6 s)
PAUSE_S = 0.45                # between sentences
MIN_S, MAX_S = 150, 390       # 2.5–6.5 min
MAX_SCENE_S, MAX_THREE = 60, 3
MAX_3D, MAX_EACH_3D = 3, 2    # HyperFrames: scenes in vectors3d or volume3d


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


class MotionScene(_Portuguese):
    title: str = Field(description="título curto da cena, mostrado na tela")
    template: Literal[TEMPLATES] = Field(description="o modelo de cena do kit que mostra este passo")
    goal: str = Field(description="o que o aluno entende ao fim da cena")
    beats: list[Beat]
    labels: list[Term]

    @property
    def mode(self) -> str:          # what the Manim-era code and pages read
        return "three" if self.template in TEMPLATES_3D else "manim"


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


class MotionPlan(_Portuguese):
    title: str = Field(description="título da aula, até 60 caracteres")
    process: str = Field(description="o processo mais complexo do tema, que a aula explica")
    objective: str = Field(description="o que você vai entender ao fim da aula, em uma frase")
    example: str = Field(description="o exemplo único que atravessa a aula, com os números que aparecem nas cenas")
    prerequisites: list[Term]
    scenes: list[MotionScene]
    quiz: list[QuizItem]


def load_plan(data):
    """A stored plan of either engine -> MotionPlan (HyperFrames) or LessonPlan (Manim)."""
    if isinstance(data, (str, bytes)):
        data = json.loads(data)
    scenes = data.get("scenes") or []
    return (MotionPlan if scenes and "template" in scenes[0] else LessonPlan).model_validate(data)


def prompt_for(plan_cls) -> str:
    return MOTION_PROMPT if plan_cls is MotionPlan else PLAN_PROMPT


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
    motion = isinstance(plan, MotionPlan)
    if motion:
        used = [s.template for s in plan.scenes]
        if sum(t in TEMPLATES_3D for t in used) > MAX_3D:
            problems.append(f"no máximo {MAX_3D} cenas em 3D (vectors3d e volume3d)")
        for t in TEMPLATES_3D:
            if used.count(t) > MAX_EACH_3D:
                problems.append(f"{used.count(t)} cenas {t}; use no máximo {MAX_EACH_3D}")
        if len(plan.example.strip()) < 10:
            problems.append("preencha example com o exemplo que atravessa a aula e os seus números")
    elif sum(s.mode == "three" for s in plan.scenes) > MAX_THREE:
        problems.append(f"no máximo {MAX_THREE} cenas em 3D")
    for n, scene in enumerate(plan.scenes, 1):
        if not 2 <= len(scene.beats) <= 8:
            problems.append(f"cena {n} tem {len(scene.beats)} frases; use de 3 a 6")
        seconds = sum(beat_seconds(b.narration) for b in scene.beats)
        if seconds > MAX_SCENE_S:
            problems.append(f"cena {n} dura ~{seconds:.0f} s; divida em cenas de até 50 s")
        if not motion and scene.mode == "three" and len(scene.why_3d.strip()) < 10:
            problems.append(f"cena {n} é 3D sem justificativa espacial em why_3d; use manim ou justifique")
        for k, beat in enumerate(scene.beats, 1):
            words = len(beat.narration.split())
            if not 5 <= words <= 30:
                problems.append(f"c{n}f{k}: a frase tem {words} palavras; use de 8 a 22")
            if _STAGE.search(beat.narration):
                problems.append(f"c{n}f{k}: tire da narração a instrução de palco (o que muda na tela vai em visual)")
            if _READ_ONLY.search(beat.narration) or beat.narration.count(",") > 2:
                problems.append(f"c{n}f{k}: frase escrita para ler, não para ouvir; tire dois-pontos, ponto e vírgula, "
                                "travessão, parênteses, aspas e barras, e use no máximo uma vírgula")
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


def make_plan(gateway, pack, models=None, schema=None):
    """-> (plan, remaining lint problems). One repair round when the lint finds problems. `schema`: MotionPlan for
    the HyperFrames engine, LessonPlan (the default) for the Manim one."""
    schema = schema or LessonPlan
    messages = [{"role": "system", "content": load_prompt(prompt_for(schema))},
                {"role": "user", "content": pack_prompt(pack)}]
    plan = gateway.structured("lesson_plan", messages, schema, models=models)
    problems = lint(plan, len(pack.sources))
    if problems:
        messages += [{"role": "assistant", "content": plan.model_dump_json()},
                     {"role": "user", "content": "Corrija estes problemas e devolva o plano inteiro:\n- "
                                                 + "\n- ".join(problems)}]
        plan = gateway.structured("lesson_plan", messages, schema, models=models)
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
    schema = type(plan)
    messages = [{"role": "system", "content": load_prompt(prompt_for(schema))},
                {"role": "user", "content": pack_prompt(pack)},
                {"role": "assistant", "content": plan.model_dump_json()},
                {"role": "user", "content": "A checagem de fatos encontrou estes problemas. Reescreva só o necessário "
                                            "(ou retire a afirmação) e devolva o plano inteiro:\n- "
                                            + "\n- ".join(f"{p.sentence}: {p.issue}" for p in problems)}]
    plan = sanitize(gateway.structured("lesson_plan", messages, schema, models=models), len(pack.sources))
    return plan, lint(plan, len(pack.sources))


def slug(text) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return _SLUG.sub("-", plain).strip("-")[:50] or "aula"
