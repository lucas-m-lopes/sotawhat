"""HyperFrames lessons: ElevenLabs alignment, storyboard validation, timing of actions and captions."""
import json

import pytest

from sotawhat.lessons import eleven
from sotawhat.lessons import hyperframes as hfm
from sotawhat.lessons.motion import spoken_decimals, two_digits
from sotawhat.lessons.storyboard import (Action, Axes, Bar, Column, Edge, Event, FormulaPart, Node, Patches, Row,
                                         SceneBoard, Series, Step, Storyboard, Vector3D, Volume, clean_narration, cue_in,
                                         roc_points, trapezoid, validate)


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


# --- ElevenLabs credits -------------------------------------------------------------------------------------------
def _speech_client(text, headers=None):
    import base64
    import httpx

    def handler(request):
        return httpx.Response(200, headers=headers or {}, json={
            "audio_base64": base64.b64encode(b"ID3").decode(), "alignment": alignment(text)})
    return httpx.Client(base_url=eleven.API, transport=httpx.MockTransport(handler))


def test_credits_come_from_the_response_header_or_the_characters_sent():
    text = "O token chega."
    _, _, credits = eleven.ElevenLabs("k", client=_speech_client(text, {"character-cost": "16"})).speak(text)
    assert credits == 16
    _, _, credits = eleven.ElevenLabs("k", client=_speech_client(text)).speak(text)
    assert credits == len(text)
    assert eleven.credits_usd(2730) == 0.455 and eleven.credits_usd(100, 22, 121000) == 0.0182


class _FakeEleven:
    def __init__(self):
        self.calls = 0

    def speak(self, text, *args, **kw):
        self.calls += 1
        return b"ID3", alignment(text), len(text) + 3


def _fake_wav(monkeypatch):
    def to_wav(ffmpeg, mp3, wav, lead_in=0.35):
        eleven.silence(wav, 1.0)
        return 1.0
    monkeypatch.setattr(eleven, "to_wav", to_wav)


def test_scene_cache_keeps_what_the_generation_cost(tmp_path, monkeypatch):
    _fake_wav(monkeypatch)
    el, sentences = _FakeEleven(), ["O token chega.", "Vira vetor."]
    first = eleven.speak_scene(el, sentences, tmp_path, "ffmpeg", "cena01")
    again = eleven.speak_scene(el, sentences, tmp_path, "ffmpeg", "cena01")
    assert el.calls == 1 and (first.cached, again.cached) == (False, True)
    assert first.credits == again.credits == len(" ".join(sentences)) + 3
    # the first cache files hold the alignment alone: their cost is the characters
    old = tmp_path / "old"
    old.mkdir()
    key = eleven.cache_key("Fim.", eleven.DEFAULT_VOICE, eleven.DEFAULT_MODEL, eleven.SETTINGS)
    (old / f"cena02-{key}.mp3").write_bytes(b"ID3")
    (old / f"cena02-{key}.json").write_text(json.dumps(alignment("Fim.")), encoding="utf-8")
    assert eleven.speak_scene(el, ["Fim."], old, "ffmpeg", "cena02").credits == 4 and el.calls == 1


def test_narration_bills_only_the_scenes_it_generated(tmp_path, monkeypatch):
    _fake_wav(monkeypatch)
    el = _FakeEleven()
    eleven.speak_scene(el, ["Uma cena pronta."], tmp_path, "ffmpeg", "cena01")
    nar = eleven.narrate(el, [["Uma cena pronta."], ["Outra nova."]], tmp_path, "ffmpeg", intro=1.0, progress=lambda *_: None)
    assert nar.billed_chars == len("Outra nova.") + 3
    assert nar.credits == len("Uma cena pronta.") + 3 + len("Outra nova.") + 3


# --- storyboard v2: chart, timeline, compare, volume3d --------------------------------------------------------------


def test_a_roc_curve_is_drawn_from_its_auc():
    pts = roc_points(0.94)
    assert pts[0] == [0.0, 0.0] and pts[-1] == [1.0, 1.0]
    assert all(b[1] >= a[1] for a, b in zip(pts, pts[1:]))              # a ROC never goes down
    assert abs(trapezoid(pts) - 0.94) < 0.015
    scene = _scene(template="chart", axes=Axes(x_label="1 − especificidade", y_label="sensibilidade", x_min=0,
                                               x_max=1, y_min=0, y_max=1),
                   series=[Series(id="roc", label="modelo", role="info", points=[[0.5, 0.2]], auc=0.94)],
                   steps=[Step(beat=0, actions=[_act("show", ["roc"]), _act("area", ["roc"], text="AUC 0,94")])])
    assert validate(Storyboard(scenes=[scene]), [["A curva sobe rápido."]]) == []
    assert len(scene.series[0].points) == 15


def test_chart_points_are_sorted_and_kept_inside_the_axes():
    scene = _scene(template="chart", axes=Axes(x_label="dados", y_label="erro", x_min=0, x_max=0, y_min=0, y_max=0),
                   series=[Series(id="a", label="treino", role="query", points=[[3, 0.2], [1, 0.9], [2, 0.4], [2, 0.5],
                                                                               [4]], auc=0)],
                   steps=[Step(beat=0, actions=[_act("show", ["a"])])])
    assert validate(Storyboard(scenes=[scene]), [["O erro cai."]]) == []
    assert scene.series[0].points == [[1, 0.9], [2, 0.5], [3, 0.2]]          # sorted, one y per x, pairs only
    ax = scene.axes
    assert (ax.x_min, ax.x_max, ax.y_min, ax.y_max) == (1, 3, 0.0, 0.9)        # derived from the points
    bad = _scene(template="chart", series=[Series(id="b", label="x", role="query", points=[[1, 1]], auc=0)])
    assert any("chart precisa" in p for p in validate(Storyboard(scenes=[bad]), [["Uma frase."]]))


def test_compare_cells_follow_the_columns_and_timelines_need_two_events():
    scene = _scene(template="compare", columns=[Column(id="cnn", title="convolução", role="value"),
                                                Column(id="vit", title="atenção", role="query")],
                   rows=[Row(id="campo", label="campo de visão", cells=["local"]),
                         Row(id="dados", label="dados", cells=["poucos", "muitos", "demais"])],
                   steps=[Step(beat=0, actions=[_act("show", ["cnn", "vit"]), _act("pick", ["campo", "vit"])])])
    assert validate(Storyboard(scenes=[scene]), [["A atenção vê tudo."]]) == []
    assert [r.cells for r in scene.rows] == [["local", ""], ["poucos", "muitos"]]
    lone = _scene(template="timeline", events=[Event(id="e1", when="1972", label="primeira TC", gloss="", role="info")])
    assert any("timeline precisa" in p for p in validate(Storyboard(scenes=[lone]), [["Em 1972."]]))


def test_volume_defaults_and_the_planned_template_is_required():
    scene = _scene(template="volume3d", volume=Volume(organ="nenhum", finding="nódulo", modality="nenhuma", slices=0),
                   steps=[Step(beat=0, actions=[_act("slice", value=1.7)])])
    problems = validate(Storyboard(scenes=[scene]), [["O corte passa."]], planned=["chart"])
    assert problems == ["cena 1: use o modelo de cena do plano, chart (veio volume3d)"]
    assert (scene.volume.organ, scene.volume.modality, scene.volume.slices) == ("corpo", "tomografia", 16)
    assert scene.steps[0].actions[0].value == 1.0


def test_storyboards_of_the_first_prototype_still_load():
    old = {"scene": 1, "template": "graph", "nodes": [], "edges": [], "bars": [], "vectors": [], "formula": [],
           "patches": {"image": "nenhuma", "rows": 0, "cols": 0, "focus_row": 0, "focus_col": 0}, "steps": []}
    board = SceneBoard.model_validate(old)
    assert board.series == [] and board.volume.organ == "nenhum"


# --- lessons learned from lesson 7 -----------------------------------------------------------------------------------
def test_a_bulk_show_waits_for_each_part_to_be_named():
    bars = [Bar(id=i, label=i, value=v, role="score") for i, v in (("ar", -1000), ("agua", 0), ("osso", 1200))]
    scene = _scene(template="bars", bars=bars, steps=[
        Step(beat=0, actions=[_act("show", ["ar", "agua", "osso"], cue="voxel")]),
        Step(beat=1, actions=[_act("show", ["ar"], cue="ar"), _act("show", ["agua"], cue="água")]),
        Step(beat=2, actions=[_act("show", ["osso"], cue="osso")])])
    validate(Storyboard(scenes=[scene]), [["Cada voxel guarda um número.", "O ar e a água.", "O osso."]])
    assert scene.steps[0].actions == []                    # emptied, so dropped: an empty show would mean all
    assert [a.ids for a in scene.steps[1].actions] == [["ar"], ["agua"]]


def test_a_note_that_repeats_the_screen_is_dropped():
    node = Node(id="p", label="projeções", kind="box", role="query", col=0, row=0, panel=1, gloss="perfis de atenuação",
                values=[])
    scene = _scene(nodes=[node], steps=[Step(beat=0, actions=[_act("show", ["p"]), _act("note", ["p"], text="perfis de atenuação")]),
                                        Step(beat=1, actions=[_act("note", ["p"], text="medidos em cada ângulo")])])
    validate(Storyboard(scenes=[scene]), [["A primeira peça.", "Medida em cada ângulo."]])
    assert [a.do for a in scene.steps[0].actions] == ["show"] and scene.steps[1].actions[0].text == "medidos em cada ângulo"


def test_a_focus_lasts_its_sentence_except_the_last_one():
    words = [{"text": "Um", "start": 1.0, "end": 1.2, "beat": 0}, {"text": "Dois", "start": 3.0, "end": 3.2, "beat": 1},
             {"text": "Três", "start": 5.0, "end": 5.2, "beat": 2}]
    nar_scene = {"start": 0.0, "end": 6.0, "beats": [(1.0, 1.2), (3.0, 3.2), (5.0, 5.2)], "words": words}
    scene = _scene(steps=[Step(beat=0, actions=[_act("focus", ["q"])]), Step(beat=1, actions=[_act("pulse", ["q"])]),
                          Step(beat=2, actions=[_act("focus", ["q"])])])
    acts = hfm.scene_actions(scene, nar_scene, slot_start=0.0)
    assert [a["do"] for a in acts] == ["focus", "unfocus", "pulse", "focus"]
    assert acts[1]["t"] == pytest.approx(3.0 - 0.3)       # released in the pause before the next sentence
