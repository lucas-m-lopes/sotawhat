"""HyperFrames lessons: ElevenLabs alignment, storyboard validation, timing of actions and captions."""
import pytest

from sotawhat.lessons import eleven
from sotawhat.lessons import hyperframes as hfm
from sotawhat.lessons.motion import spoken_decimals, two_digits
from sotawhat.lessons.storyboard import (Action, Bar, Edge, FormulaPart, Node, Patches, SceneBoard, Step, Storyboard,
                                         Vector3D, clean_narration, cue_in, validate)


def alignment(text, step=0.1):
    return {"characters": list(text), "character_start_times_seconds": [i * step for i in range(len(text))],
            "character_end_times_seconds": [i * step + step for i in range(len(text))]}


def test_beats_and_words_come_from_the_character_times():
    sentences = ["O token chega.", "Vira vetor."]
    al = alignment(" ".join(sentences))
    beats = eleven.beat_times(al, sentences)
    assert beats[0] == pytest.approx((0.0, 1.3))          # "O" .. "a" of chega, the full stop is skipped
    assert beats[1][0] == pytest.approx(1.5)              # "V" of Vira, after "chega. "
    words = eleven.word_times(al, sentences)
    assert [w["text"] for w in words] == ["O", "token", "chega.", "Vira", "vetor."]
    assert words[2]["end"] == pytest.approx(1.3) and words[3]["beat"] == 1


def test_alignment_that_does_not_match_the_text_is_refused():
    with pytest.raises(eleven.ElevenError):
        eleven.beat_times(alignment("outro texto"), ["O token chega."])


def test_cache_key_changes_with_voice_and_text():
    a = eleven.cache_key("frase", "v1", "m", {"s": 1})
    assert a == eleven.cache_key("frase", "v1", "m", {"s": 1})
    assert a != eleven.cache_key("frase", "v2", "m", {"s": 1}) != eleven.cache_key("outra", "v1", "m", {"s": 1})


def test_stage_directions_and_digit_readings_are_cleaned():
    assert clean_narration("Limpa a tela. Os scores viram números.") == "Os scores viram números."
    assert spoken_decimals("área de zero vírgula nove quatro.") == "área de zero vírgula noventa e quatro."
    assert spoken_decimals("zero vírgula cinco") == "zero vírgula cinco"
    assert [two_digits(n) for n in (7, 12, 40, 94)] == ["sete", "doze", "quarenta", "noventa e quatro"]


def test_cue_must_be_a_word_of_the_sentence():
    assert cue_in("Query", "A query azul pergunta.")
    assert cue_in("", "qualquer")
    assert not cue_in("softmax", "A query azul pergunta.")


def _act(do, ids=(), cue="", text="", value=0.0):
    return Action(do=do, ids=list(ids), text=text, value=value, cue=cue)


def _node(i, col=0, row=0):
    return Node(id=i, label=i, kind="box", role="query", col=col, row=row, panel=1, gloss="", values=[1.0])


def _scene(**kw):
    base = dict(scene=1, template="graph", nodes=[], edges=[], bars=[], vectors=[], formula=[],
                patches=Patches(image="nenhuma", rows=0, cols=0, focus_row=0, focus_col=0), steps=[])
    base.update(kw)
    return SceneBoard(**base)


def test_validate_repairs_links_cues_and_steps():
    scene = _scene(nodes=[_node("a"), _node("b", col=1)],
                   edges=[Edge(id="ab", source="a", target="b", label="", role="query")],
                   steps=[Step(beat=0, actions=[_act("show", ["ab"], cue="inexistente")])])
    board = Storyboard(scenes=[scene])
    problems = validate(board, [["A liga B.", "Fim."]])
    assert problems == []
    show = board.scenes[0].steps[0].actions[0]
    assert set(show.ids) == {"ab", "a", "b"}               # a link never appears before its ends
    assert show.cue == ""                                  # a cue that is not in the sentence is dropped
    assert len(board.scenes[0].steps) == 2                 # one step per sentence
    assert board.scenes[0].nodes[0].values == []           # values only on vectors


def test_validate_reports_unknown_ids_and_bad_links():
    scene = _scene(nodes=[_node("a")], edges=[Edge(id="x", source="a", target="z", label="", role="key")],
                   steps=[Step(beat=0, actions=[_act("focus", ["fantasma"])])])
    problems = validate(Storyboard(scenes=[scene]), [["Uma frase."]])
    assert any("ligação x" in p for p in problems) and any("fantasma" in p for p in problems)


def test_bars_take_the_dot_products_of_the_3d_scene():
    vec = _scene(template="vectors3d", vectors=[
        Vector3D(id="q", label="query", role="query", x=2, y=2, z=2),
        Vector3D(id="kb", label="key benigno", role="key", x=4, y=4, z=4),
        Vector3D(id="km", label="key mama", role="key", x=2, y=0, z=0)],
        steps=[Step(beat=0, actions=[_act("show")])])
    bars = _scene(scene=2, template="bars", bars=[Bar(id="b", label="benigno", value=1, role="score"),
                                                  Bar(id="m", label="mama", value=1, role="score")],
                  steps=[Step(beat=0, actions=[_act("show")])])
    board = Storyboard(scenes=[vec, bars])
    validate(board, [["Compara."], ["Mostra."]])
    assert [b.value for b in board.scenes[1].bars] == [24.0, 4.0]


def test_patch_grid_is_at_least_three_by_three():
    scene = _scene(template="patches", patches=Patches(image="ultrassom", rows=2, cols=2, focus_row=5, focus_col=1),
                   steps=[Step(beat=0, actions=[_act("tokenize")])])
    board = Storyboard(scenes=[scene])
    assert validate(board, [["Cada pedaço vira token."]]) == []
    p = board.scenes[0].patches
    assert (p.rows, p.cols, p.focus_row) == (3, 3, 2)


def test_actions_start_at_their_cue_word_and_captions_follow_the_words():
    words = [{"text": "A", "start": 10.0, "end": 10.1, "beat": 0}, {"text": "query", "start": 10.2, "end": 10.6, "beat": 0},
             {"text": "pergunta.", "start": 10.7, "end": 11.2, "beat": 0}, {"text": "Fim.", "start": 11.8, "end": 12.1, "beat": 1}]
    nar_scene = {"start": 9.65, "end": 12.4, "beats": [(10.0, 11.2), (11.8, 12.1)], "words": words}
    scene = _scene(steps=[Step(beat=0, actions=[_act("show", ["q"], cue="query")]), Step(beat=1, actions=[_act("pulse", ["q"])])])
    acts = hfm.scene_actions(scene, nar_scene, slot_start=9.65)
    assert acts[0]["t"] == pytest.approx(10.2 - 0.12 - 9.65)
    assert acts[1]["t"] == pytest.approx(11.8 - 0.12 - 9.65)
    assert acts[0]["until"] == pytest.approx(11.8 - 9.65)
    groups = hfm.caption_groups(words)
    assert [len(g["words"]) for g in groups] == [3, 1]     # a sentence end closes the group
    assert groups[0]["end"] <= groups[1]["start"]


def test_slots_run_from_one_scene_to_the_next():
    nar = {"duration": 30.0, "scenes": [{"start": 3.2, "end": 12.0}, {"start": 12.7, "end": 28.8}]}
    assert hfm.slots(nar) == [(3.2, 9.5), (12.7, 17.3)]


def test_formula_parts_are_kept_in_the_schema():
    part = FormulaPart(id="qk", tex="q \\cdot k")
    assert part.model_dump() == {"id": "qk", "tex": "q \\cdot k"}
