# sotawhat/lessons/motion.py
"""`sotawhat lessons hf <id>`: the HyperFrames pipeline, tried on the plan of an existing lesson.

    plan (reused, narration cleaned) → ElevenLabs narration per scene, with the time of every word
    → storyboard (LLM: one kit template per scene + the actions of each sentence, validated)
    → HyperFrames project (kit templates, captions, the narration track) → `hyperframes check`
    → render (headless Chrome + FFmpeg) → MP4 under the Telegram limit → Telegram (video + review buttons)

Every step leaves its file in data/lessons/<new id>/ and is skipped when the file exists, so a rerun after a
change in the kit only composes and renders again (no LLM, no ElevenLabs credits)."""
import json
import re
import shutil
import time
from pathlib import Path

from sotawhat.lessons import eleven
from sotawhat.lessons.plan import LessonPlan
from sotawhat.lessons.storyboard import Storyboard, clean_narration, make_storyboard, validate

_UNITS = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "quatro": 4, "cinco": 5, "seis": 6,
          "sete": 7, "oito": 8, "nove": 9}
_TEENS = {10: "dez", 11: "onze", 12: "doze", 13: "treze", 14: "catorze", 15: "quinze", 16: "dezesseis",
          17: "dezessete", 18: "dezoito", 19: "dezenove"}
_TENS = {2: "vinte", 3: "trinta", 4: "quarenta", 5: "cinquenta", 6: "sessenta", 7: "setenta", 8: "oitenta",
         9: "noventa"}
_DIGIT_PAIR = re.compile(r"\bvírgula (um|dois|três|quatro|cinco|seis|sete|oito|nove) "
                         r"(zero|um|dois|três|quatro|cinco|seis|sete|oito|nove)\b")
INTRO_S = 3.2


def two_digits(n) -> str:
    if n < 10:
        return [k for k, v in _UNITS.items() if v == n][0]
    if n < 20:
        return _TEENS[n]
    tens, unit = divmod(n, 10)
    return _TENS[tens] + (f" e {two_digits(unit)}" if unit else "")


def spoken_decimals(text) -> str:
    """"zero vírgula nove quatro" (digit by digit, as the planner wrote it) → "zero vírgula noventa e quatro"."""
    return _DIGIT_PAIR.sub(lambda m: "vírgula " + two_digits(_UNITS[m.group(1)] * 10 + _UNITS[m.group(2)]), text)


def narration_sentences(plan) -> list:
    return [[spoken_decimals(clean_narration(b.narration)) for b in scene.beats] for scene in plan.scenes]


def _save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _load(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def prepare(settings, store, source_id, lessons_root) -> int:
    """New lesson row and folder with the plan, the sources and the NotebookLM pack of lesson `source_id`."""
    source = store.get_lesson(source_id)
    if source is None or not source["plan_json"]:
        raise ValueError(f"a aula {source_id} não tem plano")
    lesson_id = store.create_lesson(source["topic"], json.loads(source["entities_json"] or "[]"))
    src, work = lessons_root / f"{int(source_id):03d}", lessons_root / f"{lesson_id:03d}"
    work.mkdir(parents=True, exist_ok=True)
    plan = LessonPlan.model_validate_json(source["plan_json"])
    sentences = narration_sentences(plan)
    for scene, said in zip(plan.scenes, sentences):          # the spoken text is the subtitle text
        for beat, text in zip(scene.beats, said):
            beat.narration = text
    _save(work / "plan.json", plan.model_dump())
    for name in ("sources.json", "fontes.md"):
        if (src / name).exists():
            shutil.copy2(src / name, work / name)
    store.update_lesson(lesson_id, title=plan.title, plan=plan.model_dump(), status="planejada",
                        report={"source_lesson": int(source_id), "engine": "hyperframes"})
    return lesson_id


def narrate_step(settings, work, plan, ffmpeg, log=print) -> dict:
    """ElevenLabs narration (cached per scene) -> the timeline saved in narracao.json."""
    out = work / "narracao.json"
    voice_dir = work / "voz"
    sentences = [[b.narration for b in scene.beats] for scene in plan.scenes]
    el = eleven.ElevenLabs(settings.elevenlabs_api_key)
    nar = eleven.narrate(el, sentences, voice_dir, ffmpeg, intro=INTRO_S, voice=settings.sotawhat_elevenlabs_voice,
                         model=settings.sotawhat_elevenlabs_model, progress=log)
    data = {"wav": str(nar.wav), "duration": nar.duration, "intro": INTRO_S, "scenes": nar.scenes,
            "chars": nar.chars, "billed_chars": nar.billed_chars,
            "voice": f"elevenlabs:{settings.sotawhat_elevenlabs_voice}", "model": settings.sotawhat_elevenlabs_model}
    data["billed_total"] = (_load(out, {}) or {}).get("billed_total", 0) + nar.billed_chars
    _save(out, data)
    return data


def storyboard_step(gateway, work, plan, log=print) -> Storyboard:
    path = work / "storyboard.json"
    sentences = [[b.narration for b in scene.beats] for scene in plan.scenes]
    if path.exists():                    # the repairs of validate() are idempotent: newer rules reach old boards
        board = Storyboard.model_validate_json(path.read_text(encoding="utf-8"))
        validate(board, sentences)
        return board
    t = time.monotonic()
    board, problems = make_storyboard(gateway, plan, sentences)
    if problems:
        log("[storyboard] problemas que ficaram:\n- " + "\n- ".join(problems))
    path.write_text(board.model_dump_json(indent=1), encoding="utf-8")
    log(f"[storyboard] {len(board.scenes)} cenas em {time.monotonic() - t:.0f} s: "
        + ", ".join(s.template for s in board.scenes))
    return board


def render_step(settings, work, hf, tools, log=print) -> dict:
    """HyperFrames render (headless Chrome + FFmpeg) → aula.mp4 under the Telegram limit."""
    from sotawhat.lessons import assemble as asm
    from sotawhat.lessons import hyperframes as hfm

    raw = work / "hf" / "render.mp4"
    t = time.monotonic()
    info = hfm.render(hf, work / "hf", raw, workers=4)
    log(f"[render] {raw.stat().st_size / 1e6:.1f} MB em {time.monotonic() - t:.0f} s · " + " · ".join(info["summary"]))
    video = asm.encode(tools, [raw], work / "voz" / "narration.wav", work / "aula.mp4",
                       max_mb=settings.sotawhat_lesson_max_mb, workdir=work / "hf")
    video["render_s"] = round(time.monotonic() - t, 1)
    return video


def send_prototype(settings, store, lesson_id, source_id, log=print) -> int:
    """The video with a caption that says what changed, and the review buttons (the quiz is the source lesson's)."""
    from sotawhat.lessons.deliver import clock, esc, review_keyboard
    from sotawhat.notify.telegram import TelegramError, TelegramNotifier

    lesson = store.get_lesson(lesson_id)
    plan = LessonPlan.model_validate_json(lesson["plan_json"])
    report = json.loads(lesson["report_json"] or "{}")
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if not notifier.configured:
        log("Telegram não configurado")
        return 2
    caption = (f"🎬 <b>{esc(plan.title)}</b> · protótipo HyperFrames\n"
               f"Mesmo roteiro da aula {source_id}, com visual novo (modelos de cena, setas calculadas, cena 3D em "
               f"three.js) e voz ElevenLabs.\n⏱ {clock(lesson['duration_s'])} · LLM US$ {lesson['cost_usd'] or 0:.3f} · "
               f"{report.get('narration', {}).get('chars', 0)} caracteres de voz")
    try:
        notifier.send_video(lesson["video_path"], caption=caption[:1024], duration=lesson["duration_s"],
                            width=1920 if (report.get("video") or {}).get("height", 1080) == 1080 else 1280,
                            height=(report.get("video") or {}).get("height", 1080))
        notifier.send_message(f"Sua revisão do protótipo (compare com a aula {source_id}):",
                              reply_markup=review_keyboard(lesson_id), disable_notification=True)
    except TelegramError as exc:
        log(f"[telegram] {exc}")
        return 1
    from sotawhat.store.db import utcnow
    store.update_lesson(lesson_id, status="entregue", delivered_at=utcnow())
    log(f"[telegram] protótipo {lesson_id} enviado")
    return 0


def make_hf_lesson(settings, store, source_id, lesson_id=None, deliver=True, redo=(), log=print) -> int:
    """Runs (or resumes) the HyperFrames pipeline. `redo`: steps to throw away first (storyboard, voz, video)."""
    from sotawhat.lessons import hyperframes as hfm
    from sotawhat.lessons.pipeline import _gateway, lessons_root
    from sotawhat.lessons.tools import Tools

    hf, tools = hfm.hf_tools(settings), Tools.from_settings(settings)
    if not hf.ready():
        log(f"HyperFrames incompleto em {hf.root}: instale com npm (veja a seção Animated lessons do README)")
        return 2
    root = lessons_root(settings)
    if lesson_id is None:
        lesson_id = prepare(settings, store, source_id, root)
        log(f"aula #{lesson_id}: protótipo HyperFrames da aula {source_id}")
    work = root / f"{int(lesson_id):03d}"
    if "storyboard" in redo:
        (work / "storyboard.json").unlink(missing_ok=True)
    if "voz" in redo:
        shutil.rmtree(work / "voz", ignore_errors=True)
    plan = LessonPlan.model_validate_json((work / "plan.json").read_text(encoding="utf-8"))
    report = json.loads(store.get_lesson(lesson_id)["report_json"] or "{}")
    report.setdefault("runs", [])
    run_id = store.start_run("lesson")
    report["runs"].append(run_id)
    started = time.monotonic()
    try:
        t = time.monotonic()
        nar = narrate_step(settings, work, plan, tools.ffmpeg(), log=log)
        report["narration"] = {"seconds": round(nar["duration"], 1), "chars": nar["chars"], "voice": nar["voice"],
                               "model": nar["model"], "billed_total": nar["billed_total"], "s": round(time.monotonic() - t, 1)}
        gateway = _gateway(settings, store, run_id, 0.0)
        t = time.monotonic()
        board = storyboard_step(gateway, work, plan, log=log)
        report["storyboard"] = {"templates": [s.template for s in board.scenes], "s": round(time.monotonic() - t, 1)}
        t = time.monotonic()
        layout = hfm.compose(hf, work / "hf", plan, board, nar, lesson_id)
        checked = hfm.check(hf, work / "hf")
        report["check"] = {"ok": checked["ok"], "errors": checked["errors"][:30], "warnings": checked["warnings"][:30],
                           "s": round(time.monotonic() - t, 1)}
        log(f"[check] {'ok' if checked['ok'] else 'com erros'}: {len(checked['errors'])} erros, "
            f"{len(checked['warnings'])} avisos")
        video = render_step(settings, work, hf, tools, log=log)
        report["video"] = video
    except Exception as exc:      # noqa: BLE001 - any step failure is recorded on the lesson and the run
        store.update_lesson(lesson_id, status="falhou", error=str(exc)[:500], report=report)
        store.finish_run(run_id, False, {"lesson": lesson_id}, error=str(exc)[:500])
        log(f"[aula {lesson_id}] parou: {exc}\nretome com: sotawhat lessons hf --aula {lesson_id}")
        return 1
    cost = round(sum(store.llm_cost_for_run(r) for r in report["runs"]), 4)
    report.update(cost_usd=cost, engine="hyperframes", total_s=round(time.monotonic() - started, 1),
                  scenes={str(n): {"template": s["template"], "ok": True} for n, s in enumerate(layout["scenes"], 1)})
    _save(work / "report.json", report)
    store.update_lesson(lesson_id, status="pronta", video_path=str(work / "aula.mp4"), duration_s=video["seconds"],
                        size_bytes=video["bytes"], cost_usd=cost, voice=report["narration"]["voice"], report=report)
    store.finish_run(run_id, True, {"lesson": lesson_id, "cost_usd": cost})
    log(f"[aula {lesson_id}] pronta: {video['seconds']:.0f} s · {video['bytes'] / 1e6:.1f} MB · LLM US$ {cost:.3f} · "
        f"{work / 'aula.mp4'}")
    return send_prototype(settings, store, lesson_id, source_id, log) if deliver else 0
