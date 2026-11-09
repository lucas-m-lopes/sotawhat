# sotawhat/lessons/tools.py
"""The lessons tools environment, data/tools/lessons: a uv venv with Manim, Playwright, matplotlib, Piper and
FFmpeg (versions in kit/requirements.txt, only releases at least two weeks old), Chromium in browsers/ and the
Brazilian Portuguese Piper voices in voices/. Everything there runs as a subprocess with a minimal environment
(no API keys), because part of what it runs is code written by an LLM."""
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

KIT = Path(__file__).parent / "kit"
VENDOR_THREE = Path(__file__).resolve().parents[1] / "web" / "static" / "vendor" / "three"
EXCLUDE_NEWER = "2026-10-26"
PIPER_VOICES = ("faber", "cadu", "jeff")              # pt_BR medium, datasets CC0
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR"
_KEEP_ENV = ("SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA",
             "HOMEDRIVE", "HOMEPATH", "COMSPEC", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "LANG")


@dataclass
class Tools:
    root: Path

    @classmethod
    def from_settings(cls, settings):
        return cls((Path(settings.sotawhat_data_dir) / "tools" / "lessons").resolve())

    @property
    def python(self) -> Path:
        return self.root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    @property
    def browsers(self) -> Path:
        return self.root / "browsers"

    @property
    def voices(self) -> Path:
        return self.root / "voices"

    def ffmpeg(self) -> str:
        found = sorted((self.root / ".venv").glob("**/imageio_ffmpeg/binaries/ffmpeg*"))
        return str(found[-1]) if found else (shutil.which("ffmpeg") or "ffmpeg")

    def env(self, **extra) -> dict:
        """A minimal environment: no secrets reach code written by an LLM."""
        out = {k: os.environ[k] for k in _KEEP_ENV if k in os.environ}
        out.update({"PLAYWRIGHT_BROWSERS_PATH": str(self.browsers), "PYTHONIOENCODING": "utf-8",
                    "MPLCONFIGDIR": str(self.root / "mpl")})
        out.update({k: str(v) for k, v in extra.items()})
        return out

    def run(self, args, cwd, timeout, **extra_env) -> subprocess.CompletedProcess:
        return subprocess.run([str(a) for a in args], cwd=str(cwd), env=self.env(**extra_env), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=timeout,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def status(self) -> dict:
        chromium = sorted(self.browsers.glob("chromium_headless_shell-*")) if self.browsers.exists() else []
        return {"python": self.python.exists(), "chromium": bool(chromium),
                "voices": [v for v in PIPER_VOICES if (self.voices / f"pt_BR-{v}-medium.onnx").exists()],
                "ffmpeg": Path(self.ffmpeg()).exists()}

    def ready(self) -> bool:
        s = self.status()
        return s["python"] and s["chromium"] and s["ffmpeg"] and bool(s["voices"])


def sync_kit(lessons_root) -> Path:
    """Copies the kit (and three.js) to data/lessons/_kit, where the renderers and the /lessons pages find it."""
    target = Path(lessons_root) / "_kit"
    target.mkdir(parents=True, exist_ok=True)
    for src in list(KIT.glob("*")) + list(VENDOR_THREE.glob("*.js")):
        if src.is_file() and src.suffix in (".py", ".js", ".css", ".html", ".txt"):
            dst = target / src.name
            if not dst.exists() or dst.read_bytes() != src.read_bytes():
                shutil.copyfile(src, dst)
    return target


def setup(tools, log=print, download=None) -> bool:
    """Creates or completes the environment: venv + pinned packages (uv), Chromium, Piper voices. Idempotent."""
    uv = shutil.which("uv")
    if not tools.python.exists():
        if not uv:
            log("uv não encontrado: instale com `winget install astral-sh.uv` e rode de novo")
            return False
        tools.root.mkdir(parents=True, exist_ok=True)
        _step(log, "ambiente", [uv, "venv", str(tools.root / ".venv"), "--python", f"{sys.version_info.major}.{sys.version_info.minor}"])
    if uv:
        _step(log, "pacotes", [uv, "pip", "install", "--python", str(tools.python), "--exclude-newer", EXCLUDE_NEWER,
                               "-r", str(KIT / "requirements.txt")])
    if not tools.status()["chromium"]:
        env = {**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(tools.browsers)}
        log("baixando o Chromium do Playwright (~150 MB)…")
        subprocess.run([str(tools.python), "-m", "playwright", "install", "chromium"], env=env, check=False)
    tools.voices.mkdir(parents=True, exist_ok=True)
    for name in PIPER_VOICES:
        for suffix in (".onnx", ".onnx.json"):
            target = tools.voices / f"pt_BR-{name}-medium{suffix}"
            if not target.exists():
                log(f"baixando a voz {name}{suffix}…")
                (download or _download)(f"{PIPER_BASE}/{name}/medium/pt_BR-{name}-medium{suffix}", target)
    status = tools.status()
    log(f"ferramentas: python {'ok' if status['python'] else 'falta'} · chromium {'ok' if status['chromium'] else 'falta'}"
        f" · ffmpeg {'ok' if status['ffmpeg'] else 'falta'} · vozes {', '.join(status['voices']) or 'nenhuma'}")
    return tools.ready()


def _step(log, name, cmd):
    log(f"{name}: {' '.join(Path(cmd[0]).name if i == 0 else c for i, c in enumerate(cmd))}")
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise RuntimeError(f"{name} falhou: {(done.stderr or done.stdout)[-800:]}")


def _download(url, target):
    import httpx

    tmp = target.with_suffix(target.suffix + ".part")
    with httpx.Client(timeout=120, follow_redirects=True) as client, client.stream("GET", url) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    tmp.replace(target)


_DURATION = re.compile(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)")


def media_seconds(tools, path) -> float:
    """Duration of a media file from FFmpeg's header line (imageio-ffmpeg ships no ffprobe)."""
    done = subprocess.run([tools.ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    match = _DURATION.search(done.stderr)
    if not match:
        raise RuntimeError(f"sem duração em {path}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)
