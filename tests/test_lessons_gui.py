"""Lessons from the interface (F1): the suggestions of the week, the voice credits, the estimate of the review and
the lesson routes of the web app with a fake launcher (no process is started, nothing goes to the network)."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from sotawhat.lessons import eleven, estimate, jobs
from sotawhat.lessons.pack import pick_topic, suggest_topics
from sotawhat.store.db import Store
from sotawhat.web.app import create_app
from tests.test_graph_query import g  # noqa: F401 - the graph fixture
from tests.test_lessons_plan import motion_plan_with

BASE = "http://127.0.0.1:8765"


# ---- suggestions, credits, estimate ---------------------------------------------------------------------------------
def test_the_suggestions_of_the_week_skip_taught_entities_until_the_lesson_is_discarded(g):  # noqa: F811
    st, ids = g
    assert suggest_topics(st) == []                                                # no weekly report yet
    run = st.start_run("weekly")
    st.save_weekly_report(run, "2026-11-09", {"trends": [
        {"entity_id": ids["google"], "name": "Google", "type": "organization", "z": 9},
        {"entity_id": ids["fract"], "name": "missed fracture", "type": "problem", "z": 4},
        {"entity_id": ids["med"], "name": "MedGemma 1.5", "type": "model", "z": 5}]})
    found = suggest_topics(st, min_sources=1)
    assert [(s["name"], s["type_label"]) for s in found] == [("MedGemma 1.5", "modelo"), ("missed fracture", "problema")]
    assert found[0]["entity_id"] == ids["med"] and found[0]["z"] == 5 and found[0]["mentions"] >= 1
    assert [s["name"] for s in suggest_topics(st, n=1, min_sources=1)] == ["MedGemma 1.5"]
    lesson = st.create_lesson("MedGemma", [ids["med"]])
    assert pick_topic(st, min_sources=1) == ("missed fracture", [ids["fract"]])
    st.update_lesson(lesson, status="descartada")
    assert pick_topic(st, min_sources=1) == ("MedGemma 1.5", [ids["med"]])


def test_the_voice_credits_left():
    def answer(request):
        assert request.url.path == "/v1/user/subscription" and request.headers["xi-api-key"] == "k"
        return httpx.Response(200, json={"tier": "starter", "character_count": 3295, "character_limit": 90000,
                                         "next_character_count_reset_unix": 1797708732})

    client = httpx.Client(base_url=eleven.API, transport=httpx.MockTransport(answer), headers={"xi-api-key": "k"})
    assert eleven.credit_balance("k", client=client) == {"left": 86705, "limit": 90000, "used": 3295, "tier": "starter",
                                                         "resets_at": "2026-12-19"}
    down = httpx.Client(base_url=eleven.API, transport=httpx.MockTransport(lambda r: httpx.Response(401, text="no")))
    assert eleven.credit_balance("k", client=down) is None and eleven.credit_balance("") is None


def test_the_estimate_of_a_planned_lesson():
    plan = motion_plan_with(("graph", "mechanism3d", "volume3d") + ("graph",) * 4).model_dump()
    chars = estimate.narration_chars(plan)
    out = estimate.production(plan, plan_usd=5.0, plan_credits=30000)
    assert out["scenes"] == 7 and out["free3d"] == 1 and out["chars"] == chars
    assert out["credits"] == round(chars * 1.013) and out["voice_usd"] == eleven.credits_usd(out["credits"], 5.0, 30000)
    assert out["video_s"] == round(chars / 12.9) and out["llm_usd"] == 0.038
    assert list(out["stages"]) == ["storyboard", "voz", "3d", "checagem", "video", "envio"]
    assert out["stages"]["3d"] == 315 and out["stages"]["video"] == round(1.9 * chars / 12.9)
    assert out["seconds"] == sum(out["stages"].values()) and out["total_usd"] == round(0.038 + out["voice_usd"], 3)
    quiet = estimate.production(motion_plan_with().model_dump(), send=False)
    assert "3d" not in quiet["stages"] and "envio" not in quiet["stages"] and quiet["llm_usd"] == 0.006


# ---- the lesson routes, with a fake launcher ------------------------------------------------------------------------
class FakeProcesses:
    """The two things the launcher does to the computer: start a process and end its tree."""

    def __init__(self):
        self.spawned, self.killed = [], []

    def spawn(self, args, log_path, cwd):
        self.spawned.append(list(args))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as out:
            out.write("planejando o roteiro…\n")
        return {"pid": 4242, "detached": True}

    def kill(self, pid):
        self.killed.append(pid)
        return True


@pytest.fixture
def lab(g, tmp_path):  # noqa: F811
    from sotawhat.lessons.launcher import Launcher

    st, ids = g
    procs = FakeProcesses()
    credits = {"left": 90000, "limit": 90000, "used": 0, "tier": "starter", "resets_at": "2026-12-19"}
    launcher = Launcher(tmp_path / "lessons", cwd=tmp_path, spawn=procs.spawn, kill=procs.kill,
                        credits=lambda: dict(credits), ready=lambda: [], telegram=True)
    client = TestClient(create_app(st.path, lessons=launcher), base_url=BASE)
    with client:
        yield client, st, ids, procs, credits, launcher


def post(client, path, body=None):
    return client.post(path, json=body or {}, headers={"origin": BASE})


def finish(st, job_id, state="concluida"):
    st.conn.execute("UPDATE lesson_jobs SET state = ? WHERE id = ?", (state, job_id))
    st.conn.commit()


def test_a_new_lesson_is_planned_in_a_process_of_its_own(lab):
    c, st, ids, procs, credits, launcher = lab
    state = c.get("/api/lessons/state").json()
    assert state["available"] and state["credits"]["left"] == 90000 and state["job"] is None and state["discarded"] == 0
    assert state["telegram"] is True and state["price"] == [5.0, 30000] and state["ready"] == []
    made = post(c, "/api/lessons", {"topic": "  MedGemma   na radiologia ", "entities": [ids["med"]],
                                    "mode": "equilibrado"})
    assert made.status_code == 200, made.text
    lesson, job = made.json()["lesson"], made.json()["job"]
    token = procs.spawned[-1][-1]
    assert procs.spawned[-1] == ["resume", str(lesson["id"]), "--so-roteiro", "--modo", "equilibrado", "--job", token]
    assert lesson["topic"] == "MedGemma na radiologia" and lesson["mode"] == "equilibrado" and not lesson["has_plan"]
    assert (job["action"], job["state"], job["alive"], job["detached"]) == ("roteiro", "iniciando", True, True)
    assert lesson["job"]["id"] == job["id"]
    assert post(c, "/api/lessons", {"topic": "MedGemma"}).status_code == 409             # one at a time
    polled = c.get("/api/lessons/job").json()["job"]
    assert polled["id"] == job["id"] and polled["log"][-1] == "planejando o roteiro…"
    assert polled["log"][0].startswith("=== ") and "sotawhat lessons resume" in polled["log"][0]
    # nothing in the graph, an unknown entity, a topic too short: refused before any process
    finish(st, job["id"])
    assert "nada no grafo" in post(c, "/api/lessons", {"topic": "receita de bolo de cenoura"}).json()["detail"]
    assert post(c, "/api/lessons", {"topic": "MedGemma", "entities": [999999]}).status_code == 422
    assert post(c, "/api/lessons", {"topic": "x"}).status_code == 422
    assert len(procs.spawned) == 1


def test_cancel_replan_produce_send_and_discard(lab, tmp_path):
    c, st, ids, procs, credits, launcher = lab
    lesson_id = post(c, "/api/lessons", {"topic": "MedGemma"}).json()["lesson"]["id"]
    cancelled = post(c, f"/api/lessons/{lesson_id}/cancel")
    assert cancelled.status_code == 200 and procs.killed == [4242]
    assert cancelled.json()["job"]["state"] == "cancelada" and cancelled.json()["lesson"]["status"] == "falhou"
    assert post(c, f"/api/lessons/{lesson_id}/cancel").status_code == 409                # nothing runs now
    assert post(c, f"/api/lessons/{lesson_id}/produce").status_code == 409                # no plan yet
    # the plan arrives (the process would write it); the review shows the estimate
    plan = motion_plan_with(("graph", "mechanism3d") + ("graph",) * 5).model_dump()
    st.update_lesson(lesson_id, plan=plan, status="planejada", error=None)
    listed = c.get("/api/lessons").json()[0]
    assert listed["has_plan"] and listed["estimate"]["free3d"] == 1 and listed["estimate"]["scenes"] == 7
    assert listed["voice_paid"] is False and listed["job"]["state"] == "cancelada"
    # make the plan again: the stored plan goes, only once the slot is ours
    redone = post(c, f"/api/lessons/{lesson_id}/plan")
    assert redone.status_code == 200 and procs.spawned[-1][:7] == ["resume", str(lesson_id), "--refazer", "plano",
                                                                   "--so-roteiro", "--modo", "economico"]
    assert st.get_lesson(lesson_id)["plan_json"] is None and st.get_lesson(lesson_id)["status"] == "nova"
    finish(st, redone.json()["job"]["id"])
    st.update_lesson(lesson_id, plan=plan, status="planejada")
    # produce: the credits are checked before the voice, the sending needs Telegram
    credits["left"] = 100
    launcher.forget_credits()
    short = post(c, f"/api/lessons/{lesson_id}/produce", {"send": False})
    assert short.status_code == 409 and short.json()["detail"].startswith("faltam créditos de voz: a aula precisa de ~")
    credits["left"] = 90000
    launcher.forget_credits()
    launcher.telegram = False
    assert "Telegram não configurado" in post(c, f"/api/lessons/{lesson_id}/produce", {"send": True}).json()["detail"]
    produced = post(c, f"/api/lessons/{lesson_id}/produce", {"send": False})
    assert produced.status_code == 200 and procs.spawned[-1][:5] == ["resume", str(lesson_id), "--modo", "economico",
                                                                     "--sem-envio"]
    assert produced.json()["job"]["action"] == "aula" and produced.json()["job"]["send"] is False
    assert post(c, f"/api/lessons/{lesson_id}/discard").status_code == 409             # its job is alive
    finish(st, produced.json()["job"]["id"])
    # sending: a lesson with its video
    assert post(c, f"/api/lessons/{lesson_id}/send").status_code == 409                # no video yet
    video = tmp_path / "aula.mp4"
    video.write_bytes(b"mp4")
    st.update_lesson(lesson_id, status="pronta", video_path=str(video))
    assert post(c, f"/api/lessons/{lesson_id}/send").status_code == 409                # Telegram is off
    launcher.telegram = True
    sent = post(c, f"/api/lessons/{lesson_id}/send")
    assert sent.status_code == 200 and procs.spawned[-1][:2] == ["send", str(lesson_id)]
    finish(st, sent.json()["job"]["id"])
    assert post(c, f"/api/lessons/{lesson_id}/plan").status_code == 409                # it has a video now
    # discard: out of the list, still on disk and in ?discarded=true
    assert post(c, f"/api/lessons/{lesson_id}/discard").json()["lesson"]["status"] == "descartada"
    assert c.get("/api/lessons").json() == [] and len(c.get("/api/lessons?discarded=true").json()) == 1
    assert c.get("/api/lessons/state").json()["discarded"] == 1
    assert post(c, f"/api/lessons/{lesson_id}/produce").status_code == 409             # discarded
    st.update_lesson(lesson_id, status="entregue")
    assert post(c, f"/api/lessons/{lesson_id}/discard").status_code == 409             # delivered
    assert post(c, "/api/lessons/999/discard").status_code == 404


def test_the_lesson_actions_are_guarded(lab, tmp_path):
    c, st, ids, procs, credits, launcher = lab
    assert c.post("/api/lessons", json={"topic": "MedGemma"}, headers={"origin": "https://evil.example"}).status_code == 403
    assert c.post("/api/lessons", content='{"topic": "MedGemma"}', headers={"content-type": "text/plain"}).status_code == 415
    assert procs.spawned == []
    with TestClient(create_app(st.path), base_url=BASE) as bare:                       # no launcher: reading only
        assert bare.get("/api/lessons/state").json()["available"] is False
        assert post(bare, "/api/lessons", {"topic": "MedGemma"}).status_code == 503
