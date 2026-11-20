# sotawhat/lessons/jobs.py
"""Lessons made from the interface (F1, docs/superpowers/specs/2026-11-20-aulas-pela-interface-design.md).

Every `sotawhat lessons make/resume/hf/send` registers a job in `lesson_jobs`, the interface's and the terminal's
alike, so that one lesson is made at a time and the Aulas tab can show its steps.

- A job is alive while its process rewrites `beat_at` (every BEAT_S). A job silent for STALE_S counts as interrupted
  (the process died, the computer slept); the page shows it so at once, but the row is only marked when another
  job asks for the slot, which also closes the run it left open.
- Asking for the slot is one `BEGIN IMMEDIATE` transaction: two clicks, or the interface and a terminal, cannot both
  start a lesson.
- The interface inserts the job as `iniciando`, with a random token, and starts `python -m sotawhat.cli lessons …
  --job TOKEN` in a process of its own (`spawn_process`), out of the job object of the scheduled task, so a restart
  of the interface does not end the lesson. The process adopts the row. "Cancelar" ends the process tree (node,
  Chrome and FFmpeg included).
- The state lives in SQLite and not in a file: Windows refuses to replace a file that another process is reading."""
import json
import os
import secrets
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

BEAT_S = 5.0
STALE_S = 30.0
LIVE = ("iniciando", "rodando")
ACTIONS = ("roteiro", "aula", "envio")
STAGES = ("roteiro", "storyboard", "voz", "3d", "checagem", "video", "envio")

# Windows process creation flags
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_NO_WINDOW = 0x08000000


class Busy(Exception):
    """Another lesson job is alive."""

    def __init__(self, row, now=None):
        self.row = row
        super().__init__(f"já há uma tarefa de aula em andamento: {describe(row, now)}")


class JobGone(Exception):
    """The job the interface created for this process was cancelled, or never existed."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment) -> str:
    return moment.isoformat(timespec="seconds")


def _age(since, now) -> float:
    return (now - datetime.fromisoformat(since)).total_seconds()


def alive(row, now=None) -> bool:
    return row is not None and row["state"] in LIVE and _age(row["beat_at"], now or _now()) <= STALE_S


def shown_state(row, now=None) -> str:
    """What the page shows: a live state whose beat stopped is `interrompida`."""
    return "interrompida" if row["state"] in LIVE and not alive(row, now) else row["state"]


def describe(row, now=None) -> str:
    """"aula #9 · produção · etapa voz · há 6 min"."""
    now = now or _now()
    what = {"roteiro": "roteiro", "aula": "produção", "envio": "envio ao Telegram"}.get(row["action"], row["action"])
    minutes = max(0, round(_age(row["started_at"], now) / 60))
    parts = [f"aula #{row['lesson_id']}" if row["lesson_id"] else "aula nova", what]
    if row["stage"]:
        parts.append(f"etapa {row['stage']}")
    parts.append(f"há {minutes} min")
    return " · ".join(parts)


# ---- reading ---------------------------------------------------------------------------------------------------
def get(store, job_id):
    return store.conn.execute("SELECT * FROM lesson_jobs WHERE id = ?", (job_id,)).fetchone()


def current(store, now=None):
    """The live job, or None."""
    rows = store.conn.execute("SELECT * FROM lesson_jobs WHERE state IN ('iniciando', 'rodando') ORDER BY id DESC")
    return next((row for row in rows if alive(row, now)), None)


def latest(store):
    return store.conn.execute("SELECT * FROM lesson_jobs ORDER BY id DESC LIMIT 1").fetchone()


def last_for(store, lesson_ids=None) -> dict:
    """{lesson_id: its latest job}."""
    rows = store.conn.execute("SELECT * FROM lesson_jobs WHERE id IN (SELECT MAX(id) FROM lesson_jobs "
                              "WHERE lesson_id IS NOT NULL GROUP BY lesson_id)").fetchall()
    wanted = None if lesson_ids is None else {int(i) for i in lesson_ids}
    return {row["lesson_id"]: row for row in rows if wanted is None or row["lesson_id"] in wanted}


HEADER = "=== "         # the line the interface writes before each job of a lesson (its log keeps them all)


def tail(path, n=12) -> list:
    """The last `n` non-empty lines of a log, from the header of its last job on (the last 16 KB are enough)."""
    path = Path(path) if path else None
    if path is None or not path.exists():
        return []
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - 16384))
        text = f.read().decode("utf-8", "replace")
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    starts = [n for n, line in enumerate(lines) if line.startswith(HEADER)]
    return lines[starts[-1] if starts else 0:][-n:]


def payload(row, now=None, log_lines=0) -> dict:
    """A job as the page reads it."""
    now = now or _now()
    end = datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else now
    args = json.loads(row["args_json"] or "{}")
    out = {"id": row["id"], "lesson_id": row["lesson_id"], "action": row["action"], "origin": row["origin"],
           "state": shown_state(row, now), "alive": alive(row, now), "stage": row["stage"],
           "stages": json.loads(row["stages_json"] or "[]"), "started_at": row["started_at"],
           "beat_at": row["beat_at"], "finished_at": row["finished_at"], "exit_code": row["exit_code"],
           "error": row["error"], "elapsed_s": round((end - datetime.fromisoformat(row["started_at"])).total_seconds()),
           "send": args.get("send"), "detached": args.get("detached")}
    if out["state"] == "interrompida" and not out["error"]:
        out["error"] = f"o processo parou de dar sinal às {row['beat_at'][11:16]} UTC"
    if log_lines:
        out["log"] = tail(row["log_path"], log_lines)
    return out


# ---- the slot -----------------------------------------------------------------------------------------------------
def _close_open_run(conn, lesson_id, error, now):
    """The run a dead job left open (the runs list of the Hoje tab would show it running forever)."""
    if not lesson_id:
        return
    lesson = conn.execute("SELECT run_id FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if lesson and lesson["run_id"]:
        conn.execute("UPDATE runs SET finished_at = ?, ok = 0, error = ? WHERE id = ? AND finished_at IS NULL",
                     (_iso(now), error, lesson["run_id"]))


def _claim(store, insert, args, now):
    """Under one BEGIN IMMEDIATE: refuse when a job is alive, mark the silent ones interrupted, insert. -> row id"""
    conn = store.conn
    with store._lock:
        conn.commit()                       # no implicit transaction left open: BEGIN needs a clean connection
        conn.execute("BEGIN IMMEDIATE")
        try:
            rows = conn.execute("SELECT * FROM lesson_jobs WHERE state IN ('iniciando', 'rodando')").fetchall()
            for row in rows:
                if alive(row, now):
                    raise Busy(row, now)
            for row in rows:
                error = f"o processo parou de dar sinal às {row['beat_at'][11:16]} UTC"
                conn.execute("UPDATE lesson_jobs SET state = 'interrompida', finished_at = ?, error = ? WHERE id = ?",
                             (_iso(now), error, row["id"]))
                _close_open_run(conn, row["lesson_id"], f"interrompida: {error}", now)
            job_id = conn.execute(insert, args).lastrowid
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return job_id


def create_pending(store, lesson_id, action, log_path, args, send=None, now=None) -> tuple:
    """The interface's side: a job `iniciando` for the process it is about to start. -> (job id, token). Raises Busy."""
    if action not in ACTIONS:
        raise ValueError(f"ação desconhecida: {action}")
    now = now or _now()
    token = secrets.token_hex(12)
    info = json.dumps({"args": [str(a) for a in args], "send": send}, ensure_ascii=False)
    job_id = _claim(store, "INSERT INTO lesson_jobs(lesson_id, action, origin, token, state, args_json, log_path,"
                           " started_at, beat_at) VALUES(?, ?, 'interface', ?, 'iniciando', ?, ?, ?, ?)",
                    (lesson_id, action, token, info, str(log_path), _iso(now), _iso(now)), now)
    return job_id, token


def started(store, job_id, pid, detached) -> None:
    """The process exists: its pid (the launcher's, until the process adopts the row) and whether it left the job
    object of the interface (False: it ends with a restart of the interface)."""
    with store._lock:
        row = get(store, job_id)
        info = json.loads(row["args_json"] or "{}")
        info["detached"] = bool(detached)
        store.conn.execute("UPDATE lesson_jobs SET pid = COALESCE(pid, ?), args_json = ? WHERE id = ?",
                           (int(pid), json.dumps(info, ensure_ascii=False), job_id))
        store.conn.commit()


def failed_to_start(store, job_id, error, now=None) -> None:
    now = now or _now()
    with store._lock:
        store.conn.execute("UPDATE lesson_jobs SET state = 'falhou', finished_at = ?, error = ? WHERE id = ?",
                           (_iso(now), str(error)[:500], job_id))
        store.conn.commit()


def cancel(store, lesson_id, kill, now=None):
    """Ends the live job of a lesson and its process tree. -> the job payload, or None when nothing runs there.

    After the process is gone: the job is `cancelada`; a lesson in the middle of its roteiro or production stops
    (`falhou`, with the step) so that "Retomar" appears; the run left open is closed. What was already paid stays in
    the cache of the lesson folder."""
    now = now or _now()
    rows = store.conn.execute("SELECT * FROM lesson_jobs WHERE lesson_id = ? AND state IN ('iniciando', 'rodando')"
                              " ORDER BY id DESC", (lesson_id,)).fetchall()
    row = next((r for r in rows if alive(r, now)), None)
    if row is None:
        return None
    if row["pid"]:
        kill(row["pid"])
    stage = row["stage"]
    error = "cancelada na interface" + (f" (etapa {stage})" if stage else "")
    stages = json.loads(row["stages_json"] or "[]")
    for entry in stages:
        if entry.get("state") == "rodando":
            entry.update(state="parou", seconds=round(_age(entry["started_at"], now)))
    with store._lock:
        conn = store.conn
        conn.execute("UPDATE lesson_jobs SET state = 'cancelada', finished_at = ?, error = ?, stages_json = ?"
                     " WHERE id = ? AND state IN ('iniciando', 'rodando')",
                     (_iso(now), error, json.dumps(stages, ensure_ascii=False), row["id"]))
        if row["action"] in ("roteiro", "aula"):
            conn.execute("UPDATE lessons SET status = 'falhou', error = ?, updated_at = ? WHERE id = ?"
                         " AND status NOT IN ('pronta', 'entregue', 'descartada')", (error, _iso(now), lesson_id))
        _close_open_run(conn, lesson_id, error, now)
        conn.commit()
    return payload(get(store, row["id"]), now)


# ---- the process's side ---------------------------------------------------------------------------------------------
class NoProgress:
    """What the engine calls when nobody tracks it (tests, the Manim engine)."""

    def attach(self, lesson_id):
        pass

    def expect(self, names):
        pass

    def stage(self, name):
        pass


class Tracker(NoProgress):
    """The job of this process: it claims the slot (or adopts the row the interface created), beats every BEAT_S
    from a thread, records the steps the engine announces and how the command ended.

    `log` is what the commands print through: the last line it saw is the reason when the command fails."""

    def __init__(self, store, action, lesson_id=None, token=None, out=print, clock=_now, beat_every=BEAT_S):
        self.store, self.action, self.lesson_id, self.token = store, action, lesson_id, token
        self.out, self.clock, self.beat_every = out, clock, beat_every
        self.id = None
        self.stages = []
        self.last_line = ""
        self.finished = False
        self._stop = threading.Event()
        self._thread = None

    # -- the slot
    def claim(self):
        now = self.clock()
        conn = self.store.conn
        if self.token:
            with self.store._lock:
                changed = conn.execute("UPDATE lesson_jobs SET state = 'rodando', pid = ?, beat_at = ? WHERE token = ?"
                                       " AND state = 'iniciando'", (os.getpid(), _iso(now), self.token)).rowcount
                conn.commit()
            if changed != 1:
                raise JobGone("a tarefa desta aula foi cancelada ou não existe mais")
            row = conn.execute("SELECT id, lesson_id FROM lesson_jobs WHERE token = ?", (self.token,)).fetchone()
            self.id, self.lesson_id = row["id"], self.lesson_id or row["lesson_id"]
        else:
            self.token = secrets.token_hex(12)
            self.id = _claim(self.store, "INSERT INTO lesson_jobs(lesson_id, action, origin, token, pid, state, started_at,"
                                         " beat_at) VALUES(?, ?, 'terminal', ?, ?, 'rodando', ?, ?)",
                             (self.lesson_id, self.action, self.token, os.getpid(), _iso(now), _iso(now)), now)
        if self.beat_every:
            self._thread = threading.Thread(target=self._loop, name="lesson-job-beat", daemon=True)
            self._thread.start()
        return self

    def __enter__(self):
        return self if self.id is not None else self.claim()

    def __exit__(self, kind, exc, tb):
        if not self.finished:
            if kind is None:
                self.finish(0)
            elif issubclass(kind, KeyboardInterrupt):
                self.finish(130, "interrompida no terminal (Ctrl+C)", state="cancelada")
            else:
                self.finish(1, f"{type(exc).__name__}: {exc}")
        return False

    def beat(self) -> None:
        with self.store._lock:
            self.store.conn.execute("UPDATE lesson_jobs SET beat_at = ? WHERE id = ? AND state = 'rodando'",
                                    (_iso(self.clock()), self.id))
            self.store.conn.commit()

    def _loop(self):
        while not self._stop.wait(self.beat_every):
            try:
                self.beat()
            except Exception:  # noqa: BLE001 - a database busy for a moment: the next beat comes in 5 s
                pass

    # -- what the engine announces
    def _write(self, **extra) -> None:
        sets = {"stages_json": json.dumps(self.stages, ensure_ascii=False), **extra}
        with self.store._lock:
            self.store.conn.execute(f"UPDATE lesson_jobs SET {', '.join(f'{k} = ?' for k in sets)} WHERE id = ?",
                                    [*sets.values(), self.id])
            self.store.conn.commit()

    def attach(self, lesson_id) -> None:
        self.lesson_id = int(lesson_id)
        self._write(lesson_id=self.lesson_id)

    def expect(self, names) -> None:
        """Steps still to come. They keep the order of STAGES, so "3d", known only after the storyboard, falls in
        its place between the voice and the check."""
        known = {s["name"] for s in self.stages}
        self.stages += [{"name": name, "state": "pendente"} for name in names if name not in known]
        order = {name: n for n, name in enumerate(STAGES)}
        self.stages.sort(key=lambda s: order.get(s["name"], len(STAGES)))
        self._write()

    def _close(self, state, now) -> None:
        for entry in self.stages:
            if entry["state"] == "rodando":
                entry.update(state=state, seconds=round(_age(entry["started_at"], now)))

    def stage(self, name) -> None:
        now = self.clock()
        self._close("feita", now)
        entry = next((s for s in self.stages if s["name"] == name), None)
        if entry is None:
            entry = {"name": name}
            self.stages.append(entry)
        entry.update(state="rodando", started_at=_iso(now))
        entry.pop("seconds", None)
        self._write(stage=name)

    def log(self, *parts) -> None:
        text = " ".join(str(p) for p in parts)
        self.out(text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            self.last_line = lines[-1]

    def finish(self, code, error=None, state=None) -> None:
        self._stop.set()
        now = self.clock()
        self._close("feita" if code == 0 else "parou", now)
        state = state or ("concluida" if code == 0 else "falhou")
        error = None if code == 0 else (error or self.last_line or f"o comando saiu com o código {code}")
        with self.store._lock:
            # a job the interface cancelled stays cancelled; one wrongly marked interrupted gets its real end
            self.store.conn.execute(
                "UPDATE lesson_jobs SET state = ?, finished_at = ?, exit_code = ?, error = ?, stages_json = ?,"
                " beat_at = ? WHERE id = ? AND state IN ('rodando', 'interrompida')",
                (state, _iso(now), int(code), error[:500] if error else None, json.dumps(self.stages, ensure_ascii=False),
                 _iso(now), self.id))
            self.store.conn.commit()
        self.finished = True


# ---- processes ----------------------------------------------------------------------------------------------------
def python_exe() -> str:
    """python.exe beside pythonw.exe: the interface runs windowless, but the lesson's output has to reach its log."""
    exe = Path(sys.executable)
    console = exe.with_name("python.exe")
    return str(console if exe.name.lower() == "pythonw.exe" and console.exists() else exe)


def command(args) -> list:
    return [python_exe(), "-m", "sotawhat.cli", "lessons", *[str(a) for a in args]]


def spawn_process(args, log_path, cwd=None, popen=subprocess.Popen) -> dict:
    """Starts `sotawhat lessons <args>` with its output appended to `log_path`. -> {"pid", "detached"}.

    Windows: a hidden console (CREATE_NO_WINDOW, inherited by node, Chrome and FFmpeg, so no window flashes), its own
    process group, and out of the job object of the scheduled task (CREATE_BREAKAWAY_FROM_JOB), else the end of the
    task would end the lesson. A job that refuses the breakaway makes the creation fail; then the lesson starts inside
    it, and `detached` says so."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    cmd = command(args)
    with open(log_path, "ab") as out:
        options = dict(stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, cwd=str(cwd or os.getcwd()),
                       env=env, close_fds=True)
        if os.name == "nt":
            base = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
            try:
                proc, detached = popen(cmd, creationflags=base | CREATE_BREAKAWAY_FROM_JOB, **options), True
            except OSError:
                proc, detached = popen(cmd, creationflags=base, **options), False
        else:
            proc, detached = popen(cmd, start_new_session=True, **options), True
            threading.Thread(target=proc.wait, daemon=True).start()        # reaps it: no zombie
    return {"pid": proc.pid, "detached": detached}


def _gone_windows(pid, wait_s) -> bool:
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x00100000, False, int(pid))      # SYNCHRONIZE
    if not handle:
        return True                                                 # no such process
    try:
        return kernel.WaitForSingleObject(handle, int(wait_s * 1000)) == 0
    finally:
        kernel.CloseHandle(handle)


def kill_tree(pid, wait_s=10.0) -> bool:
    """Ends the process and everything it started (node, Chrome, FFmpeg). -> True when it is gone."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(int(pid)), "/T", "/F"], capture_output=True, timeout=30,
                       creationflags=CREATE_NO_WINDOW)
        return _gone_windows(pid, wait_s)
    try:
        os.killpg(os.getpgid(int(pid)), signal.SIGTERM)
    except ProcessLookupError:
        return True
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        try:
            os.kill(int(pid), 0)
        except ProcessLookupError:
            return True
        time.sleep(0.2)
    return False
