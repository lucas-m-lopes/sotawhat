"""The HyperFrames engine end to end with doubles (no LLM, ElevenLabs, node or Chrome): the steps run in order (the
storyboard before the paid voice), a resume redoes nothing, the report prices LLM + voice in US$ and R$, the delivery
caption and the lessons page read the new plan, and `lessons resume` follows the engine of the lesson."""
import json
from argparse import Namespace

import pytest

from sotawhat.config import load_settings
from sotawhat.fx import Rate
from sotawhat.lessons import eleven, motion, pipeline
from sotawhat.lessons.deliver import send_lesson
from sotawhat.lessons.pack import Pack, Source
from sotawhat.lessons.plan import FactCheck
from sotawhat.lessons.storyboard import Storyboard
from sotawhat.lessons.tools import Tools
from sotawhat.store.db import Store
from sotawhat.web.app import lesson_payload
from tests.test_lessons import FakeNotifier
from tests.test_lessons_hf import alignment
from tests.test_lessons_plan import motion_plan_with


def board_for(plan) -> Storyboard:
    empty = {"patches": {"image": "nenhuma", "rows": 0, "cols": 0, "focus_row": 0, "focus_col": 0},
             "axes": {"x_label": "", "y_label": "", "x_min": 0, "x_max": 0, "y_min": 0, "y_max": 0},
             "volume": {"organ": "nenhum", "finding": "nenhum", "modality": "nenhuma", "slices": 0}}
    scenes = []
    for n, scene in enumerate(plan.scenes, 1):
        node = {"id": "a", "label": "parte", "kind": "box", "role": "query", "col": 0, "row": 0, "panel": 1, "gloss": "",
                "values": []}
        steps = [{"beat": k, "actions": [{"do": "show", "ids": ["a"], "text": "", "value": 0, "cue": ""}]}
                 for k in range(len(scene.beats))]
        scenes.append({"scene": n, "template": scene.template, "nodes": [node], "edges": [], "bars": [], "vectors": [],
                       "formula": [], "series": [], "events": [], "columns": [], "rows": [], "steps": steps, **empty})
    return Storyboard.model_validate({"scenes": scenes})


class Gateway:
    def __init__(self, events, *outputs):
        self.events, self.outputs = events, list(outputs)

    def structured(self, task, messages, model, models=None):
        self.events.append(task)
        return self.outputs.pop(0)


@pytest.fixture
def engine(tmp_path, monkeypatch):
    """A lesson with its sources, and every external piece replaced by a double that records what ran."""
    events = []
    settings = load_settings(sotawhat_data_dir=tmp_path, elevenlabs_api_key="k", sotawhat_elevenlabs_plan_usd=5.0,
                             sotawhat_elevenlabs_plan_credits=30000)
    plan = motion_plan_with()
    gateway = Gateway(events, plan, FactCheck(problems=[]), board_for(plan))
    monkeypatch.setattr(pipeline, "_gateway", lambda *a, **k: gateway)

    class FakeEleven:
        def __init__(self, key):
            pass

        def speak(self, text, *a, **k):
            events.append("voz")
            return b"ID3", alignment(text), len(text) + 2

    def to_wav(ffmpeg, mp3, wav, lead_in=0.35):
        eleven.silence(wav, 1.0)
        return 1.0

    monkeypatch.setattr(eleven, "ElevenLabs", FakeEleven)
    monkeypatch.setattr(eleven, "to_wav", to_wav)
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"")
    monkeypatch.setattr(Tools, "ffmpeg", lambda self: str(ffmpeg))

    class HF:
        root = tmp_path / "hf-tools"

        def ready(self):
            return True

    from sotawhat.lessons import hyperframes as hfm

    def compose(hf, project, plan, board, nar, lesson_id, codes=None):
        events.append("compose")
        (project / "compositions").mkdir(parents=True, exist_ok=True)
        (project / "index.html").write_text(board.model_dump_json(), encoding="utf-8")
        return {"scenes": [{"template": s.template} for s in board.scenes]}

    def render(settings, work, hf, tools, log=print):
        events.append("render")
        (work / "aula.mp4").write_bytes(b"mp4")
        return {"seconds": 288.0, "bytes": 3, "kbps": 1700, "height": 1080, "render_s": 1.0}

    monkeypatch.setattr(hfm, "hf_tools", lambda s: HF())
    monkeypatch.setattr(hfm, "compose", compose)
    monkeypatch.setattr(hfm, "check", lambda hf, project: {"ok": True, "errors": [], "warnings": ["layout: x"]})
    monkeypatch.setattr(motion, "render_step", render)
    monkeypatch.setattr(motion.interactive, "build", lambda *a, **k: None)
    monkeypatch.setattr("sotawhat.fx.usd_brl", lambda store=None, **k: Rate(5.584, "2026-11-10"))
    store = Store(tmp_path / "insight.db")
    lesson_id = store.create_lesson("Atenção", [1])
    work = tmp_path / "lessons" / f"{lesson_id:03d}"
    work.mkdir(parents=True)
    pack = Pack(topic="Atenção", sources=[Source(0, "u", "Attention", "https://x", "2026-11-01", "resumo", "texto")])
    (work / "sources.json").write_text(pack.to_json(), encoding="utf-8")
    yield settings, store, lesson_id, work, events, plan
    store.close()


def test_a_lesson_runs_every_step_once_and_is_priced(engine):
    settings, store, lesson_id, work, events, plan = engine
    assert motion.run_motion_lesson(settings, store, lesson_id, deliver=False, log=lambda *_: None) == 0
    # the storyboard is decided before the first credit is spent
    assert events.index("lesson_storyboard") < events.index("voz") < events.index("compose") < events.index("render")
    assert events.count("voz") == len(plan.scenes)
    row = store.get_lesson(lesson_id)
    report = json.loads(row["report_json"])
    credits = sum(len(" ".join(b.narration for b in s.beats)) + 2 for s in plan.scenes)
    assert report["engine"] == "hyperframes" and report["voice"]["credits"] == credits
    assert report["voice"]["usd"] == eleven.credits_usd(credits) and report["llm_usd"] == 0.0
    assert report["cost_usd"] == report["voice"]["usd"] and report["cost_brl"] == round(report["cost_usd"] * 5.584, 2)
    assert report["ptax"] == {"brl": 5.584, "day": "2026-11-10", "source": "PTAX/BCB"}
    assert row["status"] == "pronta" and row["cost_usd"] == report["cost_usd"] and (work / "fontes.md").exists()
    assert report["storyboard"]["templates"] == ["graph"] * 7 and report["gates"]["G2"] == []
    # a resume with nothing to redo spends nothing and keeps the video
    events.clear()
    assert motion.run_motion_lesson(settings, store, lesson_id, deliver=False, log=lambda *_: None) == 0
    assert events == ["compose"]
    report2 = json.loads(store.get_lesson(lesson_id)["report_json"])
    assert report2["voice"]["credits"] == credits and len(report2["runs"]) == 2


def test_redo_voice_is_charged_again_and_video_renders_again(engine):
    settings, store, lesson_id, work, events, plan = engine
    motion.run_motion_lesson(settings, store, lesson_id, deliver=False, log=lambda *_: None)
    first = json.loads(store.get_lesson(lesson_id)["report_json"])["voice"]["credits"]
    events.clear()
    motion.run_motion_lesson(settings, store, lesson_id, deliver=False, redo={"voz", "video"}, log=lambda *_: None,
                             fresh_budget=True)
    assert events.count("voz") == len(plan.scenes) and "render" in events
    assert json.loads(store.get_lesson(lesson_id)["report_json"])["voice"]["credits"] == 2 * first


def test_a_failing_step_stops_the_lesson_before_the_voice(engine, monkeypatch):
    settings, store, lesson_id, work, events, plan = engine

    def broken(*a, **k):
        raise RuntimeError("storyboard sem saída")
    monkeypatch.setattr(motion, "make_storyboard", broken)
    assert motion.run_motion_lesson(settings, store, lesson_id, deliver=False, log=lambda *_: None) == 1
    row = store.get_lesson(lesson_id)
    assert row["status"] == "falhou" and "storyboard" in row["error"] and "voz" not in events


def test_delivery_and_page_of_a_hyperframes_lesson(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        lid = st.create_lesson("Atenção", [1])
        st.update_lesson(lid, plan=motion_plan_with(("graph", "volume3d") + ("graph",) * 5).model_dump(),
                         video_path="aula.mp4", duration_s=209.0, cost_usd=0.4897,
                         report={"engine": "hyperframes", "video": {"height": 1080}, "cost_brl": 2.73, "llm_usd": 0.03,
                                 "voice": {"credits": 2730, "usd": 0.455, "plan": [5.0, 30000]}, "cost_usd": 0.4897})
        n = FakeNotifier()
        send_lesson(st, n, lid)
        caption = n.sent[0][2]["caption"]
        assert "US$ 0,49 (R$ 2,73)" in caption and "interativas" not in caption and "3:29" in caption
        assert [s[0] for s in n.sent] == ["video", "message", "message", "message", "message", "message"]
        payload = lesson_payload(st, st.get_lesson(lid), tmp_path, detail=True)
        assert payload["engine"] == "hyperframes" and payload["cost_brl"] == 2.73 and payload["scenes3d"] == []
        assert payload["report"]["voice"]["credits"] == 2730 and payload["plan"]["scenes"][1]["template"] == "volume3d"


def test_resume_follows_the_engine_of_the_lesson(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(motion, "run_motion_lesson", lambda *a, **k: calls.append(k) or 0)
    monkeypatch.setattr(pipeline, "run_lesson", lambda *a, **k: calls.append("manim") or 0)
    monkeypatch.setattr(Tools, "ready", lambda self: True)
    db = tmp_path / "insight.db"
    monkeypatch.setattr("sotawhat.config.load_settings", lambda **k: load_settings(sotawhat_data_dir=tmp_path))
    with Store(db) as st:
        new = st.create_lesson("Atenção", [])
        st.update_lesson(new, report={"engine": "hyperframes"})
    base = dict(id=new, tema=None, entidade=None, auto=False, voz=None, modo="economico", no_send=True, aula=None)
    assert pipeline.main_lessons(Namespace(lessons_action="resume", refazer="storyboard", **base)) == 0
    assert calls[-1]["redo"] == {"storyboard"} and calls[-1]["fresh_budget"] is True
    assert pipeline.main_lessons(Namespace(lessons_action="resume", refazer="2,5", **base)) == 2     # scenes: Manim only
    assert pipeline.main_lessons(Namespace(lessons_action="rerender", refazer="", **base)) == 2


# ---- lessons from the interface (F1): the plan alone, the steps the engine announces, the jobs of the commands ----
class Steps:
    """What lessons/jobs.Tracker hears from the engine."""

    def __init__(self):
        self.calls = []

    def attach(self, lesson_id):
        self.calls.append(("attach", lesson_id))

    def expect(self, names):
        self.calls.append(("expect", list(names)))

    def stage(self, name):
        self.calls.append(name)

    def names(self):
        return [c for c in self.calls if isinstance(c, str)]


def test_the_plan_alone_stops_before_the_storyboard_and_the_voice(engine):
    settings, store, lesson_id, work, events, plan = engine
    steps = Steps()
    assert motion.run_motion_lesson(settings, store, lesson_id, deliver=True, mode="equilibrado", until="roteiro",
                                    progress=steps, log=lambda *_: None) == 0
    assert events == ["lesson_plan", "lesson_facts"]
    assert steps.calls == [("attach", lesson_id), ("expect", ["roteiro"]), "roteiro"]
    row = store.get_lesson(lesson_id)
    report = json.loads(row["report_json"])
    assert row["status"] == "planejada" and report["mode"] == "equilibrado" and report["llm_usd"] == 0.0
    assert (work / "plan.json").exists() and not (work / "storyboard.json").exists()
    run = store.conn.execute("SELECT ok, finished_at FROM runs WHERE id = ?", (report["runs"][-1],)).fetchone()
    assert run["ok"] == 1 and run["finished_at"]
    events.clear()
    steps = Steps()                                       # producing it afterwards does not plan again
    assert motion.run_motion_lesson(settings, store, lesson_id, deliver=False, progress=steps, log=lambda *_: None) == 0
    assert events[0] == "lesson_storyboard" and "lesson_plan" not in events
    assert steps.names() == ["roteiro", "storyboard", "voz", "checagem", "video"]
    assert ("expect", ["roteiro", "storyboard", "voz", "checagem", "video"]) in steps.calls


def test_the_steps_of_a_production_with_3d_and_sending(engine, monkeypatch):
    settings, store, lesson_id, work, events, plan = engine
    plan3d = motion_plan_with(("graph", "mechanism3d") + ("graph",) * 5)
    (work / "plan.json").write_text(plan3d.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(motion, "storyboard_step", lambda *a, **k: board_for(plan3d))
    monkeypatch.setattr(motion.three3d, "code_step",
                        lambda *a, **k: events.append("3d") or {"codes": {}, "scenes": {}, "fallback": []})
    monkeypatch.setattr(pipeline, "send", lambda *a, **k: events.append("send") or 0)
    steps = Steps()
    assert motion.run_motion_lesson(settings, store, lesson_id, deliver=True, progress=steps, log=lambda *_: None) == 0
    assert steps.names() == ["roteiro", "storyboard", "voz", "3d", "checagem", "video", "envio"]
    assert ("expect", ["3d"]) in steps.calls and events[-1] == "send" and "3d" in events


def test_a_lesson_that_never_ran_goes_to_the_hyperframes_engine(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        fresh = st.create_lesson("Atenção", [])
        assert motion.engine_of(st.get_lesson(fresh)) == "hyperframes"
        manim = st.create_lesson("Atenção", [])
        st.update_lesson(manim, plan={"title": "x", "scenes": []})
        assert motion.engine_of(st.get_lesson(manim)) == "manim"


def test_the_commands_register_their_job_and_wait_their_turn(tmp_path, monkeypatch):
    from sotawhat.cli import parse_args
    from sotawhat.lessons import jobs

    calls = []

    def fake_run(settings, store, lesson_id, **k):
        k["progress"].attach(lesson_id)
        k["progress"].stage("roteiro")
        k["log"]("roteiro pronto")
        calls.append(k)
        return 0

    monkeypatch.setattr(motion, "run_motion_lesson", fake_run)
    monkeypatch.setattr("sotawhat.config.load_settings", lambda **k: load_settings(sotawhat_data_dir=tmp_path))
    printed = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: printed.append(" ".join(map(str, a))))
    with Store(tmp_path / "insight.db") as st:
        new = st.create_lesson("Atenção", [])
    base = dict(id=new, tema=None, entidade=None, auto=False, voz=None, modo="equilibrado", no_send=True, aula=None,
                refazer="")
    assert pipeline.main_lessons(Namespace(lessons_action="resume", plan_only=True, job=None, **base)) == 0
    assert calls[-1]["until"] == "roteiro" and calls[-1]["mode"] == "equilibrado" and printed[-1] == "roteiro pronto"
    with Store(tmp_path / "insight.db") as st:
        job = jobs.latest(st)
        assert (job["action"], job["state"], job["lesson_id"], job["origin"]) == ("roteiro", "concluida", new, "terminal")
        job_id, token = jobs.create_pending(st, new, "aula", tmp_path / "job.log", ["resume", new])
    # the process the interface starts adopts its job
    assert pipeline.main_lessons(Namespace(lessons_action="resume", plan_only=False, job=token, **base)) == 0
    with Store(tmp_path / "insight.db") as st:
        job = jobs.get(st, job_id)
        assert (job["state"], job["origin"], job["stage"]) == ("concluida", "interface", "roteiro")
        jobs.Tracker(st, "aula", lesson_id=new, beat_every=None).claim()          # another one, alive
    assert pipeline.main_lessons(Namespace(lessons_action="resume", plan_only=False, job=None, **base)) == 2
    assert "já há uma tarefa de aula em andamento" in printed[-1] and "cancele na aba Aulas" in printed[-1]
    assert pipeline.main_lessons(Namespace(lessons_action="resume", plan_only=False, job="gone", **base)) == 2
    assert printed[-1] == "a tarefa desta aula foi cancelada ou não existe mais"
    ns = parse_args(["lessons", "resume", "9", "--so-roteiro", "--job", "abc"])
    assert (ns.plan_only, ns.job, ns.id) == (True, "abc", 9)
