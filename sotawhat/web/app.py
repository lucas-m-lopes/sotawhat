# sotawhat/web/app.py
"""`sotawhat serve`: the graph interface (SDD §6.11, P3), a FastAPI app on 127.0.0.1 that reads SQLite.

A local server still gets requests that other web pages trigger in the browser, so:
- it only binds to 127.0.0.1, and TrustedHostMiddleware refuses any other Host header (DNS rebinding);
- the only write, a vote, needs a JSON body (a cross-site form or a no-cors fetch cannot send one)
  and an Origin that is absent or local."""
import json
import logging
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
from pydantic import BaseModel, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from sotawhat.graph import query as q
from sotawhat.store.db import Store

STATIC = Path(__file__).parent / "static"
LOCAL_HOSTS = ("127.0.0.1", "localhost")
log = logging.getLogger("sotawhat.web")


class Vote(BaseModel):
    item_id: str
    value: Literal["up", "down", "test"]


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
        if not request.headers.get("content-type", "").lower().startswith("application/json"):
            raise HTTPException(415, "envie JSON")
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).hostname not in LOCAL_HOSTS:
            raise HTTPException(403, "origem não permitida")
        try:
            vote = Vote.model_validate(json.loads(await request.body() or b"{}"))
        except (ValueError, ValidationError) as exc:
            raise HTTPException(422, f"voto inválido: {exc}") from None
        st = store(request)
        if not st.get_items([vote.item_id]):
            raise HTTPException(404, "item não encontrado")
        st.add_feedback("item", vote.item_id, vote.value, channel="web")
        return {"item_id": vote.item_id, "vote": st.item_votes(ids=[vote.item_id]).get(vote.item_id)}

    return app


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
