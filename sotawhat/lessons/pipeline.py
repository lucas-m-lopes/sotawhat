# sotawhat/lessons/pipeline.py
"""`sotawhat lessons`: make a lesson from a topic (or from the strongest weekly trend), resume it where it stopped,
re-render it with another voice (no LLM), deliver it, export the source pack for NotebookLM, run the blind voice
test. Everything a step produces stays in data/lessons/<id>/, so a step that already finished is never redone."""
import json
import random
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from sotawhat.lessons import assemble as asm
from sotawhat.lessons.coder import build_scene
from sotawhat.lessons.deliver import clock
from sotawhat.lessons.pack import Pack, build_pack, pack_markdown, pick_topic
from sotawhat.lessons.plan import LessonPlan, check_facts, make_plan, revise_plan
from sotawhat.lessons.render import RenderError
from sotawhat.lessons.tools import Tools, media_seconds, sync_kit
from sotawhat.lessons.voice import (DEFAULT_VOICE, GOOGLE_VOICES, SAMPLE, VoiceError, beat_paths, engine_for,
                                    load_glossary, narrate, parse_voice)
from sotawhat.llm.tasks import DEEPSEEK_FLASH, KIMI_PRO, MIMO_PRO

PLAN_MODELS = {"economico": None, "equilibrado": (KIMI_PRO, DEEPSEEK_FLASH, MIMO_PRO)}
TITLE_S, END_S = 4.0, 4.0
LLM_TIMEOUT_S = 900.0
SCENE_WORKERS = 3


class LessonError(Exception):
    pass


def lessons_root(settings) -> Path:
    return (Path(settings.sotawhat_data_dir) / "lessons").resolve()


def lesson_dir(settings, lesson_id) -> Path:
    return lessons_root(settings) / f"{int(lesson_id):03d}"


def choose_voice(settings, store, explicit=None) -> str:
    return explicit or settings.sotawhat_lesson_voice or store.meta_get("lesson_voice") or DEFAULT_VOICE


def _save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _load(path, default):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def make_lesson(settings, store, gateway, tools, lesson_id, voice, mode="economico", log=print) -> dict:
    """Runs (or resumes) every step of lesson `lesson_id`. -> the lesson report."""
    lesson = store.get_lesson(lesson_id)
    root = lessons_root(settings)
    kit_dir, cache = sync_kit(root), root / "_cache"
    work = lesson_dir(settings, lesson_id)
    work.mkdir(parents=True, exist_ok=True)
    report = _load(work / "report.json", {"scenes": {}, "timings": {}, "gates": {}, "runs": []})
    if gateway.run_id not in report["runs"]:
        report["runs"].append(gateway.run_id)
    store.update_lesson(lesson_id, voice=voice, run_id=gateway.run_id, error=None)
    started = time.monotonic()

    def lap(name, since):
        report["timings"][name] = round(report["timings"].get(name, 0) + time.monotonic() - since, 1)
        _save(work / "report.json", report)

    # 1. source pack ------------------------------------------------------------------------------
    if (work / "sources.json").exists():
        pack = Pack.from_json((work / "sources.json").read_text(encoding="utf-8"))
    else:
        pack = build_pack(store, lesson["topic"], json.loads(lesson["entities_json"]))
        if not pack.sources and not pack.entities:
            raise LessonError(f"nada no grafo sobre “{lesson['topic']}”: passe --entidade ou outro tema")
        (work / "sources.json").write_text(pack.to_json(), encoding="utf-8")
        if not json.loads(lesson["entities_json"]):
            store.conn.execute("UPDATE lessons SET entities_json = ? WHERE id = ?",
                               (json.dumps([e["id"] for e in pack.entities]), lesson_id))
            store.conn.commit()
    # 2. plan, G2 lint and G1 facts ---------------------------------------------------------------
    t = time.monotonic()
    if (work / "plan.json").exists():
        plan = LessonPlan.model_validate_json((work / "plan.json").read_text(encoding="utf-8"))
    else:
        log("planejando o roteiro…")
        plan, problems = make_plan(gateway, pack, models=PLAN_MODELS[mode])
        facts = check_facts(gateway, plan, pack)
        report["gates"]["G1_first"] = [f"{p.sentence}: {p.issue}" for p in facts]
        if facts:
            log(f"  checagem de fatos: {len(facts)} frase(s) a revisar")
            plan, problems = revise_plan(gateway, plan, pack, facts, models=PLAN_MODELS[mode])
            report["gates"]["G1_after"] = [f"{p.sentence}: {p.issue}" for p in check_facts(gateway, plan, pack)]
        report["gates"]["G2"] = problems
        (work / "plan.json").write_text(plan.model_dump_json(indent=1), encoding="utf-8")
        store.update_lesson(lesson_id, title=plan.title, plan=plan.model_dump(), status="planejada")
        lap("plano", t)
    log(f"roteiro: “{plan.title}” · {len(plan.scenes)} cenas ({sum(s.mode == 'three' for s in plan.scenes)} em 3D)"
        f" · {len(plan.quiz)} perguntas")
    # 3. narration --------------------------------------------------------------------------------
    t = time.monotonic()
    engine = engine_for(voice, tools, settings)
    glossary = load_glossary(Path(settings.sotawhat_config_dir) / "lessons_glossary.yaml")
    durations = narrate(engine, plan, work / "audio", glossary)
    _save(work / "durations.json", durations)
    store.update_lesson(lesson_id, status="narrada")
    lap("narração", t)
    # 4. scenes: SCENE_WORKERS at a time (the LLM answers in minutes; the renders interleave) ------
    paths = beat_paths(work / "audio", plan)
    todo = [n for n in range(1, len(plan.scenes) + 1)
            if not (report["scenes"].get(str(n)) and (work / "scenes" / f"{n:02d}" / "out.mp4").exists())]
    lock = threading.Lock()

    def one(n):
        log(f"cena {n}/{len(plan.scenes)} ({plan.scenes[n - 1].mode}): {plan.scenes[n - 1].title}")
        result = build_scene(gateway, tools, root, work / "scenes" / f"{n:02d}", kit_dir, cache, plan, n,
                             durations[n - 1], log=log)
        with lock:
            report["scenes"][str(n)] = result
            _save(work / "report.json", report)

    t = time.monotonic()
    with ThreadPoolExecutor(max_workers=SCENE_WORKERS) as pool:
        for future in [pool.submit(one, n) for n in todo]:
            future.result()             # the first exception (budget, credits) stops the lesson
    if todo:
        lap("cenas", t)
    for n in range(1, len(plan.scenes) + 1):
        scene_dir = work / "scenes" / f"{n:02d}"
        seconds = media_seconds(tools, scene_dir / "out.mp4")
        report["scenes"][str(n)]["seconds"] = seconds
        asm.scene_audio(paths[n - 1], durations[n - 1], scene_dir / "audio.wav", video_seconds=seconds)
    store.update_lesson(lesson_id, status="renderizada")
    # 5. cards, track, video ----------------------------------------------------------------------
    t = time.monotonic()
    day = datetime.now().strftime("%d/%m/%Y")
    title = asm.render_card(tools, work / "cards", kit_dir, cache, "title", plan.title, [plan.objective, day], TITLE_S)
    end = asm.render_card(tools, work / "cards", kit_dir, cache, "end", "Agora, o quiz",
                          [f"{len(plan.quiz)} perguntas no Telegram; o re-quiz vem em 2 dias.",
                           f"Fontes: {', '.join(s.title[:40] for s in pack.sources[:3]) or 'conhecimento canônico'}"],
                          END_S)
    scene_dirs = [work / "scenes" / f"{n:02d}" for n in range(1, len(plan.scenes) + 1)]
    parts = [(None, media_seconds(tools, title))]
    parts += [(d / "audio.wav", report["scenes"][str(n)]["seconds"]) for n, d in enumerate(scene_dirs, 1)]
    parts.append((None, media_seconds(tools, end)))
    asm.concat_wav(parts, work / "aula.wav")
    video = asm.encode(tools, [title] + [d / "out.mp4" for d in scene_dirs] + [end], work / "aula.wav",
                       work / "aula.mp4", max_mb=settings.sotawhat_lesson_max_mb)
    report["video"] = video
    (work / "fontes.md").write_text(pack_markdown(pack, plan), encoding="utf-8")
    lap("montagem", t)
    cost = round(sum(store.llm_cost_for_run(r) for r in report["runs"]), 4)
    report.update(cost_usd=cost, voice=voice, mode=mode, total_s=round(time.monotonic() - started, 1),
                  fallbacks=sum(1 for s in report["scenes"].values() if s.get("fallback")),
                  first_try=sum(1 for s in report["scenes"].values() if s.get("attempts") == 1 and s.get("ok")))
    _save(work / "report.json", report)
    store.update_lesson(lesson_id, status="pronta", video_path=str(work / "aula.mp4"), duration_s=video["seconds"],
                        size_bytes=video["bytes"], cost_usd=cost, report=report)
    return report


def rerender(settings, store, tools, lesson_id, voice):
    """New voice for a finished lesson: new narration, the scenes rendered again from their code (no LLM, unless a
    scene no longer renders), new assembly."""
    work = lesson_dir(settings, lesson_id)
    shutil.rmtree(work / "audio", ignore_errors=True)
    report = _load(work / "report.json", {"scenes": {}})
    for scene_dir in sorted((work / "scenes").glob("*")):
        (scene_dir / "out.mp4").unlink(missing_ok=True)
    report["scenes"] = {}
    _save(work / "report.json", report)


def _gateway(settings, store, run_id, previous_cost):
    from sotawhat.configfiles import load_config
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient

    if not settings.openrouter_api_key:
        raise LessonError("OPENROUTER_API_KEY vazio no .env")
    # a storyboard with high reasoning takes minutes and the answer only comes at the end: 120 s cut it off
    client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                              app_title=settings.openrouter_app_title, timeout=LLM_TIMEOUT_S)
    budget = max(0.05, settings.sotawhat_llm_budget_usd_lesson - previous_cost)
    return LLMGateway(client, store=store, settings=settings, run_id=run_id,
                      tasks=load_config(settings.sotawhat_config_dir).llm.get("tasks"), budget_run=budget)


def run_lesson(settings, store, tools, lesson_id, voice, mode, deliver, log=print) -> int:
    from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
    from sotawhat.llm.openrouter import InsufficientCredits

    lesson = store.get_lesson(lesson_id)
    previous = json.loads(lesson["report_json"] or "{}").get("cost_usd") or 0.0
    run_id = store.start_run("lesson")
    gateway = _gateway(settings, store, run_id, previous)
    try:
        report = make_lesson(settings, store, gateway, tools, lesson_id, voice, mode=mode, log=log)
    except (LessonError, BudgetExceeded, InsufficientCredits, LLMFailure, RenderError, VoiceError, RuntimeError) as exc:
        store.update_lesson(lesson_id, status="falhou", error=str(exc)[:500])
        store.finish_run(run_id, False, {"lesson": lesson_id}, error=str(exc)[:500])
        log(f"[aula {lesson_id}] parou: {exc}\nretome com: sotawhat lessons resume {lesson_id}")
        return 1
    store.finish_run(run_id, True, {"lesson": lesson_id, "cost_usd": report["cost_usd"]})
    video = report["video"]
    log(f"[aula {lesson_id}] pronta: {clock(video['seconds'])} · {video['bytes'] / 1e6:.1f} MB · US$ {report['cost_usd']:.3f}"
        f" · {report['first_try']}/{len(report['scenes'])} cenas na 1ª tentativa · {report['fallbacks']} slide(s)"
        f"\n[vídeo] {lesson_dir(settings, lesson_id) / 'aula.mp4'}\n[NotebookLM] {lesson_dir(settings, lesson_id) / 'fontes.md'}")
    if deliver:
        return send(settings, store, lesson_id, log)
    return 0


def send(settings, store, lesson_id, log=print) -> int:
    from sotawhat.lessons.deliver import send_lesson
    from sotawhat.notify.telegram import TelegramError, TelegramNotifier

    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if not notifier.configured:
        log("Telegram não configurado (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")
        return 2
    try:
        send_lesson(store, notifier, lesson_id)
    except TelegramError as exc:
        log(f"[telegram] {exc}")
        return 1
    log(f"[telegram] aula {lesson_id} enviada com o quiz")
    return 0


def voice_test(settings, store, tools, deliver=True, log=print) -> int:
    """Blind test: the same jargon-heavy paragraph in every available voice, in shuffled order (A, B, C…)."""
    from sotawhat.lessons.deliver import VOICE_TEST_KEY
    from sotawhat.notify.telegram import TelegramNotifier

    specs = [f"piper:{v}" for v in tools.status()["voices"]]
    if settings.google_tts_api_key:
        specs += [f"google:{v}" for v in GOOGLE_VOICES]
    random.shuffle(specs)
    specs = specs[:5]
    folder = lessons_root(settings) / "_vozes"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    glossary = load_glossary(Path(settings.sotawhat_config_dir) / "lessons_glossary.yaml")
    mapping = {}
    for letter, spec in zip("ABCDE", specs):
        engine_for(spec, tools, settings).synthesize([(SAMPLE, folder / f"voz-{letter}.wav")], glossary, workdir=folder)
        mapping[letter] = spec
        log(f"voz {letter}: {folder / f'voz-{letter}.wav'}")
    store.meta_set(VOICE_TEST_KEY, json.dumps(mapping))
    (folder / "gabarito.json").write_text(json.dumps(mapping, indent=1), encoding="utf-8")
    if not deliver:
        return 0
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if not notifier.configured:
        log("Telegram não configurado: ouça os arquivos acima e defina SOTAWHAT_LESSON_VOICE no .env")
        return 0
    notifier.send_message("🎙️ Teste cego de vozes para as aulas: ouça o mesmo trecho nas vozes abaixo e vote na melhor.")
    for letter in mapping:
        notifier.send_audio(folder / f"voz-{letter}.wav", title=f"Voz {letter}", caption=f"Voz {letter}")
    notifier.send_message("Qual voz fica nas aulas?", reply_markup={"inline_keyboard": [[
        {"text": f"Voz {letter}", "callback_data": f"v:{letter}"} for letter in mapping]]})
    log(f"[telegram] {len(mapping)} vozes enviadas")
    return 0


def print_list(store, log=print) -> None:
    rows = store.list_lessons()
    if not rows:
        log("nenhuma aula ainda: sotawhat lessons make --tema \"…\"")
    for r in rows:
        r0, n0 = store.lesson_score(r["id"], 0)
        r1, n1 = store.lesson_score(r["id"], 1)
        quiz = (f" · quiz {r0}/{n0}" if n0 else "") + (f" · re-quiz {r1}/{n1}" if n1 else "")
        log(f"#{r['id']} [{r['status']}] {r['title'] or r['topic']} · {clock(r['duration_s'] or 0)} · "
            f"US$ {r['cost_usd'] or 0:.3f}{quiz}" + (f" · revisão {r['review']}" if r["review"] else "")
            + (f" · vs NotebookLM {r['comparison']}" if r["comparison"] else "") + (f" · erro: {r['error'][:80]}" if r["error"] else ""))


def main_lessons(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.lessons.tools import setup
    from sotawhat.store.db import Store

    settings = load_settings()
    tools = Tools.from_settings(settings)
    log = print
    if ns.lessons_action == "setup":
        return 0 if setup(tools, log=log) else 1
    if ns.lessons_action in ("make", "resume", "rerender", "voices") and not tools.ready():
        log("ferramentas das aulas incompletas: rode `sotawhat lessons setup`")
        return 2
    with Store(settings.db_path) as store:
        if ns.lessons_action == "list":
            print_list(store, log)
            return 0
        if ns.lessons_action == "voices":
            return voice_test(settings, store, tools, deliver=not ns.no_send, log=log)
        if ns.lessons_action == "make":
            if ns.auto:
                picked = pick_topic(store)
                if picked is None:
                    log("nenhuma tendência nova com fontes suficientes no último weekly")
                    return 1
                topic, entities = picked
                log(f"tema escolhido pelo seletor: {topic}")
            elif ns.tema:
                topic, entities = ns.tema, ns.entidade or []
            else:
                log("passe --tema \"…\" (com --entidade ID opcional) ou --auto")
                return 2
            lesson_id = store.create_lesson(topic, entities)
            log(f"aula #{lesson_id}: {topic}")
        else:
            lesson_id = ns.id
            if store.get_lesson(lesson_id) is None:
                log(f"aula {lesson_id} não existe")
                return 1
        voice = choose_voice(settings, store, getattr(ns, "voz", None))
        parse_voice(voice)
        if ns.lessons_action == "send":
            return send(settings, store, lesson_id, log)
        if ns.lessons_action == "pack":
            work = lesson_dir(settings, lesson_id)
            pack = Pack.from_json((work / "sources.json").read_text(encoding="utf-8"))
            plan = LessonPlan.model_validate_json((work / "plan.json").read_text(encoding="utf-8")) \
                if (work / "plan.json").exists() else None
            (work / "fontes.md").write_text(pack_markdown(pack, plan), encoding="utf-8")
            log(f"[NotebookLM] {work / 'fontes.md'}: suba no NotebookLM e peça um Video Overview (Explainer, pt-BR)")
            return 0
        if ns.lessons_action == "rerender":
            rerender(settings, store, tools, lesson_id, voice)
        deliver = ns.lessons_action in ("make", "resume") and not ns.no_send
        return run_lesson(settings, store, tools, lesson_id, voice, getattr(ns, "modo", "economico") or "economico",
                          deliver, log=log)


