# sotawhat/lessons/render.py
"""Renders one scene: Manim (Python) or a three.js page captured by Playwright, both in the tools environment.

Code written by an LLM runs on this PC, so before any render it passes a policy: Python may only import the kit,
math, numpy and random, and may not touch files, processes, the network or dunders; JavaScript gets no imports,
network, DOM or timers (the kit provides everything). Failures come back as RenderError with a short message for
the LLM that repairs the scene."""
import ast
import json
import re
import shutil
import subprocess
from pathlib import Path

from sotawhat.lessons.tools import KIT

PY_IMPORTS = {"lesson_kit", "math", "numpy", "random"}
PY_FORBIDDEN = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr",
                "delattr", "input", "breakpoint", "help", "exit", "quit", "memoryview", "os", "sys", "subprocess",
                "shutil", "socket", "pathlib", "Path", "importlib", "ctypes", "pickle", "config", "SVGMobject",
                "ImageMobject", "Code", "ThreeDScene", "MovingCameraScene"}
JS_FORBIDDEN = re.compile(r"\b(fetch|XMLHttpRequest|WebSocket|EventSource|importScripts|localStorage|sessionStorage|"
                          r"indexedDB|document|window|navigator|location|eval|Function|setTimeout|setInterval|"
                          r"requestAnimationFrame|Worker|postMessage|Date|performance)\b|\bMath\.random\b|"
                          r"\bimport\s*\(|^\s*import\s", re.M)
MANIM_TIMEOUT, CAPTURE_TIMEOUT = 900, 1200


class RenderError(Exception):
    pass


def python_problems(code) -> list:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"erro de sintaxe na linha {exc.lineno}: {exc.msg}"]
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            problems += [f"import {a.name} não é permitido" for a in node.names if a.name.split(".")[0] not in PY_IMPORTS]
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in PY_IMPORTS:
                problems.append(f"from {node.module} import … não é permitido (use `from lesson_kit import *`)")
        elif isinstance(node, ast.Name) and node.id in PY_FORBIDDEN:
            problems.append(f"`{node.id}` não é permitido nas cenas")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            problems.append(f"atributo privado `{node.attr}` não é permitido")
        elif isinstance(node, ast.Attribute) and node.attr in ("play", "wait") and getattr(node.value, "id", "") == "self":
            problems.append(f"não chame self.{node.attr}: use self.beat(...) uma vez por frase (o tempo é automático)")
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Cena"]
    if not classes:
        problems.append("defina `class Cena(LessonScene)` com o método construct")
    elif not any(getattr(b, "id", None) == "LessonScene" for b in classes[0].bases):
        problems.append("a classe Cena precisa herdar de LessonScene")
    return list(dict.fromkeys(problems))


def js_problems(code) -> list:
    bare = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)                  # comments may say "document" or "Date"
    bare = re.sub(r"(?<![:\"'])//[^\n]*", " ", bare)
    problems = [f"`{m.group(0).strip()}` não é permitido na cena (o kit já dá THREE, câmera, tempo e rótulos)"
                for m in JS_FORBIDDEN.finditer(bare)]
    if not re.search(r"export\s+default\s+function", code):
        problems.append("exporte `export default function build(kit) { …; return { update(t) { … } }; }`")
    return list(dict.fromkeys(problems))


def _tail(text, limit=2500) -> str:
    """The useful end of a traceback: from the last 'Traceback' on, without Manim's progress bars."""
    lines = [l for l in text.splitlines() if l.strip() and "it/s]" not in l and "Animation" not in l[:12]]
    joined = "\n".join(lines)
    cut = joined.rfind("Traceback")
    return (joined[cut:] if cut != -1 else joined)[-limit:]


def write_beats(scene_dir, beats_text, durations) -> Path:
    path = Path(scene_dir) / "scene.json"
    path.write_text(json.dumps({"beats": [{"text": t, "duration": d} for t, d in zip(beats_text, durations)]},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def render_manim(tools, scene_dir, kit_dir, cache_dir, lenient=False, script="scene.py", cls="Cena", out_name="out.mp4",
                 spec_env=None) -> Path:
    scene_dir = Path(scene_dir).resolve()
    media = scene_dir / "media"
    shutil.rmtree(media, ignore_errors=True)
    env = {"PYTHONPATH": Path(kit_dir).resolve(), "LESSON_CACHE": Path(cache_dir).resolve(), "LESSON_LENIENT": "1" if lenient else "0",
           **(spec_env or {"LESSON_SCENE": scene_dir / "scene.json"})}
    try:
        done = tools.run([tools.python, "-m", "manim", "render", "-r", "1920,1080", "--fps", "30", "--disable_caching",
                          "-v", "WARNING", "--media_dir", media, "-o", out_name, script, cls], cwd=scene_dir,
                         timeout=MANIM_TIMEOUT, **env)
    except subprocess.TimeoutExpired:
        raise RenderError(f"o render passou de {MANIM_TIMEOUT // 60} min: simplifique a cena (menos objetos, "
                          "sem laços enormes)") from None
    found = sorted(media.glob(f"videos/**/{out_name}"))
    if done.returncode != 0 or not found:
        raise RenderError(_tail(done.stderr or done.stdout) or f"o Manim terminou com código {done.returncode}")
    target = scene_dir / out_name
    shutil.move(str(found[0]), str(target))
    shutil.rmtree(media, ignore_errors=True)
    warnings = [l for l in done.stdout.splitlines() if l.startswith("AVISO de layout")]
    (scene_dir / "warnings.txt").write_text("\n".join(warnings), encoding="utf-8")
    return target


def render_three(tools, lessons_root, scene_dir, lenient=False) -> Path:
    scene_dir, lessons_root = Path(scene_dir).resolve(), Path(lessons_root).resolve()
    page = scene_dir.relative_to(lessons_root).as_posix() + "/index.html"
    out = scene_dir / "out.mp4"
    args = [tools.python, KIT / "capture.py", lessons_root, page, out] + (["--lenient"] if lenient else [])
    try:
        done = tools.run(args, cwd=scene_dir, timeout=CAPTURE_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RenderError(f"a captura passou de {CAPTURE_TIMEOUT // 60} min: simplifique a cena (menos objetos)") from None
    if done.returncode != 0 or not out.exists():
        raise RenderError((done.stderr or done.stdout).strip()[-2500:] or f"captura terminou com código {done.returncode}")
    warnings = [l for l in done.stdout.splitlines() if l.startswith("AVISO de layout")]
    (scene_dir / "warnings.txt").write_text("\n".join(warnings), encoding="utf-8")
    return out


def write_three_page(scene_dir, title):
    html = (KIT / "scene.html").read_text(encoding="utf-8").replace("{title}", title.replace("<", "&lt;"))
    (Path(scene_dir) / "index.html").write_text(html, encoding="utf-8")
