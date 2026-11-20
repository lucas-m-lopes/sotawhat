"""lesson_jobs (lessons from the interface, F1): one job at a time, the token the interface hands to the process, the
silent jobs, the steps and their times, why a job failed, cancelling, and how the process is started."""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from sotawhat.lessons import jobs
from sotawhat.store.db import Store

T0 = datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, start=T0):
        self.now = start

    def __call__(self):
        return self.now

    def tick(self, seconds):
        self.now += timedelta(seconds=seconds)


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        yield st


def tracker(store, clock, action="aula", **kw):
    lines = []
    t = jobs.Tracker(store, action, out=lines.append, clock=clock, beat_every=None, **kw)
    t.lines = lines
    return t


def test_one_job_at_a_time(store):
    clock = Clock()
    lesson = store.create_lesson("Atenção", [])
    first = tracker(store, clock, lesson_id=lesson).claim()
    row = jobs.get(store, first.id)
    assert (row["state"], row["origin"], row["pid"]) == ("rodando", "terminal", os.getpid())
    with pytest.raises(jobs.Busy) as busy:
        tracker(store, clock, lesson_id=lesson).claim()
    assert str(busy.value) == f"já há uma tarefa de aula em andamento: aula #{lesson} · produção · há 0 min"
    assert jobs.current(store, clock())["id"] == first.id
    first.finish(0)
    assert jobs.get(store, first.id)["state"] == "concluida" and jobs.current(store, clock()) is None
    assert tracker(store, clock, lesson_id=lesson).claim().id == first.id + 1


def test_a_silent_job_does_not_hold_the_slot_and_its_run_is_closed(store):
    clock = Clock()
    lesson = store.create_lesson("Atenção", [])
    run = store.start_run("lesson")
    store.update_lesson(lesson, run_id=run)
    dead = tracker(store, clock, lesson_id=lesson).claim()
    clock.tick(jobs.STALE_S)
    assert jobs.alive(jobs.get(store, dead.id), clock())
    clock.tick(1)                                                    # 31 s without a beat
    row = jobs.get(store, dead.id)
    assert not jobs.alive(row, clock()) and jobs.shown_state(row, clock()) == "interrompida"
    assert jobs.payload(row, clock())["error"] == "o processo parou de dar sinal às 18:00 UTC"
    tracker(store, clock, lesson_id=lesson).claim()                  # the next job marks it
    assert jobs.get(store, dead.id)["state"] == "interrompida"
    closed = store.conn.execute("SELECT ok, finished_at, error FROM runs WHERE id = ?", (run,)).fetchone()
    assert closed["ok"] == 0 and closed["finished_at"] and closed["error"].startswith("interrompida")
    dead.beat()                                                      # a late beat does not revive it
    assert jobs.get(store, dead.id)["state"] == "interrompida"


def test_the_process_adopts_the_job_the_interface_created(store, tmp_path):
    clock = Clock()
    lesson = store.create_lesson("Atenção", [])
    job_id, token = jobs.create_pending(store, lesson, "roteiro", tmp_path / "job.log", ["resume", lesson, "--so-roteiro"],
                                        send=None, now=clock())
    jobs.started(store, job_id, 4242, detached=True)
    row = jobs.get(store, job_id)
    assert (row["state"], row["origin"], row["pid"]) == ("iniciando", "interface", 4242)
    assert json.loads(row["args_json"]) == {"args": ["resume", str(lesson), "--so-roteiro"], "send": None, "detached": True}
    with pytest.raises(jobs.Busy):                                   # a second click
        jobs.create_pending(store, lesson, "aula", tmp_path / "job.log", [], now=clock())
    adopted = tracker(store, clock, action="roteiro", token=token).claim()
    row = jobs.get(store, job_id)
    assert adopted.id == job_id and adopted.lesson_id == lesson and (row["state"], row["pid"]) == ("rodando", os.getpid())
    with pytest.raises(jobs.JobGone):
        tracker(store, clock, token=token).claim()                   # adopted already
    with pytest.raises(jobs.JobGone):
        tracker(store, clock, token="never-issued").claim()
    with pytest.raises(ValueError):
        jobs.create_pending(store, lesson, "voz", tmp_path / "job.log", [], now=clock())


def test_a_process_that_never_started_frees_the_slot(store, tmp_path):
    clock = Clock()
    lesson = store.create_lesson("Atenção", [])
    job_id, _ = jobs.create_pending(store, lesson, "aula", tmp_path / "job.log", [], now=clock())
    jobs.failed_to_start(store, job_id, "não consegui iniciar o processo: [WinError 2]", now=clock())
    assert jobs.get(store, job_id)["state"] == "falhou" and jobs.current(store, clock()) is None


def test_steps_and_their_times(store):
    clock = Clock()
    t = tracker(store, clock).claim()
    lesson = store.create_lesson("Atenção", [])
    t.attach(lesson)
    t.expect(["roteiro", "storyboard", "voz"])
    t.stage("roteiro")
    clock.tick(200)
    t.stage("storyboard")
    clock.tick(90)
    t.expect(["roteiro", "storyboard", "voz", "checagem"])          # the steps already known stay as they are
    row = jobs.get(store, t.id)
    stages = json.loads(row["stages_json"])
    assert row["lesson_id"] == lesson and row["stage"] == "storyboard"
    assert [(s["name"], s["state"]) for s in stages] == [("roteiro", "feita"), ("storyboard", "rodando"),
                                                         ("voz", "pendente"), ("checagem", "pendente")]
    assert stages[0]["seconds"] == 200
    t.finish(0)
    done = jobs.payload(jobs.get(store, t.id), clock())
    assert done["state"] == "concluida" and not done["alive"] and done["elapsed_s"] == 290 and done["error"] is None
    assert done["stages"][1] == {"name": "storyboard", "state": "feita", "started_at": "2026-11-20T18:03:20+00:00",
                                 "seconds": 90}


def test_a_failed_command_says_why(store):
    clock = Clock()
    t = tracker(store, clock).claim()
    t.stage("voz")
    t.log("[voz] cena 1 de 9")
    t.log("HyperFrames incompleto em D:/x: instale com npm\n")
    t.finish(2)
    row = jobs.get(store, t.id)
    assert (row["state"], row["exit_code"], row["error"]) == ("falhou", 2, "HyperFrames incompleto em D:/x: instale com npm")
    assert json.loads(row["stages_json"])[0]["state"] == "parou"
    assert t.lines == ["[voz] cena 1 de 9", "HyperFrames incompleto em D:/x: instale com npm\n"]
    other = tracker(store, clock).claim()
    other.finish(1, "ElevenLabs 401: invalid api key")
    assert jobs.get(store, other.id)["error"] == "ElevenLabs 401: invalid api key"
    with pytest.raises(RuntimeError), tracker(store, clock) as crashed:
        raise RuntimeError("disco cheio")
    assert jobs.get(store, crashed.id)["error"] == "RuntimeError: disco cheio"


def test_cancelling_ends_the_tree_and_stops_the_lesson(store, tmp_path):
    clock = Clock()
    lesson = store.create_lesson("Atenção", [])
    run = store.start_run("lesson")
    store.update_lesson(lesson, run_id=run, status="planejada")
    job_id, token = jobs.create_pending(store, lesson, "aula", tmp_path / "job.log", ["resume", lesson], now=clock())
    t = tracker(store, clock, token=token).claim()
    t.expect(["roteiro", "storyboard"])
    t.stage("storyboard")
    clock.tick(40)
    t.beat()                                                         # the thread beats every 5 s
    killed = []
    out = jobs.cancel(store, lesson, kill=killed.append, now=clock())
    assert killed == [os.getpid()] and out["state"] == "cancelada"
    assert out["error"] == "cancelada na interface (etapa storyboard)"
    assert [(s["name"], s["state"], s.get("seconds")) for s in out["stages"]] == [("roteiro", "pendente", None),
                                                                                ("storyboard", "parou", 40)]
    stopped = store.get_lesson(lesson)
    assert stopped["status"] == "falhou" and stopped["error"] == "cancelada na interface (etapa storyboard)"
    assert store.conn.execute("SELECT ok FROM runs WHERE id = ?", (run,)).fetchone()[0] == 0
    t.beat()
    t.finish(0)                    # (a killed process writes nothing; even if it did, the cancel stands)
    assert jobs.get(store, job_id)["state"] == "cancelada"
    assert jobs.cancel(store, lesson, kill=killed.append, now=clock()) is None       # nothing runs there now


def test_cancelling_a_sending_keeps_the_lesson_ready(store, tmp_path):
    clock = Clock()
    lesson = store.create_lesson("Atenção", [])
    store.update_lesson(lesson, status="pronta")
    job_id, _ = jobs.create_pending(store, lesson, "envio", tmp_path / "job.log", ["send", lesson], now=clock())
    jobs.started(store, job_id, 99, detached=True)
    assert jobs.cancel(store, lesson, kill=lambda pid: None, now=clock())["state"] == "cancelada"
    assert store.get_lesson(lesson)["status"] == "pronta"


def test_last_job_of_each_lesson_and_the_log_tail(store, tmp_path):
    clock = Clock()
    a, b = store.create_lesson("A", []), store.create_lesson("B", [])
    tracker(store, clock, lesson_id=a).claim().finish(1, "x")
    last_a = tracker(store, clock, lesson_id=a).claim()
    last_a.finish(0)
    log = tmp_path / "job.log"
    log.write_bytes("linha 1\n\nação 2\r\n".encode("utf-8") + b"\xff quebrada\n")
    job_id, _ = jobs.create_pending(store, b, "roteiro", log, [], now=clock())
    last = jobs.last_for(store)
    assert last[a]["id"] == last_a.id and last[b]["id"] == job_id and jobs.last_for(store, [b]).keys() == {b}
    assert jobs.payload(jobs.get(store, job_id), clock(), log_lines=2)["log"] == ["ação 2", "\ufffd quebrada"]
    assert jobs.tail(tmp_path / "none.log") == [] and jobs.tail(None) == []
    log.write_text("=== 17:38 · roteiro\nroteiro pronto\n\n=== 17:44 · aula\n[voz] cena 1\n", encoding="utf-8")
    assert jobs.tail(log) == ["=== 17:44 · aula", "[voz] cena 1"]                 # this job's lines only


def test_the_process_leaves_the_job_object_or_says_it_could_not(tmp_path, monkeypatch):
    calls = []

    class Proc:
        pid = 77

        def wait(self):
            return 0

    def popen(cmd, refuse=False, **kw):
        calls.append((cmd, kw))
        if refuse and os.name == "nt" and kw["creationflags"] & jobs.CREATE_BREAKAWAY_FROM_JOB:
            raise PermissionError(5, "Acesso negado")
        return Proc()

    info = jobs.spawn_process(["resume", 9, "--job", "t"], tmp_path / "009" / "job.log", cwd=tmp_path, popen=popen)
    cmd, kw = calls[-1]
    assert info == {"pid": 77, "detached": True} and cmd[1:] == ["-m", "sotawhat.cli", "lessons", "resume", "9", "--job", "t"]
    assert kw["env"]["PYTHONIOENCODING"] == "utf-8" and kw["env"]["PYTHONUNBUFFERED"] == "1" and kw["cwd"] == str(tmp_path)
    assert (tmp_path / "009" / "job.log").exists()
    if os.name == "nt":
        assert kw["creationflags"] == jobs.CREATE_NO_WINDOW | jobs.CREATE_NEW_PROCESS_GROUP | jobs.CREATE_BREAKAWAY_FROM_JOB
        refused = jobs.spawn_process(["send", 9], tmp_path / "job.log", popen=lambda c, **k: popen(c, refuse=True, **k))
        assert refused["detached"] is False and calls[-1][1]["creationflags"] == jobs.CREATE_NO_WINDOW | jobs.CREATE_NEW_PROCESS_GROUP
    windowless = tmp_path / "Scripts" / "pythonw.exe"
    windowless.parent.mkdir()
    windowless.write_bytes(b"")
    (windowless.parent / "python.exe").write_bytes(b"")
    monkeypatch.setattr("sys.executable", str(windowless))
    assert jobs.python_exe() == str(windowless.parent / "python.exe")
