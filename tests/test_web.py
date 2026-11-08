# tests/test_web.py
"""Local web API (SDD §6.11): FastAPI on 127.0.0.1, host and origin checks, votes from the page."""
import pytest
from fastapi.testclient import TestClient

from sotawhat.cli import parse_args
from sotawhat.items import Item
from sotawhat.store.db import Store
from sotawhat.web.app import create_app

BASE = "http://127.0.0.1:8765"
NEWS_ID = "url:https://example.org/news/1?a=1"


@pytest.fixture
def client(tmp_path):
    db = tmp_path / "insight.db"
    with Store(db) as st:
        run = st.start_run("daily")
        st.upsert_items([Item(id="pmid:1", kind="paper", source="pubmed", source_id="1", title="MedGemma reads CT",
                              url="https://example.org/1", text="t", pmid="1"),
                         Item(id=NEWS_ID, kind="article", source="rss:stat", source_id="n1", title="Hospital deploys scribe",
                              url="https://example.org/news/1?a=1", text="t")], run)
        for item_id in ("pmid:1", NEWS_ID):
            st.record_triage(item_id, run, "main", total=4.0, summary_pt="Resumo", why_it_matters_pt="Por quê")
        med = st.add_entity("model", "MedGemma 1.5", "medgemma 1 5")
        google = st.add_entity("organization", "Google", "google")
        st.add_mention("pmid:1", med, "main", "2026-11-08T10:00:00+00:00")
        st.add_mention("pmid:1", google, "mentioned", "2026-11-08T10:00:00+00:00")
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><title>sotawhat</title>", encoding="utf-8")
    (static / "app.js").write_text("console.log('ok')", encoding="utf-8")
    with TestClient(create_app(db, static_dir=static), base_url=BASE) as c:
        yield c, {"med": med, "google": google}, db


def test_graph_entity_item_search_and_stats(client):
    c, ids, _ = client
    graph = c.get("/api/graph", params={"days": 0, "types": "organization", "min": 1, "limit": 10}).json()
    assert [n["label"] for n in graph["nodes"]] == ["Google"] and graph["window"]["days"] is None
    assert {n["label"] for n in c.get("/api/graph").json()["nodes"]} == {"MedGemma 1.5", "Google"}
    assert c.get(f"/api/graph?focus=e{ids['google']}&days=0").json()["focus"] == f"e{ids['google']}"
    assert c.get(f"/api/entity/e{ids['med']}").json()["name"] == "MedGemma 1.5"
    assert c.get("/api/entity/e9999").status_code == 404
    assert c.get("/api/item", params={"id": NEWS_ID}).json()["title"] == "Hospital deploys scribe"
    assert c.get("/api/item", params={"id": "nope"}).status_code == 404
    assert [e["name"] for e in c.get("/api/search", params={"q": "medgemma"}).json()["entities"]] == ["MedGemma 1.5"]
    assert c.get("/api/stats").json()["approved"] == 2
    assert c.get("/api/graph", params={"limit": 999999}).status_code == 422


def test_votes_from_the_page(client):
    c, _, db = client
    ok = c.post("/api/feedback", json={"item_id": "pmid:1", "value": "down"}, headers={"origin": BASE})
    assert ok.status_code == 200 and ok.json() == {"item_id": "pmid:1", "vote": "down"}
    assert c.post("/api/feedback", json={"item_id": NEWS_ID, "value": "up"}).json()["vote"] == "up"   # no Origin
    with Store(db) as st:
        assert st.conn.execute("SELECT channel FROM feedback WHERE target_id = 'pmid:1'").fetchone()[0] == "web"
    assert c.post("/api/feedback", json={"item_id": "pmid:1", "value": "maybe"}).status_code == 422
    assert c.post("/api/feedback", json={"item_id": "nope", "value": "up"}).status_code == 404
    assert c.post("/api/feedback", content='{"item_id": "pmid:1", "value": "up"}',
                  headers={"content-type": "text/plain"}).status_code == 415
    assert c.post("/api/feedback", json={"item_id": "pmid:1", "value": "up"},
                  headers={"origin": "https://evil.example"}).status_code == 403


def test_host_check_page_and_static_files(client):
    c, _, _ = client
    assert c.get("/api/stats", headers={"host": "evil.example"}).status_code == 400
    page = c.get("/")
    assert page.status_code == 200 and "text/html" in page.headers["content-type"] and "sotawhat" in page.text
    script = c.get("/static/app.js")
    assert script.text == "console.log('ok')" and script.headers["cache-control"] == "no-cache"


def test_packaged_page_loads_only_local_files():
    import hashlib
    import re

    from sotawhat.web.app import STATIC

    page = (STATIC / "index.html").read_text(encoding="utf-8")
    scripts = re.findall(r'<script src="([^"]+)"', page)
    assert scripts == ["/static/vendor/graphology.umd.min.js", "/static/vendor/graphology-library.min.js",
                       "/static/vendor/sigma.min.js", "/static/app.js"]
    assert '<link rel="stylesheet" href="/static/style.css">' in page
    assert not re.search(r'(src|href)="(https?:)?//', page)                 # no CDN, nothing external
    licenses = (STATIC / "vendor" / "LICENSES.md").read_text(encoding="utf-8")
    for name in ("sigma.min.js", "graphology.umd.min.js", "graphology-library.min.js"):
        digest = hashlib.sha256((STATIC / "vendor" / name).read_bytes()).hexdigest()
        assert digest in licenses, name
    app_js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "fetch(" in app_js and "innerHTML" not in app_js                 # data goes in with textContent


def test_cli_serve():
    ns = parse_args(["serve"])
    assert (ns.command, ns.port, ns.no_browser) == ("serve", None, False)
    ns = parse_args(["serve", "--port", "9000", "--no-browser"])
    assert (ns.port, ns.no_browser) == (9000, True)
