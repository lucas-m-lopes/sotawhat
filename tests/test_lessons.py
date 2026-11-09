# tests/test_lessons.py
"""Lessons: the code policy, the narration and its glossary, the audio assembly, the repair loop of a scene,
the Telegram buttons (quiz, review, voice), the re-quiz and the CLI."""
import base64
import io
import json
import wave
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from sotawhat.lessons import assemble as asm
from sotawhat.lessons import coder
from sotawhat.lessons import render as rd
from sotawhat.lessons.deliver import handle_callback, requiz_due, review_keyboard, send_lesson
from sotawhat.lessons.plan import Beat, LessonPlan, QuizItem, Scene, Term
from sotawhat.lessons.voice import GoogleEngine, VoiceError, narrate, parse_voice, spoken
from sotawhat.notify.telegram import TelegramNotifier
from sotawhat.store.db import Store

GOOD_PY = '''from lesson_kit import *
import numpy as np


class Cena(LessonScene):
    def construct(self):
        self.beat(FadeIn(title("Atenção")))
        self.beat()
'''
GOOD_JS = '''// keys and values; the document of the paper says Date 2017
export default function build(kit) {
  const { THREE, scene } = kit;
  const rnd = kit.random(3);
  return { update(t) { scene.rotation.y = t * rnd(); } };
}
'''


def _wav(path, seconds, rate=22050):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\1\0" * int(seconds * rate))
    return path


def _plan(modes=("manim", "three")):
    return LessonPlan(title="Atenção", process="atenção", objective="entender",
                      prerequisites=[Term(term="Q", gloss_pt="consulta")],
                      scenes=[Scene(title=f"C{n}", mode=m, why_3d="espacial" if m == "three" else "", goal="g",
                                    beats=[Beat(narration="Frase um da cena.", visual="v", source=-1),
                                           Beat(narration="Frase dois da cena.", visual="v", source=-1)],
                                    labels=[Term(term="Q", gloss_pt="consulta")]) for n, m in enumerate(modes, 1)],
                      quiz=[QuizItem(question="Por que dividir por raiz de d?", options=["escala", "cor", "ruído"],
                                     answer=0, explanation="Evita saturar a softmax.", source=-1),
                            QuizItem(question="O que é V?", options=["value", "voxel", "vetor nulo"], answer=0,
                                     explanation="O value é misturado pelos pesos.", source=-1)])


# --- policy ---------------------------------------------------------------------------------------------
def test_python_policy():
    assert rd.python_problems(GOOD_PY) == []
    bad = GOOD_PY + "\nimport os\nx = open('a')\ny = ().__class__\nconfig.media_dir = 'x'\n"
    problems = "\n".join(rd.python_problems(bad))
    for expected in ("import os", "`open`", "`__class__`", "`config`"):
        assert expected in problems
    assert "self.play" in "\n".join(rd.python_problems(GOOD_PY.replace("self.beat()", "self.play(Wait())")))
    assert "Cena" in rd.python_problems("from lesson_kit import *\nclass Other(LessonScene):\n    pass\n")[0]
    assert "sintaxe" in rd.python_problems("def (:")[0]


def test_js_policy_ignores_comments():
    assert rd.js_problems(GOOD_JS) == []
    problems = "\n".join(rd.js_problems("import x from 'y';\nexport default function build(k) { fetch('u'); "
                                        "const a = Math.random(); return {update(t) { document.title = t; }}; }"))
    for expected in ("import", "fetch", "Math.random", "document"):
        assert expected in problems
    assert "export default" in rd.js_problems("function build() {}")[0]


# --- voice ----------------------------------------------------------------------------------------------
def test_voice_spec_and_glossary():
    assert parse_voice("piper:faber") == ("piper", "faber") and parse_voice(None) == ("piper", "faber")
    with pytest.raises(VoiceError):
        parse_voice("edge:francisca")
    glossary = [{"term": "large language model", "spoken": "lardj"}, {"term": "token", "spoken": "tôken"},
                {"term": "tokens", "spoken": "tôkens"}]
    assert spoken("O Large Language Model lê tokens e um token; tokenizer fica.", glossary) == \
        "O lardj lê tôkens e um tôken; tokenizer fica."


def test_google_engine_sends_the_key_in_a_header(tmp_path):
    seen = []
    audio = io.BytesIO()
    _wav(tmp_path / "x.wav", 0.5, rate=24000)
    content = (tmp_path / "x.wav").read_bytes()

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"audioContent": base64.b64encode(content).decode()})

    engine = GoogleEngine("segredo", "pt-BR-Chirp3-HD-Charon", client=httpx.Client(transport=httpx.MockTransport(handler)))
    engine.synthesize([("Use a softmax.", tmp_path / "out.wav")], [{"term": "softmax", "ipa": "ˈsɔft.mɛks"}])
    body = json.loads(seen[0].content)
    assert seen[0].headers["X-Goog-Api-Key"] == "segredo" and "segredo" not in str(seen[0].url)
    assert body["voice"]["name"] == "pt-BR-Chirp3-HD-Charon"
    assert body["input"]["customPronunciations"]["pronunciations"][0]["phrase"] == "softmax"
    assert (tmp_path / "out.wav").read_bytes() == content and audio.getvalue() == b""
    with pytest.raises(VoiceError):
        GoogleEngine("", "x")


def test_narrate_keeps_existing_clips(tmp_path):
    calls = []

    class Fake:
        def synthesize(self, jobs, glossary=(), workdir=None):
            calls.append([str(p.name) for _, p in jobs])
            for _, p in jobs:
                _wav(p, 1.0)

    plan = _plan()
    durations = narrate(Fake(), plan, tmp_path / "audio")
    assert durations == [[1.45, 1.45], [1.45, 1.45]] and calls[0][0] == "c01f01.wav"
    (tmp_path / "audio" / "c02f02.wav").unlink()
    narrate(Fake(), plan, tmp_path / "audio")
    assert calls[1] == ["c02f02.wav"]                                               # only the missing sentence


# --- assembly -------------------------------------------------------------------------------------------
def test_scene_audio_pads_each_sentence_and_follows_the_video(tmp_path):
    a, b = _wav(tmp_path / "a.wav", 1.0), _wav(tmp_path / "b.wav", 2.0)
    total = asm.scene_audio([a, b], [1.5, 2.5], tmp_path / "scene.wav", video_seconds=4.1)
    with wave.open(str(tmp_path / "scene.wav")) as w:
        assert w.getframerate() == 22050 and abs(w.getnframes() / 22050 - 4.1) < 0.001
    assert abs(total - 4.1) < 1e-9
    asm.concat_wav([(None, 1.0), (tmp_path / "scene.wav", 4.1), (None, 2.0)], tmp_path / "all.wav")
    with wave.open(str(tmp_path / "all.wav")) as w:
        assert abs(w.getnframes() / w.getframerate() - 7.1) < 0.001
    _wav(tmp_path / "c.wav", 1.0, rate=24000)
    with pytest.raises(ValueError):
        asm.concat_wav([(a, 1.0), (tmp_path / "c.wav", 1.0)], tmp_path / "bad.wav")
    assert asm.target_kbps(300, 48) == 1162 and asm.target_kbps(30, 48) > 4000


# --- the repair loop ------------------------------------------------------------------------------------
class CodeGateway:
    def __init__(self, *codes):
        self.codes, self.calls = list(codes), []

    def structured(self, task, messages, model, models=None):
        self.calls.append((task, messages, models))
        return coder.SceneCode(code=self.codes.pop(0))


def test_scene_is_repaired_then_escalated_then_rendered(tmp_path, monkeypatch):
    renders = []

    def fake_manim(tools, scene_dir, kit_dir, cache_dir, lenient=False, **kw):
        renders.append(lenient)
        if len(renders) < 3:
            raise rd.RenderError("Traceback ...\nNameError: name 'Foo' is not defined")
        (scene_dir / "out.mp4").write_bytes(b"x")
        (scene_dir / "warnings.txt").write_text("", encoding="utf-8")

    monkeypatch.setattr(rd, "render_manim", fake_manim)
    gw = CodeGateway(GOOD_PY.replace("import numpy as np", "import os"), GOOD_PY, GOOD_PY, GOOD_PY)
    report = coder.build_scene(gw, None, tmp_path, tmp_path / "s1", tmp_path, tmp_path, _plan(), 1, [2.0, 3.0],
                               log=lambda *_: None)
    assert report["ok"] and report["attempts"] == 4 and not report["fallback"]
    assert "política de código" in report["errors"][0] and "NameError" in report["errors"][1]
    other = coder.ESCALATE["economico"]["manim"][0]
    assert [c[2][0] for c in gw.calls] == [coder.PRIMARY["manim"][0], coder.PRIMARY["manim"][0], other, other]
    assert other != coder.PRIMARY["manim"][0] and coder.ESCALATE["equilibrado"]["manim"][0].startswith("moonshotai/")
    assert renders == [False, False, True]                                         # lenient only on the last try
    assert "O render falhou" in gw.calls[-1][1][-1]["content"]
    beats = json.loads((tmp_path / "s1" / "scene.json").read_text(encoding="utf-8"))["beats"]
    assert beats == [{"text": "Frase um da cena.", "duration": 2.0}, {"text": "Frase dois da cena.", "duration": 3.0}]


def test_a_scene_that_never_renders_becomes_a_slide(tmp_path, monkeypatch):
    scripts = []

    def fake_three(*args, **kw):
        raise rd.RenderError("erro de JavaScript: x is not defined")

    def fake_manim(tools, scene_dir, kit_dir, cache_dir, lenient=False, **kw):
        scripts.append((scene_dir / "scene.py").read_text(encoding="utf-8"))
        (scene_dir / "out.mp4").write_bytes(b"x")

    monkeypatch.setattr(rd, "render_three", fake_three)
    monkeypatch.setattr(rd, "render_manim", fake_manim)
    gw = CodeGateway(*[GOOD_JS] * 4)
    report = coder.build_scene(gw, None, tmp_path, tmp_path / "s2", tmp_path, tmp_path, _plan(), 2, [2.0, 3.0],
                               log=lambda *_: None)
    assert report["fallback"] and not report["ok"] and report["attempts"] == 4
    assert (tmp_path / "s2" / "index.html").exists() and "class Cena(LessonScene)" in scripts[0]
    assert rd.python_problems(scripts[0].replace("import textwrap\n", "")) == [] or "textwrap" in scripts[0]


# --- Telegram -------------------------------------------------------------------------------------------
class FakeNotifier:
    def __init__(self):
        self.sent, self.answers, self.edits = [], [], []

    def send_video(self, path, **kw):
        self.sent.append(("video", path, kw))

    def send_message(self, text, reply_markup=None, disable_notification=False):
        self.sent.append(("message", text, reply_markup))

    def answer_callback(self, cid, text=""):
        self.answers.append(text)

    def edit_message_text(self, chat, mid, text, reply_markup=None):
        self.edits.append((text, reply_markup))

    def edit_reply_markup(self, chat, mid, markup):
        self.edits.append((None, markup))


def _query(data):
    return {"id": "1", "data": data, "from": {"id": 7}, "message": {"chat": {"id": 7}, "message_id": 9}}


def test_delivery_quiz_review_and_requiz(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        lid = st.create_lesson("Atenção", [1])
        st.update_lesson(lid, plan=_plan().model_dump(), video_path="aula.mp4", duration_s=272.0, cost_usd=0.08,
                         report={"video": {"height": 1080}})
        n = FakeNotifier()
        send_lesson(st, n, lid)
        kinds = [s[0] for s in n.sent]
        assert kinds == ["video", "message", "message", "message"] and "4:32" in n.sent[0][2]["caption"]
        assert n.sent[1][2]["inline_keyboard"][0][0]["callback_data"] == f"q:{lid}:0:0:0"
        assert st.get_lesson(lid)["status"] == "entregue"
        assert handle_callback(st, n, _query(f"q:{lid}:0:0:1")) == "quiz" and n.answers[-1].startswith("❌")
        assert "a certa é A" in n.edits[-1][0] and n.edits[-1][1] == {"inline_keyboard": []}
        assert handle_callback(st, n, _query(f"q:{lid}:0:0:0")) == "quiz" and "já respondida" in n.answers[-1]
        handle_callback(st, n, _query(f"q:{lid}:0:1:0"))
        assert st.lesson_score(lid, 0) == (1, 2) and "1/2 certas" in n.sent[-1][1]
        assert handle_callback(st, n, _query(f"l:{lid}:melhor")) == "review"
        assert handle_callback(st, n, _query(f"l:{lid}:ok")) == "review"
        row = st.get_lesson(lid)
        assert (row["review"], row["comparison"]) == ("ok", "melhor")
        assert n.edits[-1][1] == review_keyboard(lid, "ok", "melhor") and n.edits[-1][1]["inline_keyboard"][0][0]["text"].startswith("✓")
        assert handle_callback(st, n, _query("f:abcdef0123:u")) is None                 # not a lesson button
        later = datetime.now(timezone.utc) + timedelta(days=3)
        assert requiz_due(st, n, now=later) == 1 and requiz_due(st, n, now=later) == 0
        assert n.sent[-2][2]["inline_keyboard"][0][0]["callback_data"].startswith(f"q:{lid}:1:")


def test_voice_vote(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        n = FakeNotifier()
        assert handle_callback(st, n, _query("v:B")) == "voice" and "não encontrado" in n.answers[-1]
        st.meta_set("lesson_voice_test", json.dumps({"A": "piper:faber", "B": "piper:jeff"}))
        handle_callback(st, n, _query("v:B"))
        assert st.meta_get("lesson_voice") == "piper:jeff"


def test_send_video_is_a_multipart_upload(tmp_path):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    video = tmp_path / "aula.mp4"
    video.write_bytes(b"\0" * 100)
    n = TelegramNotifier("t", "42", transport=httpx.MockTransport(handler))
    n.send_video(video, caption="Aula", duration=272.4, width=1920, height=1080,
                 reply_markup={"inline_keyboard": []})
    body = seen[0].content
    assert seen[0].url.path.endswith("/sendVideo") and b'name="video"; filename="aula.mp4"' in body
    assert b'name="supports_streaming"' in body and b'name="duration"\r\n\r\n272' in body and b'"inline_keyboard"' in body


def test_cli_lessons_arguments():
    from sotawhat.cli import parse_args

    ns = parse_args(["lessons", "make", "--tema", "Atenção no Transformer", "--entidade", "105", "--entidade", "634",
                     "--sem-envio"])
    assert (ns.lessons_action, ns.tema, ns.entidade, ns.no_send, ns.modo) == ("make", "Atenção no Transformer",
                                                                            [105, 634], True, "economico")
    assert parse_args(["lessons", "resume", "3"]).id == 3
    with pytest.raises(SystemExit):
        parse_args(["lessons", "send"])


def test_doctor_lessons_check(tmp_path):
    from types import SimpleNamespace

    from sotawhat.doctor import check_lessons
    from sotawhat.lessons.tools import Tools

    settings = SimpleNamespace(sotawhat_data_dir=tmp_path, google_tts_api_key="")
    assert check_lessons(settings).status == "warn"                                   # nothing installed
    tools = Tools(tmp_path / "tools")

    class Ready(Tools):
        def status(self):
            return {"python": True, "chromium": True, "ffmpeg": True, "voices": ["faber"]}

    check = check_lessons(settings, tools=Ready(tools.root))
    assert check.status == "ok" and "faber" in check.detail and "sem GOOGLE_TTS_API_KEY" in check.detail
