# sotawhat/lessons/motion.py
"""The lessons engine since 2026-11-10 (HyperFrames): `sotawhat lessons make` and `resume`, and `lessons hf <id>`
to remake an older lesson in it.

    source pack → plan (LLM, lesson_plan_v3: one kit template per scene, one worked example) → fact gate G1 and
    lint G2 → storyboard (LLM: the data of each template and the actions of each sentence, validated)
    → ElevenLabs narration per scene, with the time of every word → the three.js of the mechanism3d scenes (LLM,
    checked by a headless probe and the visual critic; three3d.py) → HyperFrames project (kit templates, captions,
    the narration track) → `hyperframes check` → render (headless Chrome + FFmpeg) → MP4 under the Telegram limit
    → interativo.html (the 3D scenes to turn by hand; interactive.py) → Telegram (video, the 3D file, quiz,
    review buttons)

The storyboard comes before the voice, so a failure there spends no ElevenLabs credits. Every step leaves its file
in data/lessons/<id>/ and is skipped when the file exists; the render is skipped when the composed project is the
one that produced aula.mp4. The report prices the lesson: LLM (the runs of the lesson) + voice (the credits billed
× the plan's price per credit), in US$ and, by the PTAX of the Banco Central, in R$."""
import hashlib
import json
import re
import shutil
import time
from pathlib import Path

from sotawhat.lessons import eleven, interactive, three3d
from sotawhat.lessons.plan import MotionPlan, check_facts, load_plan, make_plan, revise_plan
from sotawhat.lessons.storyboard import Storyboard, clean_narration, make_storyboard, planned_templates, validate

_UNITS = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "quatro": 4, "cinco": 5, "seis": 6,
          "sete": 7, "oito": 8, "nove": 9}
_TEENS = {10: "dez", 11: "onze", 12: "doze", 13: "treze", 14: "catorze", 15: "quinze", 16: "dezesseis",
          17: "dezessete", 18: "dezoito", 19: "dezenove"}
_TENS = {2: "vinte", 3: "trinta", 4: "quarenta", 5: "cinquenta", 6: "sessenta", 7: "setenta", 8: "oitenta",
         9: "noventa"}
_DIGIT_PAIR = re.compile(r"\bvírgula (um|dois|três|quatro|cinco|seis|sete|oito|nove) "
                         r"(zero|um|dois|três|quatro|cinco|seis|sete|oito|nove)\b")
INTRO_S = 3.2
ENGINE = "hyperframes"
REDO = ("plano", "storyboard", "voz", "3d", "video")


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


def speakable(plan):
    """The spoken text is the caption text: stage directions out, decimals as people say them."""
    for scene, said in zip(plan.scenes, narration_sentences(plan)):
        for beat, text in zip(scene.beats, said):
            beat.narration = text
    return plan


def _save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _load(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def engine_of(lesson) -> str:
    return json.loads(lesson["report_json"] or "{}").get("engine") or "manim"


def prepare(settings, store, source_id, lessons_root) -> int:
    """New lesson row and folder with the plan, the sources and the NotebookLM pack of lesson `source_id`."""
    source = store.get_lesson(source_id)
    if source is None or not source["plan_json"]:
        raise ValueError(f"a aula {source_id} não tem plano")
    lesson_id = store.create_lesson(source["topic"], json.loads(source["entities_json"] or "[]"))
    src, work = lessons_root / f"{int(source_id):03d}", lessons_root / f"{lesson_id:03d}"
    work.mkdir(parents=True, exist_ok=True)
    plan = speakable(load_plan(source["plan_json"]))
    _save(work / "plan.json", plan.model_dump())
    for name in ("sources.json", "fontes.md"):
        if (src / name).exists():
            shutil.copy2(src / name, work / name)
    store.update_lesson(lesson_id, title=plan.title, plan=plan.model_dump(), status="planejada",
                        report={"source_lesson": int(source_id), "engine": ENGINE})
    return lesson_id


# ---- steps ------------------------------------------------------------------------------------------------------
def plan_step(gateway, store, lesson_id, work, report, mode="economico", log=print):
    """plan.json, or the planner (MotionPlan) with the fact gate G1 and the lint G2."""
    from sotawhat.lessons.pack import pack_markdown
    from sotawhat.lessons.pipeline import PLAN_MODELS, source_pack

    path = work / "plan.json"
    if path.exists():
        return load_plan(path.read_text(encoding="utf-8"))
    pack = source_pack(store, store.get_lesson(lesson_id), work)
    log("planejando o roteiro…")
    t = time.monotonic()
    plan, problems = make_plan(gateway, pack, models=PLAN_MODELS[mode], schema=MotionPlan)
    facts = check_facts(gateway, plan, pack)
    gates = report.setdefault("gates", {})
    gates["G1_first"] = [f"{p.sentence}: {p.issue}" for p in facts]
    if facts:
        log(f"  checagem de fatos: {len(facts)} frase(s) a revisar")
        plan, problems = revise_plan(gateway, plan, pack, facts, models=PLAN_MODELS[mode])
        gates["G1_after"] = [f"{p.sentence}: {p.issue}" for p in check_facts(gateway, plan, pack)]
    gates["G2"] = problems
    speakable(plan)
    path.write_text(plan.model_dump_json(indent=1), encoding="utf-8")
    (work / "fontes.md").write_text(pack_markdown(pack, plan), encoding="utf-8")
    store.update_lesson(lesson_id, title=plan.title, plan=plan.model_dump(), status="planejada")
    report.setdefault("timings", {})["plano"] = round(time.monotonic() - t, 1)
    return plan


def narrate_step(settings, work, plan, ffmpeg, log=print) -> dict:
    """ElevenLabs narration (cached per scene) -> the timeline saved in narracao.json; `billed_total` adds up the
    credits charged for this lesson over all its runs (a scene whose text changed is charged again)."""
    out = work / "narracao.json"
    voice_dir = work / "voz"
    sentences = [[b.narration for b in scene.beats] for scene in plan.scenes]
    el = eleven.ElevenLabs(settings.elevenlabs_api_key)
    nar = eleven.narrate(el, sentences, voice_dir, ffmpeg, intro=INTRO_S, voice=settings.sotawhat_elevenlabs_voice,
                         model=settings.sotawhat_elevenlabs_model, progress=log)
    data = {"wav": str(nar.wav), "duration": nar.duration, "intro": INTRO_S, "scenes": nar.scenes,
            "chars": nar.chars, "credits": nar.credits, "billed_chars": nar.billed_chars,
            "voice": f"elevenlabs:{settings.sotawhat_elevenlabs_voice}", "model": settings.sotawhat_elevenlabs_model}
    data["billed_total"] = (_load(out, {}) or {}).get("billed_total", 0) + nar.billed_chars
    _save(out, data)
    return data


def storyboard_step(gateway, work, plan, log=print) -> Storyboard:
    path = work / "storyboard.json"
    sentences = [[b.narration for b in scene.beats] for scene in plan.scenes]
    if path.exists():                    # the repairs of validate() are idempotent: newer rules reach old boards
        board = Storyboard.model_validate_json(path.read_text(encoding="utf-8"))
        validate(board, sentences, planned_templates(plan))
        return board
    t = time.monotonic()
    board, problems = make_storyboard(gateway, plan, sentences)
    if problems:
        log("[storyboard] problemas que ficaram:\n- " + "\n- ".join(problems))
    path.write_text(board.model_dump_json(indent=1), encoding="utf-8")
    log(f"[storyboard] {len(board.scenes)} cenas em {time.monotonic() - t:.0f} s: "
        + ", ".join(s.template for s in board.scenes))
    return board


def project_key(project) -> str:
    """What the render depends on: the composed project (compositions, kit, narration track)."""
    project = Path(project)
    files = sorted(list((project / "compositions").glob("*.html")) + list((project / "assets" / "kit").glob("*"))
                   + [project / "index.html", project / "assets" / "narration.wav"])
    digest = hashlib.sha256()
    for f in files:
        if f.is_file():
            digest.update(f.relative_to(project).as_posix().encode())
            digest.update(hashlib.sha256(f.read_bytes()).digest())
    return digest.hexdigest()[:20]


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


def price(settings, store, report, nar) -> dict:
    """LLM + voice in US$ and R$ (PTAX): the fields of the report that the delivery and the page show."""
    from sotawhat import fx

    llm = round(sum(store.llm_cost_for_run(r) for r in report.get("runs", [])), 4)
    credits = int(nar.get("billed_total") or 0)
    voice_usd = eleven.credits_usd(credits, settings.sotawhat_elevenlabs_plan_usd, settings.sotawhat_elevenlabs_plan_credits)
    total = round(llm + voice_usd, 4)
    out = {"llm_usd": llm, "voice": {"credits": credits, "usd": voice_usd,
                                     "plan": [settings.sotawhat_elevenlabs_plan_usd, settings.sotawhat_elevenlabs_plan_credits]},
           "cost_usd": total, "cost_brl": None, "ptax": None}
    rate = fx.usd_brl(store)
    if rate is not None:
        out.update(cost_brl=rate.convert(total), ptax={"brl": rate.brl, "day": rate.day, "source": rate.source})
    return out


# ---- the run ----------------------------------------------------------------------------------------------------
def forget(work, redo) -> None:
    """Throws away the steps to redo. `plano` takes the storyboard with it; `voz` is charged again."""
    if "plano" in redo:
        for name in ("plan.json", "storyboard.json"):
            (work / name).unlink(missing_ok=True)
    if "storyboard" in redo:
        (work / "storyboard.json").unlink(missing_ok=True)
    if "voz" in redo:
        shutil.rmtree(work / "voz", ignore_errors=True)
    if "3d" in redo:
        shutil.rmtree(work / "3d", ignore_errors=True)


def run_motion_lesson(settings, store, lesson_id, deliver=True, redo=(), mode="economico", log=print,
                      fresh_budget=False) -> int:
    """Runs (or resumes) lesson `lesson_id` in the HyperFrames engine. -> exit code."""
    from sotawhat.lessons import hyperframes as hfm
    from sotawhat.lessons.pipeline import _gateway, lessons_root, send
    from sotawhat.lessons.tools import Tools

    hf, tools = hfm.hf_tools(settings), Tools.from_settings(settings)
    if not hf.ready():
        log(f"HyperFrames incompleto em {hf.root}: instale com npm (veja a seção Animated lessons do README)")
        return 2
    if not Path(tools.ffmpeg()).exists():
        log("FFmpeg das aulas não encontrado: rode `sotawhat lessons setup`")
        return 2
    if not settings.elevenlabs_api_key:
        log("ELEVENLABS_API_KEY vazia no .env: a voz das aulas é a ElevenLabs")
        return 2
    work = lessons_root(settings) / f"{int(lesson_id):03d}"
    work.mkdir(parents=True, exist_ok=True)
    forget(work, redo)
    report = json.loads(store.get_lesson(lesson_id)["report_json"] or "{}")
    report["engine"] = ENGINE
    report.setdefault("runs", [])
    previous = 0.0 if fresh_budget else float(report.get("llm_usd") or 0.0)
    run_id = store.start_run("lesson")
    report["runs"].append(run_id)
    store.update_lesson(lesson_id, run_id=run_id, error=None, report=report)
    timings = report.setdefault("timings", {})
    started = time.monotonic()
    try:
        gateway = _gateway(settings, store, run_id, previous, mode)
        plan = plan_step(gateway, store, lesson_id, work, report, mode=mode, log=log)
        log(f"roteiro: “{plan.title}” · {len(plan.scenes)} cenas: "
            + ", ".join(getattr(s, "template", s.mode) for s in plan.scenes) + f" · {len(plan.quiz)} perguntas")
        t = time.monotonic()
        board = storyboard_step(gateway, work, plan, log=log)
        report["storyboard"] = {"templates": [s.template for s in board.scenes]}
        timings["storyboard"] = round(time.monotonic() - t, 1)
        t = time.monotonic()
        nar = narrate_step(settings, work, plan, tools.ffmpeg(), log=log)
        report["narration"] = {"seconds": round(nar["duration"], 1), "chars": nar["chars"], "credits": nar["credits"],
                               "billed_total": nar["billed_total"], "voice": nar["voice"], "model": nar["model"]}
        store.update_lesson(lesson_id, status="narrada")
        timings["voz"] = round(time.monotonic() - t, 1)
        t = time.monotonic()
        free = three3d.code_step(gateway, tools, hf, work, plan, board, nar, log=log)
        if free["scenes"]:
            report["free3d"] = {str(n): r for n, r in free["scenes"].items()}
            timings["3d"] = round(time.monotonic() - t, 1)
            t = time.monotonic()
        layout = hfm.compose(hf, work / "hf", plan, board, nar, lesson_id, codes=free["codes"])
        key = project_key(work / "hf")
        checked = hfm.check(hf, work / "hf")
        report["check"] = {"ok": checked["ok"], "errors": checked["errors"][:30], "warnings": checked["warnings"][:30]}
        timings["check"] = round(time.monotonic() - t, 1)
        log(f"[check] {'ok' if checked['ok'] else 'com erros'}: {len(checked['errors'])} erros, "
            f"{len(checked['warnings'])} avisos")
        if "video" not in redo and report.get("render_key") == key and (work / "aula.mp4").exists() and report.get("video"):
            log("[render] nada mudou desde o último vídeo: mantido")
            video = report["video"]
        else:
            video = render_step(settings, work, hf, tools, log=log)
            report["render_key"] = key
            timings["render"] = video["render_s"]
        report["video"] = video
        try:
            report["interactive"] = interactive.build(hf, tools.ffmpeg(), work, plan, board, nar, lesson_id, free["codes"])
            if report["interactive"]:
                log(f"[3D interativo] {report['interactive']['path']} · {report['interactive']['bytes'] / 1e6:.1f} MB")
        except Exception as exc:      # noqa: BLE001 - the video stands without its interactive page
            report["interactive"] = {"error": str(exc)[:300]}
            log(f"[3D interativo] não saiu: {str(exc)[:200]}")
    except Exception as exc:      # noqa: BLE001 - any step failure is recorded on the lesson and the run
        store.update_lesson(lesson_id, status="falhou", error=str(exc)[:500], report=report)
        store.finish_run(run_id, False, {"lesson": lesson_id}, error=str(exc)[:500])
        log(f"[aula {lesson_id}] parou: {exc}\nretome com: sotawhat lessons resume {lesson_id}")
        return 1
    report.update(price(settings, store, report, nar))
    report.update(total_s=round(time.monotonic() - started, 1),
                  scenes={str(n): {"template": s["template"], "ok": True,
                                   "fallback": n in free["fallback"]} for n, s in enumerate(layout["scenes"], 1)})
    _save(work / "report.json", report)
    store.update_lesson(lesson_id, status="pronta", video_path=str(work / "aula.mp4"), duration_s=video["seconds"],
                        size_bytes=video["bytes"], cost_usd=report["cost_usd"], voice=report["narration"]["voice"],
                        report=report)
    store.finish_run(run_id, True, {"lesson": lesson_id, "cost_usd": report["llm_usd"]})
    brl = f" (R$ {report['cost_brl']:.2f})".replace(".", ",") if report.get("cost_brl") is not None else ""
    log(f"[aula {lesson_id}] pronta: {video['seconds']:.0f} s · {video['bytes'] / 1e6:.1f} MB · "
        f"US$ {report['cost_usd']:.3f}{brl} (LLM {report['llm_usd']:.3f} + voz {report['voice']['credits']} créditos)"
        f"\n[vídeo] {work / 'aula.mp4'}\n[NotebookLM] {work / 'fontes.md'}")
    return send(settings, store, lesson_id, log) if deliver else 0


def remake(settings, store, source_id, lesson_id=None, deliver=True, redo=(), log=print) -> int:
    """`lessons hf <id>`: an older lesson (its plan and sources) made again in this engine."""
    from sotawhat.lessons.pipeline import lessons_root

    if lesson_id is None:
        lesson_id = prepare(settings, store, source_id, lessons_root(settings))
        log(f"aula #{lesson_id}: a aula {source_id} refeita no motor HyperFrames")
    return run_motion_lesson(settings, store, lesson_id, deliver=deliver, redo=redo, log=log, fresh_budget=bool(redo))
