# sotawhat/web/app.py
"""`sotawhat serve`: the graph interface (SDD §6.11, P3), a FastAPI app on 127.0.0.1 that reads SQLite.

A local server still gets requests that other web pages trigger in the browser, so:
- it only binds to 127.0.0.1, and TrustedHostMiddleware refuses any other Host header (DNS rebinding);
- the writes (votes on items and on ideas) need a JSON body (a cross-site form or a no-cors fetch
  cannot send one) and an Origin that is absent or local.
P4 adds the ideas page (/api/ideas, /api/ideas/{id}, /api/ideas/vote) and the trends panel (/api/trends).
The tools radar (2026-11-10) adds /api/radar and /api/radar/vote.
The lessons (aulas 3D) add /api/lessons and the files of data/lessons under /lessons: the videos and the
interactive pages of the 3D scenes. The glossary of the digests (2026-11-20) adds /api/glossary and
/api/glossary/status ("já sei"); the questions to the graph add /api/ask (hybrid retrieval, then the local SLM)
and /api/rag/status. The lessons made from the interface (F1, docs/superpowers/specs/2026-11-20-aulas-pela-interface-
design.md) add /api/lessons/state and /api/lessons/job (read), and POST /api/lessons (plan a new one) and
/api/lessons/{id}/plan, /produce, /send, /cancel and /discard: each starts or ends a `sotawhat lessons` process
through the launcher (lessons/launcher.py), one at a time."""
import json
import logging
import mimetypes
import os
import sys
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from sotawhat import glossary
from sotawhat.graph import query as q
from sotawhat.ideation import ledger
from sotawhat.lessons import estimate, jobs
from sotawhat.lessons.eleven import VOICE_NAMES
from sotawhat.store.db import Store

STATIC = Path(__file__).parent / "static"
LOCAL_HOSTS = ("127.0.0.1", "localhost")
log = logging.getLogger("sotawhat.web")
# the Windows registry may map .js to text/plain, and browsers refuse ES modules served that way
for _type, _ext in (("text/javascript", ".js"), ("text/javascript", ".mjs"), ("text/css", ".css"),
                    ("audio/wav", ".wav"), ("video/mp4", ".mp4"), ("text/markdown", ".md")):
    mimetypes.add_type(_type, _ext)


class Vote(BaseModel):
    item_id: str
    value: Literal["up", "down", "test"]


class IdeaVote(BaseModel):
    idea_id: int
    value: Literal["up", "down", "test", "archive", "built"]
    note: str | None = Field(default=None, max_length=300)


class ToolVote(BaseModel):
    repo: str = Field(min_length=3, max_length=200, pattern=r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$")
    value: Literal["test", "up", "down", "archive"]


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    days: int | None = Field(default=None, ge=1, le=3650)
    k: int | None = Field(default=None, ge=1, le=20)
    sources_only: bool = False
    engine: Literal["slm", "jev"] | None = None      # None: RAG_ENGINE


class NewLesson(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    entities: list[int] = Field(default_factory=list, max_length=3)
    mode: Literal["economico", "equilibrado"] = "economico"


class Production(BaseModel):
    send: bool = True            # to Telegram when it is ready (unchecked: --sem-envio)


class TermStatus(BaseModel):
    term_id: int
    status: Literal["ativo", "conhecido"]


async def json_body(request: Request) -> dict:
    """The checks every write goes through: JSON content type and a local (or absent) Origin."""
    if not request.headers.get("content-type", "").lower().startswith("application/json"):
        raise HTTPException(415, "envie JSON")
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).hostname not in LOCAL_HOSTS:
        raise HTTPException(403, "origem não permitida")
    try:
        body = json.loads(await request.body() or b"{}")
    except ValueError as exc:
        raise HTTPException(422, f"JSON inválido: {exc}") from None
    if not isinstance(body, dict):
        raise HTTPException(422, "envie um objeto JSON")
    return body


def create_app(db_path, static_dir=STATIC, rag=None, lessons=None) -> FastAPI:
    """`rag`: a callable store -> (retriever, slm, jev, settings-like with rag_sources, rag_context_chars and
    rag_engine), called at the first question (the embedding model takes seconds to load); None answers 503 on
    /api/ask. `lessons`: the launcher of lesson jobs (lessons/launcher.py); None answers 503 on the lesson actions."""
    static_dir = Path(static_dir)
    parts = {}
    rag_lock = threading.Lock()

    def rag_parts(st):
        with rag_lock:
            if "rag" not in parts:
                parts["rag"] = rag(st)
            return parts["rag"]

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = Store(db_path)
        try:
            yield
        finally:
            app.state.store.close()

    app = FastAPI(title="sotawhat", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(LOCAL_HOSTS))

    @app.middleware("http")
    async def revalidate_static(request: Request, call_next):
        # without it the browser keeps an old app.js after an update (heuristic caching); ETag makes it cheap
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    def store(request: Request) -> Store:
        return request.app.state.store

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(static_dir / "index.html", headers={"Cache-Control": "no-store"})

    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/api/stats")
    def api_stats(request: Request):
        return q.stats(store(request))

    @app.get("/api/graph")
    def api_graph(request: Request, days: int = Query(30, ge=0, le=3650), types: str = "",
                  min_mentions: int = Query(1, alias="min", ge=1, le=1000), limit: int = Query(250, ge=1, le=2000),
                  focus: str = ""):
        wanted = [t for t in types.split(",") if t] or None
        return q.graph_view(store(request), days=days or None, types=wanted, min_mentions=min_mentions, limit=limit,
                            focus=focus or None)

    @app.get("/api/entity/{entity_id}")
    def api_entity(entity_id: str, request: Request):
        detail = q.entity_detail(store(request), entity_id)
        if detail is None:
            raise HTTPException(404, "entidade não encontrada")
        return detail

    @app.get("/api/item")
    def api_item(request: Request, item_id: str = Query(..., alias="id")):
        detail = q.item_detail(store(request), item_id)
        if detail is None:
            raise HTTPException(404, "item não encontrado")
        return detail

    @app.get("/api/search")
    def api_search(request: Request, text: str = Query("", alias="q", max_length=200)):
        return q.search(store(request), text)

    @app.post("/api/feedback")
    async def api_feedback(request: Request):
        try:
            vote = Vote.model_validate(await json_body(request))
        except ValidationError as exc:
            raise HTTPException(422, f"voto inválido: {exc}") from None
        st = store(request)
        if not st.get_items([vote.item_id]):
            raise HTTPException(404, "item não encontrado")
        st.add_feedback("item", vote.item_id, vote.value, channel="web")
        return {"item_id": vote.item_id, "vote": st.item_votes(ids=[vote.item_id]).get(vote.item_id)}

    # --- today and runs (P6) ----------------------------------------------------------
    @app.get("/api/today")
    def api_today(request: Request):
        return q.today(store(request))

    @app.get("/api/runs")
    def api_runs(request: Request, limit: int = Query(15, ge=1, le=100)):
        return q.runs(store(request), limit=limit)

    # --- ideas and trends (P4) ---------------------------------------------------------
    @app.get("/api/ideas")
    def api_ideas(request: Request, status: str = "", finalists: bool = True, limit: int = Query(100, ge=1, le=500)):
        if status and status not in ledger.STATUSES:
            raise HTTPException(422, f"status inválido; use um de {', '.join(ledger.STATUSES)}")
        return ledger.list_ideas(store(request), status=status or None, finalists_only=finalists, limit=limit)

    @app.get("/api/ideas/{idea_id}")
    def api_idea(idea_id: int, request: Request):
        detail = ledger.idea_detail(store(request), idea_id)
        if detail is None:
            raise HTTPException(404, "ideia não encontrada")
        return detail

    @app.post("/api/ideas/vote")
    async def api_idea_vote(request: Request):
        try:
            vote = IdeaVote.model_validate(await json_body(request))
        except ValidationError as exc:
            raise HTTPException(422, f"voto inválido: {exc}") from None
        st = store(request)
        if st.get_idea(vote.idea_id) is None:
            raise HTTPException(404, "ideia não encontrada")
        status = st.vote_idea(vote.idea_id, vote.value, "web", note=(vote.note or "").strip() or None)
        return {"idea_id": vote.idea_id, "status": status}

    @app.get("/api/trends")
    def api_trends(request: Request):
        return ledger.trends_view(store(request))

    # --- tools radar (2026-11-10) -------------------------------------------------------
    @app.get("/api/radar")
    def api_radar(request: Request):
        from sotawhat.radar.report import radar_view
        return radar_view(store(request))

    @app.post("/api/radar/vote")
    async def api_radar_vote(request: Request):
        try:
            vote = ToolVote.model_validate(await json_body(request))
        except ValidationError as exc:
            raise HTTPException(422, f"voto inválido: {exc}") from None
        st, key = store(request), vote.repo.lower()
        if st.conn.execute("SELECT 1 FROM radar_picks WHERE full_name = ? LIMIT 1", (key,)).fetchone() is None:
            raise HTTPException(404, "ferramenta fora do radar")
        st.add_feedback("tool", key, vote.value, "web")
        return {"repo": key, "vote": vote.value}

    # --- glossary of the digests (2026-11-20) -------------------------------------------
    @app.get("/api/glossary")
    def api_glossary(request: Request, text: str = Query("", alias="q", max_length=100), status: str = ""):
        if status and status not in glossary.STATUSES:
            raise HTTPException(422, f"status inválido; use um de {', '.join(glossary.STATUSES)}")
        return glossary.view(store(request), text=text, status=status)

    @app.post("/api/glossary/status")
    async def api_glossary_status(request: Request):
        try:
            change = TermStatus.model_validate(await json_body(request))
        except ValidationError as exc:
            raise HTTPException(422, f"pedido inválido: {exc}") from None
        if not store(request).set_glossary_status(change.term_id, change.status):
            raise HTTPException(404, "termo não encontrado")
        return {"term_id": change.term_id, "status": change.status}

    # --- questions to the graph (2026-11-20) --------------------------------------------
    @app.post("/api/ask")
    async def api_ask(request: Request):
        from sotawhat.rag.answer import ask

        try:
            asked = Question.model_validate(await json_body(request))
        except ValidationError as exc:
            raise HTTPException(422, f"pergunta inválida: {exc}") from None
        if rag is None:
            raise HTTPException(503, "perguntas desligadas neste servidor")
        st = store(request)

        def work():
            retriever, slm, jev, knobs = rag_parts(st)
            with rag_lock:                          # one question at a time: one GPU, one SQLite connection
                return ask(retriever, None if asked.sources_only else slm, asked.question, days=asked.days,
                           k=asked.k or knobs.rag_sources, budget=knobs.rag_context_chars,
                           engine="slm" if asked.sources_only else (asked.engine or knobs.rag_engine), jev=jev)

        answer = await run_in_threadpool(work)
        if asked.sources_only:
            answer.error = None
        return answer.as_dict()

    @app.get("/api/rag/status")
    def api_rag_status(request: Request):
        from sotawhat.rag import index

        status = index.status(store(request))
        if rag is not None and "rag" in parts:
            _, slm, jev, knobs = parts["rag"]
            ok, detail = slm.ping()
            status["slm"] = {"ok": ok, "detail": detail, "model": slm.model}
            status["jev"] = {"ok": bool(jev is not None and jev.configured), "model": getattr(jev, "model", None),
                             "zdr": bool(getattr(jev, "zdr", False))}
            status["engine"] = knobs.rag_engine
        return status

    # --- lessons (aulas 3D) ------------------------------------------------------------
    lessons_dir = Path(db_path).parent / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/lessons", StaticFiles(directory=lessons_dir), name="lessons")

    price = lessons.price if lessons is not None else None

    def one_lesson(st, lesson_id, detail=False) -> dict:
        row = st.get_lesson(lesson_id)
        if row is None:
            raise HTTPException(404, "aula não encontrada")
        return lesson_payload(st, row, lessons_dir, detail=detail, job=jobs.last_for(st, [lesson_id]).get(lesson_id),
                              price=price)

    @app.get("/api/lessons")
    def api_lessons(request: Request, limit: int = Query(50, ge=1, le=500), discarded: bool = False):
        st = store(request)
        last = jobs.last_for(st)
        return [lesson_payload(st, row, lessons_dir, job=last.get(row["id"]), price=price)
                for row in st.list_lessons(limit) if discarded or row["status"] != "descartada"]

    @app.get("/api/lessons/state")
    def api_lessons_state(request: Request):
        """What the Aulas tab reads when it opens: the job, the voice credits, what is missing for a production,
        the suggestions of the week and how many lessons were discarded."""
        from sotawhat.lessons.pack import suggest_topics

        st = store(request)
        job = jobs.current(st) or jobs.latest(st)
        discarded = st.conn.execute("SELECT COUNT(*) FROM lessons WHERE status = 'descartada'").fetchone()[0]
        out = {"available": lessons is not None, "job": jobs.payload(job, log_lines=12) if job is not None else None,
               "credits": None, "ready": [], "telegram": False, "price": None, "suggestions": suggest_topics(st),
               "discarded": discarded, "plan_s": estimate.PLAN_S, "plan_usd": estimate.PLAN_USD}
        if lessons is not None:
            out.update(credits=lessons.credits(), ready=lessons.ready(), telegram=lessons.telegram,
                       price=list(lessons.price))
        return out

    @app.get("/api/lessons/job")
    def api_lessons_job(request: Request):
        """What the tab polls while a job runs: the live job (else the latest) with the end of its log."""
        st = store(request)
        job = jobs.current(st) or jobs.latest(st)
        return {"job": jobs.payload(job, log_lines=12) if job is not None else None}

    @app.get("/api/lessons/{lesson_id}")
    def api_lesson(lesson_id: int, request: Request):
        return one_lesson(store(request), lesson_id, detail=True)

    def launcher():
        if lessons is None:
            raise HTTPException(503, "aulas pela interface desligadas neste servidor")
        return lessons

    def start(st, lesson_id, action, args, send=None, before=None) -> dict:
        try:
            job_id = launcher().start(st, lesson_id, action, args, send=send, before=before)
        except jobs.Busy as busy:
            raise HTTPException(409, str(busy)) from None
        except OSError as exc:
            raise HTTPException(500, f"não consegui iniciar o processo: {exc}") from None
        return {"lesson": one_lesson(st, lesson_id), "job": jobs.payload(jobs.get(st, job_id))}

    def busy_check(st):
        live = jobs.current(st)
        if live is not None:
            raise HTTPException(409, str(jobs.Busy(live)))

    def editable(row):
        if row["status"] in ("entregue", "descartada"):
            raise HTTPException(409, f"esta aula está {row['status']}")

    @app.post("/api/lessons")
    async def api_lesson_new(request: Request):
        """A new lesson: it is created here (the card exists from the first second), then its plan is made by
        `sotawhat lessons resume N --so-roteiro`. No voice is spent before the review."""
        from sotawhat.lessons.pack import build_pack

        try:
            asked = NewLesson.model_validate(await json_body(request))
        except ValidationError as exc:
            raise HTTPException(422, f"aula inválida: {exc}") from None
        launcher()
        st = store(request)
        topic = " ".join(asked.topic.split())
        entities = list(dict.fromkeys(asked.entities))

        def work():
            if entities:
                known = {r[0] for r in st.conn.execute(
                    f"SELECT id FROM entities WHERE id IN ({','.join('?' * len(entities))})", entities)}
                if set(entities) - known:
                    raise HTTPException(422, f"entidade inexistente: {sorted(set(entities) - known)}")
            pack = build_pack(st, topic, entities, max_sources=2, chars=0)
            if not pack.sources and not pack.entities:
                raise HTTPException(422, f"nada no grafo sobre “{topic}”: ligue a uma entidade ou mude o tema")
            busy_check(st)
            lesson_id = st.create_lesson(topic, entities)
            st.update_lesson(lesson_id, report={"engine": "hyperframes", "mode": asked.mode})
            return start(st, lesson_id, "roteiro", ["resume", lesson_id, "--so-roteiro", "--modo", asked.mode])

        return await run_in_threadpool(work)

    @app.post("/api/lessons/{lesson_id}/plan")
    async def api_lesson_plan(lesson_id: int, request: Request):
        """Plans a lesson that has no plan, or makes its plan again. The plan kept in the database goes too, once the
        slot is ours: a "Retomar" after a failure must never produce a lesson nobody reviewed."""
        await json_body(request)
        launcher()
        st = store(request)

        def work():
            row = st.get_lesson(lesson_id)
            if row is None:
                raise HTTPException(404, "aula não encontrada")
            editable(row)
            if row["video_path"]:
                raise HTTPException(409, "esta aula já tem vídeo: o roteiro não muda mais")
            mode = json.loads(row["report_json"] or "{}").get("mode") or "economico"

            def clear():
                with st._lock:
                    st.conn.execute("UPDATE lessons SET plan_json = NULL, title = NULL, status = 'nova', error = NULL"
                                    " WHERE id = ?", (lesson_id,))
                    st.conn.commit()

            return start(st, lesson_id, "roteiro",
                         ["resume", lesson_id, "--refazer", "plano", "--so-roteiro", "--modo", mode], before=clear)

        return await run_in_threadpool(work)

    @app.post("/api/lessons/{lesson_id}/produce")
    async def api_lesson_produce(lesson_id: int, request: Request):
        """Produces a reviewed lesson, or resumes one that stopped: the steps already made come from the cache."""
        try:
            asked = Production.model_validate(await json_body(request))
        except ValidationError as exc:
            raise HTTPException(422, f"pedido inválido: {exc}") from None
        launch = launcher()
        st = store(request)

        def work():
            row = st.get_lesson(lesson_id)
            if row is None:
                raise HTTPException(404, "aula não encontrada")
            editable(row)
            if not row["plan_json"]:
                raise HTTPException(409, "esta aula ainda não tem roteiro")
            if row["status"] == "pronta":
                raise HTTPException(409, "a aula já está pronta")
            if not (lessons_dir / f"{lesson_id:03d}" / "narracao.json").exists():      # the voice still to be paid
                need = estimate.production(json.loads(row["plan_json"]), *launch.price)["credits"]
                left = (launch.credits() or {}).get("left")
                if left is not None and left < need:
                    raise HTTPException(409, f"faltam créditos de voz: a aula precisa de ~{need:,} e restam {left:,}"
                                        .replace(",", "."))
            if asked.send and not launch.telegram:
                raise HTTPException(409, "Telegram não configurado: desmarque o envio ou preencha TELEGRAM_BOT_TOKEN e"
                                         " TELEGRAM_CHAT_ID no .env")
            mode = json.loads(row["report_json"] or "{}").get("mode") or "economico"
            out = start(st, lesson_id, "aula", ["resume", lesson_id, "--modo", mode] + ([] if asked.send else ["--sem-envio"]),
                        send=asked.send)
            launch.forget_credits()
            return out

        return await run_in_threadpool(work)

    @app.post("/api/lessons/{lesson_id}/send")
    async def api_lesson_send(lesson_id: int, request: Request):
        await json_body(request)
        launch = launcher()
        st = store(request)

        def work():
            row = st.get_lesson(lesson_id)
            if row is None:
                raise HTTPException(404, "aula não encontrada")
            if not row["video_path"] or not Path(row["video_path"]).exists():
                raise HTTPException(409, "a aula ainda não tem vídeo")
            if not launch.telegram:
                raise HTTPException(409, "Telegram não configurado (TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env)")
            return start(st, lesson_id, "envio", ["send", lesson_id], send=True)

        return await run_in_threadpool(work)

    @app.post("/api/lessons/{lesson_id}/cancel")
    async def api_lesson_cancel(lesson_id: int, request: Request):
        await json_body(request)
        launch = launcher()
        st = store(request)

        def work():
            job = launch.cancel(st, lesson_id)
            if job is None:
                raise HTTPException(409, "nada rodando nesta aula")
            return {"lesson": one_lesson(st, lesson_id), "job": job}

        return await run_in_threadpool(work)

    @app.post("/api/lessons/{lesson_id}/discard")
    async def api_lesson_discard(lesson_id: int, request: Request):
        """Out of the list; the files stay on disk, and its entities go back to the suggestions."""
        await json_body(request)
        st = store(request)
        row = st.get_lesson(lesson_id)
        if row is None:
            raise HTTPException(404, "aula não encontrada")
        if row["status"] == "entregue":
            raise HTTPException(409, "uma aula entregue não se descarta")
        live = jobs.current(st)
        if live is not None and live["lesson_id"] == lesson_id:
            raise HTTPException(409, "cancele a tarefa desta aula antes de descartá-la")
        st.update_lesson(lesson_id, status="descartada")
        return {"lesson": one_lesson(st, lesson_id)}

    return app


VOICE_PROVIDERS = {"elevenlabs": "ElevenLabs", "piper": "Piper", "google": "Google"}


def voice_label(voice) -> str | None:
    """'elevenlabs:<id>' -> 'ElevenLabs · Klaus': the card showed the raw voice id."""
    if not voice:
        return None
    provider, _, name = str(voice).partition(":")
    if provider == "elevenlabs":
        name = VOICE_NAMES.get(name, "")
    label = VOICE_PROVIDERS.get(provider, provider)
    return f"{label} · {name}" if name else label


def lesson_payload(st, row, lessons_dir, detail=False, job=None, price=None) -> dict:
    """`job`: the latest lesson job of this lesson (lessons/jobs.py); `price`: (US$, credits) of the voice plan, for
    the estimate of a lesson waiting for its review."""
    plan = json.loads(row["plan_json"] or "null")
    report = json.loads(row["report_json"] or "{}")
    folder = f"{row['id']:03d}"
    scenes = (report.get("scenes") or {})
    out = {"id": row["id"], "topic": row["topic"], "title": row["title"] or row["topic"], "status": row["status"],
           "created_at": row["created_at"], "duration_s": row["duration_s"], "size_bytes": row["size_bytes"],
           "cost_usd": row["cost_usd"], "cost_brl": report.get("cost_brl"), "engine": report.get("engine") or "manim",
           "voice": row["voice"], "voice_label": voice_label(row["voice"]), "review": row["review"],
           "comparison": row["comparison"],
           "error": row["error"], "objective": (plan or {}).get("objective"),
           "video": f"/lessons/{folder}/aula.mp4" if row["video_path"] and (lessons_dir / folder / "aula.mp4").exists() else None,
           "sources_md": f"/lessons/{folder}/fontes.md" if (lessons_dir / folder / "fontes.md").exists() else None,
           "interactive": f"/lessons/{folder}/interativo.html" if (lessons_dir / folder / "interativo.html").exists() else None,
           "quiz_score": [st.lesson_score(row["id"], 0), st.lesson_score(row["id"], 1)],
           "scenes3d": [{"n": n, "title": s["title"], "url": f"/lessons/{folder}/scenes/{n:02d}/index.html"}
                        for n, s in enumerate((plan or {}).get("scenes") or [], 1)
                        if s.get("mode") == "three" and (scenes.get(str(n)) or {}).get("ok")]}
    out.update(has_plan=plan is not None, delivered_at=row["delivered_at"], mode=report.get("mode"),
               llm_usd=report.get("llm_usd"), voice_paid=(lessons_dir / folder / "narracao.json").exists(),
               job=jobs.payload(job) if job is not None else None,
               estimate=estimate.production(plan, *(price or ())) if plan and not out["video"] else None)
    if detail:
        sources = lessons_dir / folder / "sources.json"
        out.update(plan=plan, report={k: report.get(k) for k in ("gates", "timings", "scenes", "video", "fallbacks",
                                                                  "first_try", "mode", "engine", "check", "narration",
                                                                  "storyboard", "llm_usd", "voice", "cost_usd",
                                                                  "cost_brl", "ptax")},
                   sources=json.loads(sources.read_text(encoding="utf-8"))["sources"] if sources.exists() else [])
    return out


def serve(db_path, port=8765, open_browser=True, host="127.0.0.1", rag=None, lessons=None):
    """`host` is 127.0.0.1 except inside a container (SOTAWHAT_IN_CONTAINER=1), whose own network is the boundary:
    there the port is published on the host's 127.0.0.1 only (compose.vps.yaml). The Host check stays local."""
    import uvicorn

    if host not in LOCAL_HOSTS and not (host == "0.0.0.0" and os.environ.get("SOTAWHAT_IN_CONTAINER") == "1"):
        raise ValueError("a interface só escuta em 127.0.0.1")
    for name in ("stdout", "stderr"):      # pythonw (logon task) has no console
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
    url = f"http://127.0.0.1:{port}/"
    if open_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    print(f"sotawhat · interface em {url} (Ctrl+C para parar)")
    log.info("serving %s", url)
    uvicorn.run(create_app(db_path, rag=rag, lessons=lessons), host=host, port=port, log_config=None, access_log=False)


def main_serve(ns) -> int:
    from datetime import date

    from sotawhat.config import load_settings
    from sotawhat.pipeline.daily import setup_logging

    settings = load_settings()
    setup_logging(settings.sotawhat_data_dir, date.today().isoformat(), settings.sotawhat_log_level)
    def rag(store):
        from sotawhat.rag.commands import build

        return (*build(settings, store), settings)

    in_container = os.environ.get("SOTAWHAT_IN_CONTAINER") == "1"
    from sotawhat.lessons.launcher import Launcher

    # lessons are made on this computer (HyperFrames, Chrome and FFmpeg); the container serves the reading only
    lessons = None if in_container else Launcher.from_settings(settings)
    serve(settings.db_path, port=ns.port or settings.sotawhat_web_port, open_browser=not ns.no_browser and not in_container,
          host="0.0.0.0" if in_container else "127.0.0.1", rag=rag, lessons=lessons)
    return 0
