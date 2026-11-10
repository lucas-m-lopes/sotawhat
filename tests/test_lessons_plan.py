# tests/test_lessons_plan.py
"""Lessons: the source pack, the storyboard lint (G2), the planner's repair round and the fact gate (G1)."""
from sotawhat.lessons.pack import Pack, Source, build_pack, pack_markdown, pack_prompt, pick_topic
from sotawhat.lessons.plan import (Beat, FactCheck, FactProblem, LessonPlan, MotionPlan, MotionScene, QuizItem, Scene,
                                   Term, check_facts, estimate_seconds, lint, load_plan, make_plan, revise_plan, slug)
from tests.test_graph_query import g  # noqa: F401 - the graph fixture

SENTENCE = " ".join(["palavra"] * 18)          # 18 words, ~10 s of narration


def plan_with(scenes=7, beats=4, three=0, quiz=4, source=0) -> LessonPlan:
    items = []
    for n in range(scenes):
        mode = "three" if n < three else "manim"
        items.append(Scene(title=f"Cena {n}", mode=mode, why_3d="a geometria do tomógrafo é espacial" if mode == "three"
                           else "", goal="entender", beats=[Beat(narration=SENTENCE, visual="aparece", source=source)
                                                            for _ in range(beats)], labels=[Term(term="Q", gloss_pt="consulta")]))
    return LessonPlan(title="Atenção", process="atenção", objective="entender a atenção",
                      prerequisites=[Term(term=t, gloss_pt=t) for t in ("Q", "K", "V")], scenes=items,
                      quiz=[QuizItem(question="Por quê?", options=["a", "b", "c"], answer=1, explanation="porque",
                                     source=-1) for _ in range(quiz)])


class FakeGateway:
    def __init__(self, *outputs):
        self.outputs, self.calls = list(outputs), []

    def structured(self, task, messages, model, models=None):
        self.calls.append((task, messages, models))
        return self.outputs.pop(0)


def test_lint_accepts_a_good_plan_and_names_each_problem():
    good = plan_with()
    assert 150 <= estimate_seconds(good) <= 390 and lint(good, n_sources=2) == []
    bad = plan_with(scenes=4, three=1, quiz=2, source=5)
    bad.scenes[0].why_3d = ""
    bad.scenes[1].beats = bad.scenes[1].beats * 2                                    # 8 beats, ~80 s
    bad.quiz[0].answer = 7
    problems = "\n".join(lint(bad, n_sources=2))
    for expected in ("4 cenas", "3D sem justificativa", "cena 2 dura", "fonte 5 não existe", "quiz tem 2",
                     "quiz 1: a resposta 7"):
        assert expected in problems


def test_make_plan_repairs_once_then_sanitizes():
    first, second = plan_with(scenes=3), plan_with(source=9)
    gw = FakeGateway(first, second)
    plan, problems = make_plan(gw, Pack(topic="Atenção", sources=[]))
    assert len(gw.calls) == 2 and "Corrija" in gw.calls[1][1][-1]["content"] and "3 cenas" in gw.calls[1][1][-1]["content"]
    assert problems == [] and all(b.source == -1 for s in plan.scenes for b in s.beats)   # sanitized: no sources


def test_fact_gate_keeps_known_sentences_and_revises():
    plan = plan_with()
    pack = Pack(topic="Atenção", sources=[Source(0, "url:x", "Attention", "https://x", "2026-11-01", "resumo", "texto")])
    gw = FakeGateway(FactCheck(problems=[FactProblem(sentence="c1f2", issue="número sem fonte"),
                                         FactProblem(sentence="c99f1", issue="inventado")]))
    problems = check_facts(gw, plan, pack)
    assert [p.sentence for p in problems] == ["c1f2"]
    user = gw.calls[0][1][1]["content"]
    assert "c1f1 [fonte 0]" in user and "quiz1 [fonte -1]" in user and "[0] Attention" in user
    revised = plan_with()
    revised.title = "Atenção revisada"
    gw2 = FakeGateway(revised)
    plan2, lint_problems = revise_plan(gw2, plan, pack, problems)
    assert plan2.title == "Atenção revisada" and lint_problems == [] and "c1f2: número sem fonte" in gw2.calls[0][1][-1]["content"]


def test_cjk_in_the_plan_is_refused():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Beat(narration="O modelo 潜在 aprende.", visual="x", source=-1)


def test_pack_from_the_graph_and_its_markdown(g):  # noqa: F811
    st, ids = g
    pack = build_pack(st, "MedGemma", [ids["med"]])
    assert [e["name"] for e in pack.entities] == ["MedGemma 1.5"]
    assert [s.title for s in pack.sources] == ["MedGemma reads CT volumes", "Old radiology news"]   # main role first
    assert pack.sources[0].text == "text" and pack.sources[0].summary_pt.startswith("Resumo")
    assert "Google" in pack.neighbors and "MedGemma 1.5" not in pack.neighbors
    assert "[0] MedGemma reads CT volumes" in pack_prompt(pack)
    assert Pack.from_json(pack.to_json()) == pack
    by_search = build_pack(st, "medgemma")                                          # entity found by name
    assert by_search.entities and by_search.sources
    nothing = build_pack(st, "radiology")                                           # no entity: matching items
    assert [s.title for s in nothing.sources] == ["Old radiology news"]
    md = pack_markdown(pack, plan_with())
    assert md.startswith("# Atenção") and "## [0] MedGemma reads CT volumes" in md and "Video Overview" in md
    assert slug("Atenção no Transformer!") == "atencao-no-transformer"


def test_pick_topic_skips_taught_and_non_process_entities(g):  # noqa: F811
    st, ids = g
    assert pick_topic(st) is None                                                   # no weekly report yet
    run = st.start_run("weekly")
    st.save_weekly_report(run, "2026-11-09", {"trends": [
        {"entity_id": ids["google"], "name": "Google", "type": "organization", "z": 9},
        {"entity_id": ids["med"], "name": "MedGemma 1.5", "type": "model", "z": 5},
        {"entity_id": ids["fract"], "name": "missed fracture", "type": "problem", "z": 4}]})
    assert pick_topic(st, min_sources=2) == ("MedGemma 1.5", [ids["med"]])
    st.create_lesson("MedGemma", [ids["med"]])
    assert pick_topic(st, min_sources=1) == ("missed fracture", [ids["fract"]])


# --- the HyperFrames plan: each scene names its kit template ------------------------------------------------------
def motion_plan_with(templates=("graph",) * 7, beats=4, example="o token nódulo; scores 8, 24 e 4") -> MotionPlan:
    scenes = [MotionScene(title=f"Cena {n}", template=t, goal="entender", labels=[Term(term="Q", gloss_pt="consulta")],
                          beats=[Beat(narration=SENTENCE, visual="aparece", source=0) for _ in range(beats)])
              for n, t in enumerate(templates)]
    return MotionPlan(title="Atenção", process="atenção", objective="entender a atenção", example=example,
                      prerequisites=[Term(term=t, gloss_pt=t) for t in ("Q", "K", "V")], scenes=scenes,
                      quiz=[QuizItem(question="Por quê?", options=["a", "b", "c"], answer=1, explanation="porque",
                                     source=-1) for _ in range(4)])


def test_motion_plan_lint_counts_3d_scenes_and_wants_the_example():
    assert lint(motion_plan_with(("graph", "bars", "chart", "vectors3d", "volume3d", "compare", "graph")), 2) == []
    problems = " | ".join(lint(motion_plan_with(("graph", "vectors3d", "vectors3d", "vectors3d", "volume3d", "bars",
                                                  "graph")), 2))
    assert "no máximo 3 cenas em 3D" in problems and "3 cenas vectors3d" in problems
    assert any("example" in p for p in lint(motion_plan_with(example=""), 2))
    staged = motion_plan_with()
    staged.scenes[1].beats[0].narration = "Limpa a tela. " + SENTENCE
    assert any("c2f1" in p and "instrução de palco" in p for p in lint(staged, 2))


def test_load_plan_reads_both_engines():
    motion = load_plan(motion_plan_with(("graph", "volume3d") + ("graph",) * 5).model_dump_json())
    assert isinstance(motion, MotionPlan) and [s.mode for s in motion.scenes[:2]] == ["manim", "three"]
    assert isinstance(load_plan(plan_with().model_dump()), LessonPlan)


def test_the_motion_planner_gets_the_template_prompt_and_repairs_with_it():
    gw = FakeGateway(motion_plan_with(example=""), motion_plan_with())
    plan, problems = make_plan(gw, Pack(topic="Atenção", sources=[Source(0, "u", "t", "", "", "", "")]),
                               schema=MotionPlan)
    assert isinstance(plan, MotionPlan) and problems == [] and len(gw.calls) == 2
    assert "Scene templates" in gw.calls[0][1][0]["content"] and "example" in gw.calls[1][1][-1]["content"]
    gw2 = FakeGateway(motion_plan_with())
    revise_plan(gw2, plan, Pack(topic="Atenção", sources=[]), [FactProblem(sentence="c1f1", issue="x")])
    assert "Scene templates" in gw2.calls[0][1][0]["content"]
