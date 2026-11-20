# sotawhat/lessons/launcher.py
"""What the interface does with lessons (F1, docs/superpowers/specs/2026-11-20-aulas-pela-interface-design.md): it
starts a job (`sotawhat lessons …` in a process of its own, lessons/jobs.py), cancels it, and reads what the review
step shows beside the plan: the voice credits left and whether the tools of the production are installed."""
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from sotawhat.lessons import jobs


class Launcher:
    def __init__(self, root, cwd=None, spawn=jobs.spawn_process, kill=jobs.kill_tree, credits=None, ready=None,
                 telegram=False, price=(5.0, 30000), ttl=60.0, clock=time.monotonic):
        self.root, self.cwd = Path(root), str(cwd or os.getcwd())
        self.spawn, self.kill = spawn, kill
        self._credits, self._ready = credits or (lambda: None), ready or (lambda: [])
        self.telegram, self.price, self.ttl, self.clock = telegram, tuple(price), ttl, clock
        self._cache, self._lock = {}, threading.Lock()

    @classmethod
    def from_settings(cls, settings):
        from sotawhat.lessons import eleven
        from sotawhat.lessons import hyperframes as hfm
        from sotawhat.lessons.pipeline import lessons_root

        def credits():
            return eleven.credit_balance(settings.elevenlabs_api_key)

        def ready():
            problems = []
            if not settings.openrouter_api_key:
                problems.append("OPENROUTER_API_KEY vazia no .env: sem ela não há roteiro")
            if not settings.elevenlabs_api_key:
                problems.append("ELEVENLABS_API_KEY vazia no .env: sem ela não há voz")
            hf = hfm.hf_tools(settings)
            if not hf.ready():
                problems.append(f"HyperFrames incompleto em {hf.root} (veja Animated lessons no README)")
            return problems

        return cls(lessons_root(settings), credits=credits, ready=ready,
                   telegram=bool(settings.telegram_bot_token and settings.telegram_chat_id),
                   price=(settings.sotawhat_elevenlabs_plan_usd, settings.sotawhat_elevenlabs_plan_credits))

    def _cached(self, name, compute):
        with self._lock:
            hit = self._cache.get(name)
            if hit and self.clock() - hit[0] < self.ttl:
                return hit[1]
        value = compute()
        with self._lock:
            self._cache[name] = (self.clock(), value)
        return value

    def credits(self):
        """The ElevenLabs balance, read at most once a minute (it spends nothing, but it is a call)."""
        return self._cached("credits", self._credits)

    def ready(self) -> list:
        """What is missing for a production (keys, HyperFrames); [] when nothing is."""
        return self._cached("ready", self._ready)

    def forget_credits(self) -> None:
        with self._lock:
            self._cache.pop("credits", None)

    def start(self, store, lesson_id, action, args, send=None, before=None) -> int:
        """Asks for the slot, runs `before()` (the interface clears a plan to redo only once the slot is its own), then
        starts `sotawhat lessons <args> --job TOKEN` with its output in the lesson's job.log. -> the job id.
        Raises jobs.Busy, or the error of the process creation (the job is then marked failed)."""
        log_path = self.root / f"{int(lesson_id):03d}" / "job.log"
        job_id, token = jobs.create_pending(store, lesson_id, action, log_path, args, send=send)
        try:
            if before is not None:
                before()
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as out:
                out.write(f"\n{jobs.HEADER}{datetime.now():%Y-%m-%d %H:%M:%S} · {action} · sotawhat lessons "
                          f"{' '.join(str(a) for a in args)}\n")
            info = self.spawn([*[str(a) for a in args], "--job", token], log_path, self.cwd)
        except Exception as exc:
            jobs.failed_to_start(store, job_id, f"não consegui iniciar o processo: {exc}")
            raise
        jobs.started(store, job_id, info["pid"], info["detached"])
        return job_id

    def cancel(self, store, lesson_id):
        return jobs.cancel(store, lesson_id, kill=self.kill)
