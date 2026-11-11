"""The hybrid 3D of the lessons (2026-11-11): mechanism3d scenes (three.js written by the LLM inside the HyperFrames
kit, checked by a headless probe and the visual critic, falling back to the graph of the same parts) and the
interactive page of a lesson (one self-contained file with every 3D scene). No LLM, node or Chrome here."""
import json

import pytest

from sotawhat.lessons import hyperframes as hfm
from sotawhat.lessons import interactive, three3d
from sotawhat.lessons.coder import SceneCode, VisualReview
from sotawhat.lessons.deliver import send_lesson
from sotawhat.lessons.storyboard import Node, Step, Storyboard, validate
from sotawhat.notify.telegram import TelegramError
from sotawhat.store.db import Store
from sotawhat.web.app import lesson_payload
from tests.test_lessons import FakeNotifier
from tests.test_lessons_hf import _act, _scene
from tests.test_lessons_plan import motion_plan_with

GANTRY = """export default function build(kit) {
  const { THREE, part, material, color } = kit;
  const ring = part("gantry", new THREE.Mesh(new THREE.TorusGeometry(2, 0.2, 16, 64), material(color("gantry"))));
  part("tubo", new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.5), material(color("tubo"))));
  return { update(t) { ring.rotation.z = t * 0.8; } };
}"""


def _part(i, role="query"):
    return Node(id=i, label=i, kind="vector", role=role, col=0, row=0, panel=1, gloss="", values=[1.0])


def mech_scene():
    return _scene(template="mechanism3d", nodes=[_part("gantry", "neutral"), _part("tubo", "score")],
                  steps=[Step(beat=0, actions=[_act("show", ["gantry"])]), Step(beat=1, actions=[_act("show", ["tubo"])])])


def nar_for(n_scenes, beats=2):
    scenes, t = [], 3.2
    for _ in range(n_scenes):
        words, bs = [], []
        for k in range(beats):
            words.append({"text": "palavra", "start": t + 0.1, "end": t + 0.6, "beat": k})
            bs.append((t + 0.1, t + 0.6))
            t += 1.0
        scenes.append({"start": t - beats, "end": t, "beats": bs, "words": words})
        t += 0.5
    return {"wav": "narration.wav", "duration": t, "intro": 3.2, "scenes": scenes}


# ---- storyboard and plan --------------------------------------------------------------------------------------
def test_a_mechanism_scene_needs_two_to_six_parts_drawn_as_cards_if_it_falls_back():
    scene = mech_scene()
    board = Storyboard(scenes=[scene])
    assert validate(board, [["Frase um.", "Frase dois."]], ["mechanism3d"]) == []
    assert {n.kind for n in scene.nodes} == {"box"}
    lonely = Storyboard(scenes=[_scene(template="mechanism3d", nodes=[_part("a")],
                                       steps=[Step(beat=0, actions=[_act("show", ["a"])])])])
    assert any("2 a 6 peças" in p for p in validate(lonely, [["Frase."]], ["mechanism3d"]))


# ---- the code step ------------------------------------------------------------------------------------------
class Gateway:
    def __init__(self, *outputs):
        self.outputs, self.tasks = list(outputs), []

    def structured(self, task, messages, schema, models=None):
        self.tasks.append(task)
        return self.outputs.pop(0)


def _setup(tmp_path):
    plan = motion_plan_with(("graph", "mechanism3d") + ("graph",) * 5, beats=2)
    board = Storyboard(scenes=[_scene(scene=n, template=s.template,
                                      nodes=[_part("gantry", "neutral"), _part("tubo", "score")],
                                      steps=[Step(beat=0, actions=[_act("show", ["gantry"])]),
                                             Step(beat=1, actions=[_act("show", ["tubo"])])])
                               for n, s in enumerate(plan.scenes, 1)])
    validate(board, [[b.narration for b in s.beats] for s in plan.scenes], [s.template for s in plan.scenes])
    work = tmp_path / "lessons" / "008"
    work.mkdir(parents=True)
    return plan, board, work, nar_for(len(plan.scenes))


def test_the_brief_lists_the_parts_the_sentences_and_the_actions(tmp_path):
    plan, board, work, nar = _setup(tmp_path)
    (start, dur) = hfm.slots(nar)[1]
    data = hfm.scene_data(2, plan.scenes[1], board.scenes[1], nar["scenes"][1], start, dur)
    text = three3d.brief(plan, 2, board.scenes[1], data)
    assert '"gantry": rótulo "gantry"' in text and '"tubo"' in text and "papel score" in text
    assert "0. [0.1–0.6 s] narração:" in text and "ações do storyboard: show gantry" in text
    assert 'part("tubo", …)' in text and "export default function build(kit)" in text
    assert data["beats"] == [(0.1, 0.6), (1.1, 1.6)] and three3d.probe_times(data) == [0.48, 1.48]


def test_a_probe_problem_goes_back_once_then_the_critic_passes_and_a_resume_pays_nothing(tmp_path, monkeypatch):
    plan, board, work, nar = _setup(tmp_path)
    monkeypatch.setattr(hfm, "copy_assets", lambda *a, **k: None)
    probes = [{"errors": [], "issues": [[1, 'a peça "tubo" do storyboard não foi registrada']], "frames": []},
              {"errors": [], "issues": [], "frames": [str(tmp_path / "f1.jpg"), str(tmp_path / "f2.jpg")]}]
    for f in ("f1.jpg", "f2.jpg"):
        (tmp_path / f).write_bytes(b"\xff\xd8")
    seen = []

    def probe(tools, work_, page, times, out_dir):
        seen.append((page, times))
        return probes.pop(0)
    monkeypatch.setattr(three3d, "run_probe", probe)
    gw = Gateway(SceneCode(code=GANTRY.replace('  part("tubo"', '  add(')), SceneCode(code=GANTRY), VisualReview(defects=[]))
    out = three3d.code_step(gw, None, None, work, plan, board, nar, log=lambda *_: None)
    assert out["codes"] == {2: work / "3d" / "s02.js"} and out["fallback"] == []
    assert gw.tasks == ["lesson_code_3d", "lesson_code_3d", "lesson_critic"]
    assert (work / "3d" / "s02.js").read_text(encoding="utf-8") == GANTRY
    assert seen[0][0] == "3d/probe-s02.html" and seen[0][1] == [0.48, 1.48]
    page = (work / "3d" / "probe-s02.html").read_text(encoding="utf-8")
    assert 'import build from "./s02.a2.js"' in page and "mountFree(\"s02\", data, 0, build)" in page
    assert not list((work / "3d").glob("s02.a*.js"))           # the candidates are cleaned up
    report = out["scenes"][2]
    assert report["ok"] and report["attempts"] == 2 and "não foi registrada" in report["errors"][0]
    again = three3d.code_step(Gateway(), None, None, work, plan, board, nar, log=lambda *_: None)
    assert again["codes"] == {2: work / "3d" / "s02.js"} and again["scenes"][2]["cached"]


def test_code_that_breaks_the_policy_never_reaches_the_probe_and_a_scene_that_never_passes_falls_back(tmp_path, monkeypatch):
    plan, board, work, nar = _setup(tmp_path)
    monkeypatch.setattr(hfm, "copy_assets", lambda *a, **k: None)
    calls = []
    monkeypatch.setattr(three3d, "run_probe", lambda *a: calls.append(a) or {"errors": ["erro de JavaScript: x"], "issues": [], "frames": []})
    bad = SceneCode(code=GANTRY.replace("ring.rotation.z = t * 0.8;", "document.title = 'x';"))
    gw = Gateway(bad, SceneCode(code=GANTRY), SceneCode(code=GANTRY))
    out = three3d.code_step(gw, None, None, work, plan, board, nar, log=lambda *_: None)
    assert out["codes"] == {} and out["fallback"] == [2] and len(calls) == 2
    assert "política de código" in out["scenes"][2]["errors"][0]
    assert not (work / "3d" / "s02.js").exists()
    # the failure is remembered: a resume with the same brief does not pay again
    again = three3d.code_step(Gateway(), None, None, work, plan, board, nar, log=lambda *_: None)
    assert again["fallback"] == [2] and again["scenes"][2]["cached"]


def test_compose_writes_the_free_scene_module_or_falls_back_to_the_graph(tmp_path, monkeypatch):
    plan, board, work, nar = _setup(tmp_path)
    monkeypatch.setattr(hfm, "copy_assets", lambda *a, **k: None)
    code = work / "3d" / "s02.js"
    code.parent.mkdir()
    code.write_text(GANTRY, encoding="utf-8")
    project = work / "hf"
    layout = hfm.compose(None, project, plan, board, nar, 8, codes={2: code})
    comp = (project / "compositions" / "s02.html").read_text(encoding="utf-8")
    assert 'import build from "./assets/scenes/s02.js"' in comp and 'mountFree("s02", ' in comp
    assert (project / "assets" / "scenes" / "s02.js").read_text(encoding="utf-8") == GANTRY
    assert layout["scenes"][1]["template"] == "mechanism3d"
    layout = hfm.compose(None, project, plan, board, nar, 8, codes={})
    comp = (project / "compositions" / "s02.html").read_text(encoding="utf-8")
    assert 'MK.scene("s02"' in comp and '"template": "graph"' in comp and layout["scenes"][1]["template"] == "graph"
    assert not (project / "assets" / "scenes" / "s02.js").exists()


# ---- the interactive page --------------------------------------------------------------------------------------
def test_the_interactive_page_holds_the_3d_scenes_only_and_fetches_nothing():
    board = Storyboard(scenes=[_scene(scene=n, template=t) for n, t in
                               enumerate(("graph", "mechanism3d", "volume3d", "mechanism3d"), 1)])
    assert interactive.scenes_3d(board, {2: "x/s02.js"}) == [2, 3]          # scene 4 fell back to the graph
    entry = interactive.entry_source({2: "x/s02.js"}, [2, 3])
    assert 'import b02 from "./s02.js";' in entry and "builds: { s02: b02 }" in entry
    scenes = [{"id": "s02", "num": 2, "title": "A aquisição", "dur": 9.0, "template": "mechanism3d", "data": {},
               "captions": [], "audio": "data:audio/mpeg;base64,AA=="}]
    page = interactive.page("Da TC <ao> volume", "SOTA What · aula 8 · 3D interativo", "body{}",
                            ["var x = '</script>';"], scenes)
    assert "<title>Da TC &lt;ao&gt; volume · 3D interativo · SOTA What</title>" in page
    assert "'<\\/script>'" in page and "PLAYER.start" in page and '"template": "mechanism3d"' in page
    assert "http://" not in page and "https://" not in page and "src=" not in page


def test_the_document_follows_the_video_and_the_page_links_it(tmp_path):
    folder = tmp_path / "008"
    folder.mkdir()
    page = folder / "interativo.html"
    page.write_text("<!doctype html>", encoding="utf-8")
    with Store(tmp_path / "insight.db") as st:
        lid = st.create_lesson("TC", [1])
        assert lid == 1
        st.update_lesson(lid, plan=motion_plan_with(("graph", "mechanism3d") + ("graph",) * 5).model_dump(),
                         video_path="aula.mp4", duration_s=200.0, cost_usd=0.1,
                         report={"engine": "hyperframes", "video": {"height": 1080}, "llm_usd": 0.1,
                                 "voice": {"credits": 0, "usd": 0.0, "plan": [5.0, 30000]}, "cost_usd": 0.1,
                                 "interactive": {"path": str(page), "bytes": 15, "scenes": [2]}})
        n = FakeNotifier()
        send_lesson(st, n, lid)
        assert [s[0] for s in n.sent[:2]] == ["video", "document"]
        assert "3D interativo, quiz e revisão logo abaixo." in n.sent[0][2]["caption"]
        doc = n.sent[1][2]
        assert doc["name"] == "aula-001-3d-interativo.html" and "1 cena(s)" in doc["caption"]
        (tmp_path / "001").mkdir()
        (tmp_path / "001" / "interativo.html").write_text("x", encoding="utf-8")
        assert lesson_payload(st, st.get_lesson(lid), tmp_path)["interactive"] == "/lessons/001/interativo.html"


def test_a_missing_page_is_not_sent(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        lid = st.create_lesson("TC", [1])
        st.update_lesson(lid, plan=motion_plan_with().model_dump(), video_path="aula.mp4", duration_s=200.0,
                         cost_usd=0.1, report={"engine": "hyperframes", "video": {"height": 1080},
                                               "interactive": {"path": str(tmp_path / "nada.html"), "scenes": [2]}})
        n = FakeNotifier()
        send_lesson(st, n, lid)
        assert "document" not in [s[0] for s in n.sent] and "Quiz e revisão logo abaixo." in n.sent[0][2]["caption"]


def test_a_document_telegram_refuses_is_written_in_the_report_and_the_quiz_still_goes(tmp_path):
    page = tmp_path / "interativo.html"
    page.write_text("x", encoding="utf-8")

    class Refusing(FakeNotifier):
        def send_document(self, path, **kw):
            raise TelegramError("sendDocument: HTTP 413 Request Entity Too Large")
    with Store(tmp_path / "insight.db") as st:
        lid = st.create_lesson("TC", [1])
        st.update_lesson(lid, plan=motion_plan_with().model_dump(), video_path="aula.mp4", duration_s=200.0,
                         cost_usd=0.1, report={"engine": "hyperframes", "video": {"height": 1080},
                                               "interactive": {"path": str(page), "scenes": [2]}})
        n = Refusing()
        send_lesson(st, n, lid)
        assert "message" in [s[0] for s in n.sent]
        assert "413" in json.loads(st.get_lesson(lid)["report_json"])["interactive"]["error"]
