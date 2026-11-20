# tests/test_rag_surfaces.py
"""Where a question to the graph can come from: the interface (/api/ask), the MCP tool and the doctor."""
import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from sotawhat import mcp_server as m
from sotawhat.config import Settings
from sotawhat.doctor import check_rag
from sotawhat.items import Item
from sotawhat.rag import index
from sotawhat.rag.answer import SLM
from sotawhat.rag.retrieve import Retriever
from sotawhat.store.db import Store
from sotawhat.store.vectors import HashEmbedder
from sotawhat.web.app import create_app, serve

BASE = "http://127.0.0.1:8765"


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "insight.db"
    with Store(path) as st:
        run = st.start_run("daily")
        st.upsert_items([Item(id="pmid:1", kind="paper", source="pubmed", source_id="1", title="SepsisNet prediz sepse",
                              url="https://example.org/1", text="t"),
                         Item(id="pmid:2", kind="paper", source="pubmed", source_id="2", title="Escriba ambiente no PS",
                              url="https://example.org/2", text="t")], run)
        st.record_triage("pmid:1", run, "main", total=4.0, summary_pt="SepsisNet prevê sepse com AUROC 0,91.",
                         why_it_matters_pt="Útil na UTI.")
        st.record_triage("pmid:2", run, "frontier", total=3.5, summary_pt="Escriba ambiente reduz digitação.",
                         why_it_matters_pt="Útil no PS.")
        model = st.add_entity("model", "SepsisNet", "sepsisnet")
        st.add_mention("pmid:1", model, "main", "2026-11-19T10:00:00+00:00")
        index.refresh(st, HashEmbedder())
    return path


def _slm(text="O SepsisNet prevê sepse com AUROC 0,91 [1].", status=200):
    def post(url, json=None, headers=None, timeout=None):
        body = {"model": "m", "choices": [{"message": {"content": text}}], "usage": {}}
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))

    def get(url, headers=None, timeout=None):
        return httpx.Response(200, json={"data": [{"id": "m"}]}, request=httpx.Request("GET", url))

    return SLM("http://x/v1", "m", post=post, get=get)


def _client(db, tmp_path, slm=None, with_rag=True, jev=None):
    static = tmp_path / "static"
    static.mkdir(exist_ok=True)
    (static / "index.html").write_text("<!doctype html><title>sotawhat</title>", encoding="utf-8")
    knobs = Settings(_env_file=None)
    rag = (lambda store: (Retriever(store, HashEmbedder()), slm or _slm(), jev, knobs)) if with_rag else None
    return TestClient(create_app(db, static_dir=static, rag=rag), base_url=BASE)


def test_ask_from_the_interface(db, tmp_path):
    with _client(db, tmp_path) as c:
        before = c.get("/api/rag/status").json()
        assert before["items_indexed"] == 2 and before["approved_items"] == 2 and "slm" not in before
        answer = c.post("/api/ask", json={"question": "O que o SepsisNet faz?"}, headers={"origin": BASE})
        assert answer.status_code == 200
        body = answer.json()
        assert body["answer"].startswith("O SepsisNet") and body["cited"] == [1] and body["warnings"] == []
        assert body["sources"][0]["item_id"] == "pmid:1" and body["entities"][0]["name"] == "SepsisNet"
        status = c.get("/api/rag/status").json()
        assert status["slm"] == {"ok": True, "detail": "m em http://x/v1", "model": "m"} and status["engine"] == "slm"
        assert status["jev"] == {"ok": False, "model": None, "zdr": False}
        only = c.post("/api/ask", json={"question": "O que o SepsisNet faz?", "sources_only": True, "k": 1}).json()
        assert only["answer"] is None and only["error"] is None and len(only["sources"]) == 1
        assert c.post("/api/ask", json={"question": "oi"}).status_code == 422
        assert c.post("/api/ask", json={"question": "O que saiu?", "days": 0}).status_code == 422
        assert c.post("/api/ask", content='{"question": "O que saiu?"}', headers={"content-type": "text/plain"}).status_code == 415
        assert c.post("/api/ask", json={"question": "O que saiu?"}, headers={"origin": "https://evil.example"}).status_code == 403
    with _client(db, tmp_path, slm=_slm(status=500)) as c:
        down = c.post("/api/ask", json={"question": "O que o SepsisNet faz?"}).json()
        assert down["answer"] is None and "500" in down["error"] and down["sources"]
    with _client(db, tmp_path, with_rag=False) as c:
        assert c.post("/api/ask", json={"question": "O que saiu?"}).status_code == 503


def test_the_interface_leaves_127_0_0_1_only_inside_a_container(db, monkeypatch):
    with pytest.raises(ValueError, match="127.0.0.1"):
        serve(db, host="0.0.0.0", open_browser=False)
    monkeypatch.setenv("SOTAWHAT_IN_CONTAINER", "1")
    with pytest.raises(ValueError, match="127.0.0.1"):
        serve(db, host="192.168.0.10", open_browser=False)


def test_retrieve_tool_of_the_mcp(db):
    tools = asyncio.run(m.build_server(db).list_tools())
    assert {"retrieve", "glossary"} <= {t.name for t in tools}
    assert "error" in m.retrieve_tool(db, "O que o SepsisNet faz?")                         # no retriever here
    found = m.retrieve_tool(db, "O que o SepsisNet faz?", k=1, retriever_factory=lambda store: Retriever(store, HashEmbedder()))
    assert [s["item_id"] for s in found["sources"]] == ["pmid:1"] and found["sources"][0]["day"] == found["sources"][0]["day"][:10]
    assert found["entities"][0]["name"] == "SepsisNet" and any("SepsisNet (modelo" in f for f in found["facts"])


def test_doctor_checks_the_index_and_the_slm(db, tmp_path):
    settings = Settings(_env_file=None)
    with Store(db) as store:
        ok, slm = check_rag(settings, store, ping=lambda: (True, "m em http://x/v1"))
        assert (ok.status, slm.status) == ("ok", "ok") and "2 de 2 itens aprovados" in ok.detail
        down = check_rag(settings, store, ping=lambda: (False, "http://x não responde (ConnectError)"))[1]
        assert down.status == "warn" and "sotawhat rag up" in down.detail
        run = store.start_run("daily")
        store.upsert_items([Item(id="pmid:3", kind="paper", source="pubmed", source_id="3", title="Novo", url="u")], run)
        store.record_triage("pmid:3", run, "main", summary_pt="Resumo.")
        assert check_rag(settings, store, ping=lambda: (True, "ok"))[0].status == "warn"   # an approved item not indexed
    with Store(tmp_path / "empty.db") as empty:
        assert "vazio" in check_rag(settings, empty, ping=lambda: (True, "ok"))[0].detail
