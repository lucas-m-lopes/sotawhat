# tests/test_lessons_quality.py
"""Lessons after the pilot feedback (2026-11-09): speech written for the ear and shaped pauses, the visual review
(G4) with fixes shown the frames, and the kit's layout check on the real Manim (arrows left behind, arrows before
their target)."""
import wave

import numpy as np
import pytest

from sotawhat.lessons import coder
from sotawhat.lessons import render as rd
from sotawhat.lessons.voice import shape_pauses, speech_text
from tests.test_lessons import GOOD_PY, _plan


# --- speech ------------------------------------------------------------------------------------------------------
def test_speech_text_rewrites_for_the_ear():
    glossary = [{"term": "query", "spoken": "kuéri"}, {"term": "key", "spoken": "qui"}, {"term": "value", "spoken": "véliu"}]
    assert speech_text("São três peças: Query-Key-Value; a IA usa a TC (tomografia).", glossary) == \
        "São três peças, kuéri-qui-véliu. A i á usa a tê cê, tomografia."
    assert speech_text("Reduziu 30% — cerca de 2,86x menos, AUC ≈ 0,94 no SUS") == \
        "Reduziu 30 por cento, cerca de 2,86 vezes menos, á u cê cerca de 0,94 no SUS."
    assert speech_text("o “banco” de sangue...") == "O banco de sangue."


def test_shape_pauses_lengthens_commas_and_trims_the_edges(tmp_path):
    rate = 22050

    def tone(s):
        return (np.sin(np.arange(int(s * rate)) * 0.3) * 8000).astype(np.int16)

    def gap(s):
        return np.zeros(int(s * rate), dtype=np.int16)

    pieces = [gap(0.3), tone(0.5), gap(0.05), tone(0.3), gap(0.14), tone(0.5), gap(0.5)]   # plosive, comma, tail
    with wave.open(str(tmp_path / "x.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.concatenate(pieces).tobytes())
    seconds = shape_pauses(tmp_path / "x.wav")
    # head (0.3 s) and tail (0.5 s) trimmed to small margins; the 0.14 s comma becomes 0.24 s; the 0.05 s gap stays
    assert 1.55 < seconds < 1.75, seconds


# --- visual review (G4) ------------------------------------------------------------------------------------------
def _fake_frames(tools, video, durations, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / f"f{k}.jpg" for k in range(1, len(durations) + 1)]
    for p in paths:
        p.write_bytes(b"\xff\xd8jpeg")
    return paths


def test_visual_review_fixes_serious_defects_with_the_frames(tmp_path, monkeypatch):
    renders = []

    def fake_manim(tools, scene_dir, kit_dir, cache_dir, lenient=False, **kw):
        renders.append((scene_dir / "scene.py").read_text(encoding="utf-8"))
        (scene_dir / "out.mp4").write_bytes(b"v%d" % len(renders))

    monkeypatch.setattr(rd, "render_manim", fake_manim)
    monkeypatch.setattr(coder, "frames_of", _fake_frames)

    class Gateway:
        def __init__(self):
            self.calls = []
            self.reviews = [[{"frame": 2, "kind": "seta_solta", "where": "seta à direita", "fix": "use connect",
                              "severity": "grave"}],
                            [{"frame": 1, "kind": "ilegivel", "where": "rótulo", "fix": "aumente", "severity": "leve"}]]

        def structured(self, task, messages, model, models=None):
            self.calls.append((task, messages, models))
            if task == "lesson_critic":
                return coder.VisualReview.model_validate({"defects": self.reviews.pop(0)})
            return coder.SceneCode(code=GOOD_PY if len(self.calls) == 1 else GOOD_PY.replace("Atenção", "Atenção 2"))

    gw = Gateway()
    report = coder.build_scene(gw, None, tmp_path, tmp_path / "s1", tmp_path, tmp_path, _plan(), 1, [2.0, 3.0],
                               log=lambda *_: None)
    assert [c[0] for c in gw.calls] == ["lesson_code", "lesson_critic", "lesson_fix", "lesson_critic"]
    fix = gw.calls[2]
    content = fix[1][-1]["content"]
    assert fix[2] == coder.VISUAL_FIX and isinstance(content, list)                            # it sees the frames
    assert "quadro 2 (seta_solta)" in content[0]["text"] and content[1]["type"] == "image_url"
    assert report["visual_fixes"] == 1 and len(report["visual"]) == 2 and "Atenção 2" in renders[-1]
    critic = gw.calls[1][1][1]["content"]
    assert critic[0]["text"].startswith("Cena: C1") and len(critic) == 3                      # text + 2 frames


def test_a_visual_fix_that_breaks_the_scene_keeps_the_good_version(tmp_path, monkeypatch):
    def fake_manim(tools, scene_dir, kit_dir, cache_dir, lenient=False, **kw):
        if "quebrado" in (scene_dir / "scene.py").read_text(encoding="utf-8"):
            raise rd.RenderError("LayoutError: frase 1: ...")
        (scene_dir / "out.mp4").write_bytes(b"bom")

    monkeypatch.setattr(rd, "render_manim", fake_manim)
    monkeypatch.setattr(coder, "frames_of", _fake_frames)
    monkeypatch.setattr(coder, "review", lambda gateway, frames, scene: [coder.VisualDefect(
        frame=1, kind="sobreposicao", where="x", fix="y", severity="grave")])
    codes = [GOOD_PY, GOOD_PY + "# quebrado\n"]

    class Gateway:
        def structured(self, task, messages, model, models=None):
            return coder.SceneCode(code=codes.pop(0))

    report = coder.build_scene(Gateway(), None, tmp_path, tmp_path / "s1", tmp_path, tmp_path, _plan(), 1, [2.0, 3.0],
                               log=lambda *_: None)
    assert report["ok"] and report["visual_fixes"] == 0 and "correção visual" in report["errors"][-1]
    assert (tmp_path / "s1" / "out.mp4").read_bytes() == b"bom"
    assert "quebrado" not in (tmp_path / "s1" / "scene.py").read_text(encoding="utf-8")


# --- the kit's layout check on the real Manim (only where the tools are installed) -------------------------------
def _tools():
    from sotawhat.config import load_settings
    from sotawhat.lessons.tools import Tools

    tools = Tools.from_settings(load_settings(_env_file=None))
    return tools if tools.status()["python"] else None


LEFT_BEHIND = """from lesson_kit import *


class Cena(LessonScene):
    def construct(self):
        a, b = box("A").move_to([-3, 0, 0]), box("B").move_to([3, 0, 0])
        seta = Arrow(a.get_right(), b.get_left(), buff=0.1)
        self.beat(FadeIn(a), FadeIn(b), GrowArrow(seta))
        self.beat(FadeOut(b))
"""
TOO_EARLY = """from lesson_kit import *


class Cena(LessonScene):
    def construct(self):
        a, b = box("A").move_to([-3, 0, 0]), box("B").move_to([3, 0, 0])
        self.beat(FadeIn(a), GrowArrow(Arrow(a.get_right(), b.get_left(), buff=0.1)))
        self.beat(FadeIn(b))
"""
CLEAN = """from lesson_kit import *


class Cena(LessonScene):
    def construct(self):
        self.add(title("Fluxo"))
        steps, links = flow(box("token"), box("embedding"), box("atenção"))
        at(steps, "center")
        self.beat(FadeIn(steps[0]), FadeIn(steps[1]), GrowArrow(links[0]))
        self.beat(FadeIn(steps[2]), GrowArrow(links[1]))
        self.beat(*self.clear_stage(), FadeIn(at(box("nova ideia", color=C_GREEN), "center")))
"""


@pytest.mark.parametrize("code, beats, expected", [(LEFT_BEHIND, 2, "ficou na tela"),
                                                   (TOO_EARLY, 2, "apareceu antes do alvo"),
                                                   (CLEAN, 3, None)])
def test_kit_layout_check_on_manim(tmp_path, code, beats, expected):
    tools = _tools()
    if tools is None:
        pytest.skip("ferramentas das aulas não instaladas (sotawhat lessons setup)")
    from sotawhat.lessons.tools import KIT

    scene_dir = tmp_path / "cena"
    scene_dir.mkdir()
    (scene_dir / "scene.py").write_text(code, encoding="utf-8")
    rd.write_beats(scene_dir, ["Um.", "Dois.", "Três."][:beats], [0.6] * beats)
    if expected is None:
        rd.render_manim(tools, scene_dir, KIT, tmp_path / "cache")
        assert (scene_dir / "out.mp4").exists()
    else:
        with pytest.raises(rd.RenderError, match=expected):
            rd.render_manim(tools, scene_dir, KIT, tmp_path / "cache")


def test_three_scenes_and_visual_fixes_use_their_own_tasks(tmp_path, monkeypatch):
    from sotawhat.llm.tasks import DEFAULT_TASKS

    assert DEFAULT_TASKS["lesson_code_3d"].reasoning == "low" and DEFAULT_TASKS["lesson_fix"].reasoning == "low"
    assert DEFAULT_TASKS["lesson_code_3d"].max_tokens >= 24000 and coder.TASKS == {"manim": "lesson_code",
                                                                                   "three": "lesson_code_3d"}

    def fake_three(tools, lessons_root, scene_dir, lenient=False):
        (scene_dir / "out.mp4").write_bytes(b"x")

    monkeypatch.setattr(rd, "render_three", fake_three)
    tasks = []

    class Gateway:
        def structured(self, task, messages, model, models=None):
            tasks.append(task)
            return coder.SceneCode(code="export default function build(kit) { return { update(t) {} }; }")

    report = coder.build_scene(Gateway(), None, tmp_path, tmp_path / "s2", tmp_path, tmp_path, _plan(), 2, [2.0, 3.0],
                               log=lambda *_: None, critic=False)
    assert report["ok"] and tasks == ["lesson_code_3d"]


def test_lessons_never_pay_dear_endpoints(tmp_path):
    from types import SimpleNamespace

    from sotawhat.lessons.pipeline import MAX_PRICE, _gateway
    from sotawhat.store.db import Store

    settings = SimpleNamespace(openrouter_api_key="k", openrouter_base_url="https://openrouter.ai/api/v1",
                               openrouter_app_title="", openrouter_zdr=True, openrouter_data_collection="deny",
                               quantizations=["fp8"], sotawhat_llm_budget_usd_day=1.0, sotawhat_llm_budget_usd_month=25.0,
                               sotawhat_llm_budget_usd_lesson=0.6, sotawhat_config_dir=tmp_path,
                               model_override=lambda task: "")
    with Store(tmp_path / "insight.db") as st:
        gw = _gateway(settings, st, st.start_run("lesson"), 0.0, "economico")
        assert gw.privacy.max_price == MAX_PRICE["economico"] and gw.budget_run == 0.6 and gw.budget_day is None
        assert MAX_PRICE["economico"]["completion"] < 8.0 <= MAX_PRICE["equilibrado"]["completion"] + 2.0
