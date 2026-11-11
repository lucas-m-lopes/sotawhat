# sotawhat/lessons/deliver.py
"""Telegram for the lessons: the video, its quiz (inline buttons; the first answer counts), your review (G8) and
the comparison with the NotebookLM Video Overview, the re-quiz days later (retrieval practice) and the blind voice
test. Callback data: q:<lesson>:<round>:<question>:<option> · l:<lesson>:<ok|erro|melhor|empate|pior> · v:<A–E>."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sotawhat.lessons.plan import load_plan
from sotawhat.notify.telegram import TelegramError, esc
from sotawhat.store.db import utcnow

LETTERS = "ABCD"
REVIEW = {"ok": "✅ sem erros", "erro": "⚠️ tem erro"}
COMPARE = {"melhor": "🏆 melhor que o NotebookLM", "empate": "🤝 empate", "pior": "📉 pior"}
VOICE_TEST_KEY, VOICE_KEY = "lesson_voice_test", "lesson_voice"
_QUIZ = re.compile(r"q:(\d+):([01]):(\d+):(\d)")
_REVIEW = re.compile(r"l:(\d+):(ok|erro|melhor|empate|pior)")
_VOICE = re.compile(r"v:([A-E])")


def clock(seconds) -> str:
    seconds = int(round(seconds or 0))
    return f"{seconds // 60}:{seconds % 60:02d}"


def cost_text(cost_usd, report) -> str:
    """"US$ 0,49 (R$ 2,73)": the total of the lesson (LLM + voice), in reais at the PTAX when known."""
    text = f"US$ {cost_usd or 0:.2f}".replace(".", ",")
    if report.get("cost_brl") is not None:
        text += f" (R$ {report['cost_brl']:.2f})".replace(".", ",")
    return text


def quiz_text(item, n, total, round_) -> str:
    head = "🔁 Re-quiz" if round_ else "❓ Quiz"
    options = "\n".join(f"{LETTERS[i]}) {esc(o)}" for i, o in enumerate(item.options))
    return f"{head} {n + 1}/{total}: <b>{esc(item.question)}</b>\n{options}"


def quiz_keyboard(lesson_id, round_, n, options) -> dict:
    return {"inline_keyboard": [[{"text": LETTERS[i], "callback_data": f"q:{lesson_id}:{round_}:{n}:{i}"}
                                 for i in range(len(options))]]}


def review_keyboard(lesson_id, review=None, comparison=None) -> dict:
    def button(code, text, chosen):
        return {"text": ("✓ " if chosen == code else "") + text, "callback_data": f"l:{lesson_id}:{code}"}
    return {"inline_keyboard": [[button(c, t, review) for c, t in REVIEW.items()],
                                [button(c, t, comparison) for c, t in COMPARE.items()]]}


def send_quiz(notifier, lesson_id, plan, round_=0) -> int:
    for n, item in enumerate(plan.quiz):
        notifier.send_message(quiz_text(item, n, len(plan.quiz), round_),
                              reply_markup=quiz_keyboard(lesson_id, round_, n, item.options), disable_notification=n > 0)
    return len(plan.quiz)


def send_lesson(store, notifier, lesson_id) -> None:
    lesson = store.get_lesson(lesson_id)
    plan = load_plan(lesson["plan_json"])
    report = json.loads(lesson["report_json"] or "{}")
    height = (report.get("video") or {}).get("height", 1080)
    page = (report.get("interactive") or {}).get("path")
    page = page if page and Path(page).exists() else None
    if report.get("engine") != "hyperframes":
        tail = "Quiz e revisão logo abaixo; cenas 3D interativas em http://127.0.0.1:8765/#aulas"
    else:
        tail = "3D interativo, quiz e revisão logo abaixo." if page else "Quiz e revisão logo abaixo."
    caption = (f"🎓 <b>{esc(plan.title)}</b>\n{esc(plan.objective)}\n⏱ {clock(lesson['duration_s'])} · "
               f"{len(plan.scenes)} cenas · {cost_text(lesson['cost_usd'], report)}\n" + tail)
    notifier.send_video(lesson["video_path"], caption=caption[:1024], duration=lesson["duration_s"],
                        width=1920 if height == 1080 else 1280, height=height)
    if page:
        scenes = (report.get("interactive") or {}).get("scenes") or []
        try:
            notifier.send_document(page, name=f"aula-{int(lesson_id):03d}-3d-interativo.html", disable_notification=True,
                                   caption=f"🧊 <b>3D interativo</b> · {len(scenes)} cena(s) · abra no navegador: "
                                           "ouça a cena, arraste para girar, pinça para aproximar")
        except TelegramError as exc:   # the video and the quiz still go; the page is also on the Aulas tab
            report["interactive"]["error"] = f"Telegram: {exc}"[:300]
            store.update_lesson(lesson_id, report=report)
    send_quiz(notifier, lesson_id, plan, 0)
    notifier.send_message("Sua revisão desta aula (o checklist está na página da aula) e a comparação com o Video "
                          "Overview do NotebookLM gerado do fontes.md:", reply_markup=review_keyboard(lesson_id),
                          disable_notification=True)
    store.update_lesson(lesson_id, status="entregue", delivered_at=utcnow())


def _answer(notifier, query, text):
    try:
        notifier.answer_callback(query["id"], text)
    except TelegramError:
        pass


def _edit(notifier, query, text=None, markup=None):
    message = query.get("message") or {}
    chat, message_id = (message.get("chat") or {}).get("id"), message.get("message_id")
    if chat is None or not message_id:
        return
    try:
        if text is not None:
            notifier.edit_message_text(chat, message_id, text, reply_markup=markup)
        else:
            notifier.edit_reply_markup(chat, message_id, markup)
    except TelegramError:
        pass   # too old to edit, or nothing changed


def handle_callback(store, notifier, query):
    """A lesson button -> "quiz" | "review" | "voice"; None when the button is not about lessons."""
    data = query.get("data") or ""
    if m := _QUIZ.fullmatch(data):
        lesson_id, round_, n, chosen = (int(x) for x in m.groups())
        lesson = store.get_lesson(lesson_id)
        if lesson is None or not lesson["plan_json"]:
            _answer(notifier, query, "aula não encontrada")
            return "quiz"
        plan = load_plan(lesson["plan_json"])
        if n >= len(plan.quiz) or chosen >= len(plan.quiz[n].options):
            _answer(notifier, query, "pergunta não encontrada")
            return "quiz"
        item = plan.quiz[n]
        right = chosen == item.answer
        if not store.record_lesson_answer(lesson_id, round_, n, chosen, right):
            _answer(notifier, query, "já respondida (vale a primeira resposta)")
            return "quiz"
        _answer(notifier, query, "✅ certo!" if right else f"❌ a resposta é {LETTERS[item.answer]}")
        verdict = "✅ você acertou" if right else f"❌ você marcou {LETTERS[chosen]}; a certa é {LETTERS[item.answer]}"
        _edit(notifier, query, f"{quiz_text(item, n, len(plan.quiz), round_)}\n\n{verdict}. {esc(item.explanation)}",
              {"inline_keyboard": []})
        score, total = store.lesson_score(lesson_id, round_)
        if total == len(plan.quiz):
            label = "re-quiz" if round_ else "quiz"
            try:
                notifier.send_message(f"📊 {label} de “{esc(plan.title)}”: {score}/{total} certas.", disable_notification=True)
            except TelegramError:
                pass
        return "quiz"
    if m := _REVIEW.fullmatch(data):
        lesson_id, code = int(m.group(1)), m.group(2)
        lesson = store.get_lesson(lesson_id)
        if lesson is None:
            _answer(notifier, query, "aula não encontrada")
            return "review"
        if code in REVIEW:
            store.update_lesson(lesson_id, review=code)
        else:
            store.update_lesson(lesson_id, comparison=code)
        lesson = store.get_lesson(lesson_id)
        _answer(notifier, query, "registrado")
        _edit(notifier, query, markup=review_keyboard(lesson_id, lesson["review"], lesson["comparison"]))
        return "review"
    if m := _VOICE.fullmatch(data):
        mapping = json.loads(store.meta_get(VOICE_TEST_KEY) or "{}")
        spec = mapping.get(m.group(1))
        if not spec:
            _answer(notifier, query, "teste de vozes não encontrado")
            return "voice"
        store.meta_set(VOICE_KEY, spec)
        _answer(notifier, query, f"voz {m.group(1)} escolhida para as próximas aulas")
        _edit(notifier, query, f"🎙️ Escolhida a voz {m.group(1)}: {esc(spec)}", {"inline_keyboard": []})
        return "voice"
    return None


def requiz_due(store, notifier, now=None, days=2) -> int:
    """Retrieval practice: the quiz again, days after the lesson was delivered."""
    now = now or datetime.now(timezone.utc)
    sent = 0
    for lesson in store.lessons_due_requiz((now - timedelta(days=days)).isoformat(timespec="seconds")):
        if not lesson["plan_json"]:
            continue
        plan = load_plan(lesson["plan_json"])
        notifier.send_message(f"🔁 Re-quiz de “{esc(plan.title)}” (a aula foi há {days}+ dias): responda sem rever.")
        send_quiz(notifier, lesson["id"], plan, round_=1)
        store.update_lesson(lesson["id"], requiz_at=utcnow())
        sent += 1
    return sent
