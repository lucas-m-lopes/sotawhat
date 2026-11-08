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


def _seed_ideas(db):
    """Two finalists of one weekly run (one already liked) and one discarded draft."""
    draft = {"titulo": "Escriba de alta no PS", "problema_jtbd": "Altas atrasam 2 h.", "stakeholder_dono": "coordenador do PS",
             "setor": "A06", "mecanismo": "Resume o atendimento.", "tecnicas": ["ASR"], "capacidade_intermediaria": "resumo",
             "dado_necessario": ["áudio"], "forma": "produto_b2b", "integracao": "FHIR", "modelo_negocio": "SaaS",
             "why_now": "ASR em pt-BR.", "riscos": ["alucinação"], "hipotese_nula": "o médico não lê."}
    with Store(db) as st:
        run = st.start_run("weekly")
        candidate = {"technique_id": 1, "technique": "speech recognition", "problem_id": 2, "problem": "discharge delay",
                     "sampler": "recent_technique", "context": ["2026-11-07 · item: Ambient scribe RCT — ensaio"]}
        ids = []
        for title, score, status, selected in (("Escriba de alta no PS", 6.2, "nova", True),
                                               ("Painel de leitos", 7.0, "curtida", True),
                                               ("Escriba repetido", 0.0, "descartada", False)):
            idea = st.add_idea(run, title, card={"draft": draft | {"titulo": title}, "model": "x/y",
                                                 "dossie": {"piloto_90d": "1 unidade", "classe_samd": "II"}},
                               lens="jtbd", persona="gestor de leitos", niche="A06|C?|produto_b2b", candidate=candidate,
                               status=status)
            st.update_idea(idea, score=score, selected=selected,
                           scores={"eixos": {"valor": 8}, "gates": [], "confianca": 0.8, "justificativas": ["boa dor"]},
                           novelty={"camadas": {"openalex": [{"title": "Scribes", "year": 2026, "url": "https://x.org"}],
                                                "_nao_verificado": ["patentes"]},
                                    "facetas": {"problema": {"estado": "nao_encontrado", "vizinhos": []}}, "nota": 7.5},
                           critique={"criticas": [{"papel": "clinico", "veredito": "ajustar", "kill_criteria": ["sem PEP"],
                                                   "o_que_mudaria": "piloto"}], "nasss_complexos": 2, "pre_mortem": "x"})
            ids.append(idea)
        st.update_idea(ids[2], discard_reason="duplicada da ideia 1")
    return ids


def test_ideas_page_api(client):
    c, _, db = client
    first, liked, dropped = _seed_ideas(db)
    data = c.get("/api/ideas").json()
    assert [i["id"] for i in data["ideas"]] == [liked, first] and data["counts"] == {"nova": 1, "curtida": 1}
    card = data["ideas"][1]
    assert card["sector_label"] == "emergência/triagem" and card["kill"] == ["sem PEP"] and card["unverified"] == ["patentes"]
    assert "context" not in card["candidate"] and "já existe" in data["reasons"]
    everything = c.get("/api/ideas", params={"finalists": "false"}).json()
    assert everything["total"] == 3 and everything["counts"]["descartada"] == 1
    only = c.get("/api/ideas", params={"finalists": "false", "status": "descartada"}).json()["ideas"]
    assert [i["id"] for i in only] == [dropped] and only[0]["discard_reason"] == "duplicada da ideia 1"
    assert c.get("/api/ideas", params={"status": "bogus"}).status_code == 422
    detail = c.get(f"/api/ideas/{first}").json()
    assert detail["context"] == ["2026-11-07 · item: Ambient scribe RCT — ensaio"] and detail["votes"] == []
    assert c.get("/api/ideas/9999").status_code == 404


def test_idea_votes_from_the_page(client):
    c, _, db = client
    first, liked, _ = _seed_ideas(db)
    res = c.post("/api/ideas/vote", json={"idea_id": first, "value": "down", "note": " já existe "},
                 headers={"origin": BASE})
    assert res.status_code == 200 and res.json() == {"idea_id": first, "status": "rejeitada"}
    assert c.post("/api/ideas/vote", json={"idea_id": liked, "value": "built"}).json()["status"] == "construida"
    votes = c.get(f"/api/ideas/{first}").json()["votes"]
    assert [(v["value"], v["note"], v["channel"]) for v in votes] == [("down", "já existe", "web")]
    for body, headers, code in (
            ({"idea_id": first, "value": "maybe"}, {}, 422),
            ({"idea_id": 9999, "value": "up"}, {}, 404),
            ({"idea_id": first, "value": "up", "note": "x" * 301}, {}, 422),
            ({"idea_id": first, "value": "up"}, {"origin": "https://evil.example"}, 403),
            ({"idea_id": first, "value": "up"}, {"origin": "null"}, 403)):
        assert c.post("/api/ideas/vote", json=body, headers=headers).status_code == code, body
    assert c.post("/api/ideas/vote", content='{"idea_id": 1, "value": "up"}',
                  headers={"content-type": "text/plain"}).status_code == 415
    assert c.post("/api/ideas/vote", content="[1]", headers={"content-type": "application/json"}).status_code == 422
    assert c.post("/api/ideas/vote", content="{", headers={"content-type": "application/json"}).status_code == 422


def test_trends_api(client):
    c, ids, _ = client
    data = c.get("/api/trends").json()
    assert set(data) == {"trends", "communities", "gaps", "weekly", "rules"}
    assert data["weekly"] is None and data["rules"] == [] and set(data["gaps"]) == {"recent_technique", "community_bridge",
                                                                                    "serendipity"}


def test_page_has_the_three_views():
    from sotawhat.web.app import STATIC

    page = (STATIC / "index.html").read_text(encoding="utf-8")
    for anchor in ('href="#grafo"', 'href="#ideias"', 'href="#tendencias"', 'id="view-ideas"', 'id="view-trends"'):
        assert anchor in page


def test_today_and_runs(client):
    c, ids, db = client
    with Store(db) as st:
        run = st.conn.execute("SELECT MAX(id) FROM runs").fetchone()[0]          # the fixture's run, still open
        st.finish_run(run, ok=True, stats={"collected": {"medico": 2}, "new": 2})
        st.record_delivery(run, "2026-11-08", NEWS_ID, "k1", "main", 2)
        st.record_delivery(run, "2026-11-08", "pmid:1", "k2", "main", 1)
        st.add_feedback("item", "pmid:1", "up", "web")
    data = c.get("/api/today").json()
    assert data["run"]["collected"] == 2 and data["run"]["new"] == 2
    assert [i["id"] for i in data["sections"]["main"]] == ["pmid:1", NEWS_ID]          # the delivery order
    assert data["sections"]["main"][0]["vote"] == "up" and data["sections"]["main"][0]["summary_pt"] == "Resumo"
    runs = c.get("/api/runs", params={"limit": 5}).json()
    assert runs[0]["kind"] == "daily" and runs[0]["ok"] is True and runs[0]["seconds"] is not None


def test_today_skips_runs_without_a_digest(client):
    c, ids, db = client
    with Store(db) as st:
        first = st.conn.execute("SELECT MAX(id) FROM runs").fetchone()[0]
        st.finish_run(first, ok=True, stats={})
        st.record_delivery(first, "2026-11-08", "pmid:1", "k1", "main", 1)
        later = st.start_run("daily")                                         # --no-llm: nothing approved
        st.finish_run(later, ok=True, stats={"collected": {"geral": 5}, "new": 5})
    run = c.get("/api/today").json()["run"]
    assert run["id"] == first and run["latest_id"] == later
