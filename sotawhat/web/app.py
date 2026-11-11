# sotawhat/web/app.py
"""`sotawhat serve`: the graph interface (SDD §6.11, P3), a FastAPI app on 127.0.0.1 that reads SQLite.

A local server still gets requests that other web pages trigger in the browser, so:
- it only binds to 127.0.0.1, and TrustedHostMiddleware refuses any other Host header (DNS rebinding);
- the writes (votes on items and on ideas) need a JSON body (a cross-site form or a no-cors fetch
  cannot send one) and an Origin that is absent or local.
P4 adds the ideas page (/api/ideas, /api/ideas/{id}, /api/ideas/vote) and the trends panel (/api/trends).
The tools radar (2026-11-10) adds /api/radar and /api/radar/vote.
The lessons (aulas 3D) add /api/lessons and the files of data/lessons under /lessons: the videos and the
interactive pages of the 3D scenes."""
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
from starlette.middleware.trustedhost import TrustedHostMiddleware

from sotawhat.graph import query as q
from sotawhat.ideation import ledger
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


def create_app(db_path, static_dir=STATIC) -> FastAPI:
    static_dir = Path(static_dir)

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

    # --- lessons (aulas 3D) ------------------------------------------------------------
    lessons_dir = Path(db_path).parent / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/lessons", StaticFiles(directory=lessons_dir), name="lessons")

    @app.get("/api/lessons")
    def api_lessons(request: Request, limit: int = Query(50, ge=1, le=500)):
        st = store(request)
        return [lesson_payload(st, row, lessons_dir) for row in st.list_lessons(limit)]

    @app.get("/api/lessons/{lesson_id}")
    def api_lesson(lesson_id: int, request: Request):
        st = store(request)
        row = st.get_lesson(lesson_id)
        if row is None:
            raise HTTPException(404, "aula não encontrada")
        return lesson_payload(st, row, lessons_dir, detail=True)

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


def lesson_payload(st, row, lessons_dir, detail=False) -> dict:
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
    if detail:
        sources = lessons_dir / folder / "sources.json"
        out.update(plan=plan, report={k: report.get(k) for k in ("gates", "timings", "scenes", "video", "fallbacks",
                                                                  "first_try", "mode", "engine", "check", "narration",
                                                                  "storyboard", "llm_usd", "voice", "cost_usd",
                                                                  "cost_brl", "ptax")},
                   sources=json.loads(sources.read_text(encoding="utf-8"))["sources"] if sources.exists() else [])
    return out


def serve(db_path, port=8765, open_browser=True, host="127.0.0.1"):
    import uvicorn

    if host not in LOCAL_HOSTS:
        raise ValueError("a interface só escuta em 127.0.0.1")
    for name in ("stdout", "stderr"):      # pythonw (logon task) has no console
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
    url = f"http://127.0.0.1:{port}/"
    if open_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    print(f"sotawhat · interface em {url} (Ctrl+C para parar)")
    log.info("serving %s", url)
    uvicorn.run(create_app(db_path), host=host, port=port, log_config=None, access_log=False)


def main_serve(ns) -> int:
    from datetime import date

    from sotawhat.config import load_settings
    from sotawhat.pipeline.daily import setup_logging

    settings = load_settings()
    setup_logging(settings.sotawhat_data_dir, date.today().isoformat(), settings.sotawhat_log_level)
    serve(settings.db_path, port=ns.port or settings.sotawhat_web_port, open_browser=not ns.no_browser)
    return 0
