# sotawhat/lessons/hyperframes.py
"""The HyperFrames side of the lessons: the pinned toolchain in data/tools/hyperframes (npm, versions at least two
weeks old, telemetry off), the project a lesson becomes (index.html + one sub-composition per scene, the kit,
the libraries, the fonts and the narration), and the CLI calls: check, snapshot and render.

Timing is computed here, from the ElevenLabs word times: an action starts when its cue word is spoken (a little
before, so the part is there as the word lands), the captions follow the words, and every scene owns the slot
from the start of its audio to the start of the next one (its exit happens in the silence between them)."""
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from sotawhat.lessons.storyboard import _fold

HF_VERSION = "0.8.206"
KIT = Path(__file__).parent / "motion_kit"
FONTS = {"@fontsource/manrope/files": [f"manrope-latin-{w}-normal.woff2" for w in (400, 500, 600, 700, 800)],
         "@fontsource/fraunces/files": [f"fraunces-latin-{w}-{s}.woff2" for w in (400, 600) for s in ("normal", "italic")]}
LEAD_S = 0.12            # an element appears this much before its word
FPS = 30


class HFError(Exception):
    pass


@dataclass
class HFTools:
    root: Path            # data/tools/hyperframes (package.json + node_modules)
    ffmpeg: Path
    ffprobe: Path
    browser: Path

    @property
    def modules(self) -> Path:
        return self.root / "node_modules"

    def env(self) -> dict:
        keep = ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
                "HOMEDRIVE", "HOMEPATH", "COMSPEC", "PATHEXT", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE")
        env = {k: os.environ[k] for k in keep if k in os.environ}      # no secrets reach node or Chrome
        env.update(HYPERFRAMES_NO_TELEMETRY="1", DO_NOT_TRACK="1", HYPERFRAMES_FFMPEG_PATH=str(self.ffmpeg),
                   HYPERFRAMES_FFPROBE_PATH=str(self.ffprobe), HYPERFRAMES_BROWSER_PATH=str(self.browser), CI="1")
        return env

    def ready(self) -> bool:
        return all(p.exists() for p in (self.modules / "hyperframes", self.ffmpeg, self.ffprobe, self.browser))

    def run(self, args, timeout=3600, cwd=None) -> subprocess.CompletedProcess:
        entry = self.modules / "hyperframes" / "bin" / "hyperframes.mjs"    # not hyperframes-localize-fonts.mjs
        cmd = (["node", str(entry)] if entry.exists() else ["npx.cmd" if os.name == "nt" else "npx", "hyperframes"]) \
            + [str(a) for a in args]
        return subprocess.run(cmd, cwd=str(cwd or self.root), env=self.env(), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)


def hf_tools(settings) -> HFTools:
    data = Path(settings.sotawhat_data_dir).resolve() / "tools"
    lessons = data / "lessons"
    ffmpeg = next(iter(sorted((lessons / ".venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries").glob("ffmpeg*.exe"))), None)
    browser = next(iter(sorted((lessons / "browsers").glob("chromium_headless_shell-*/*/chrome-headless-shell.exe"))), None)
    root = data / "hyperframes"
    return HFTools(root, ffmpeg or Path("ffmpeg"), root / "node_modules" / "@ffprobe-installer" / "win32-x64" / "ffprobe.exe",
                   browser or Path("chrome-headless-shell"))


# ---- timing ------------------------------------------------------------------------------------------------------
def cue_time(words, beat, cue, beat_start) -> float:
    """Global time of the first word of `cue` inside sentence `beat`, else the start of the sentence."""
    first = next((_fold(w) for w in cue.split() if _fold(w)), "")
    if first:
        for w in words:
            if w["beat"] == beat and _fold(w["text"]) == first:
                return w["start"]
    return beat_start


def scene_actions(board_scene, nar_scene, slot_start) -> list:
    """[{do, ids, text, value, t, until}] with t local to the scene slot, in time order."""
    beats, words = nar_scene["beats"], nar_scene["words"]
    out = []
    for step in board_scene.steps:
        if step.beat >= len(beats):
            continue
        b_start, b_end = beats[step.beat]
        nxt = beats[step.beat + 1][0] if step.beat + 1 < len(beats) else nar_scene["end"]
        for k, a in enumerate(step.actions):
            at = cue_time(words, step.beat, a.cue, b_start) - LEAD_S
            out.append({"do": a.do, "ids": list(a.ids), "text": a.text, "value": a.value,
                        "t": round(max(0.05, at - slot_start), 3), "until": round(nxt - slot_start, 3), "_k": k})
    out.sort(key=lambda x: (x["t"], x["_k"]))
    for x in out:
        x.pop("_k")
    return out


def caption_groups(words, max_words=6, max_chars=42, pause=0.35) -> list:
    """Words → caption groups (one on screen at a time). A sentence is cut at its pauses and then into groups of
    near-equal size (13 words → 5 + 4 + 4, never 6 + 6 + 1)."""
    runs, cur = [], []
    for w in words:
        if cur and (w["beat"] != cur[-1]["beat"] or w["start"] - cur[-1]["end"] >= pause):
            runs.append(cur)
            cur = []
        cur.append(w)
    if cur:
        runs.append(cur)
    merged = []
    for run in runs:                      # "… a soma dê" + "um." would leave a lonely word on screen
        if merged and len(run) <= 2 and run[0]["beat"] == merged[-1][-1]["beat"]:
            merged[-1] = merged[-1] + run
        else:
            merged.append(run)
    runs = merged
    groups = []
    for run in runs:
        chars = len(" ".join(x["text"] for x in run))
        parts = max(-(-len(run) // max_words), -(-chars // max_chars), 1)
        size = -(-len(run) // parts)
        for i in range(0, len(run), size):
            groups.append(run[i:i + size])
    out = []
    for n, g in enumerate(groups):
        start = max(0.0, g[0]["start"] - 0.08)
        end = g[-1]["end"] + 0.3
        if n + 1 < len(groups):
            end = min(end, groups[n + 1][0]["start"] - 0.1)
        out.append({"start": round(start, 3), "end": round(max(end, start + 0.4), 3),
                    "words": [{"text": w["text"], "start": round(w["start"], 3)} for w in g]})
    return out


def slots(nar) -> list:
    """[(start, duration)] of each scene: from its audio start to the next scene's (the last one to the end)."""
    scenes = nar["scenes"]
    out = []
    for i, s in enumerate(scenes):
        end = scenes[i + 1]["start"] if i + 1 < len(scenes) else nar["duration"]
        out.append((round(s["start"], 3), round(end - s["start"], 3)))
    return out


# ---- the project -------------------------------------------------------------------------------------------------
def _js(data) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _host(cid, start, duration, z, kind="graphics") -> str:
    return (f'  <div id="{cid}" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" '
            f'data-start="{start}" data-duration="{duration}" data-track-index="{z}" data-track-kind="{kind}" '
            f'data-width="1920" data-height="1080" style="z-index:{z}"></div>')


def _scene_file(cid, script, module=False) -> str:
    kind = ' type="module"' if module else ""
    return (f'<template>\n  <style>#root {{ position: absolute; inset: 0; }}</style>\n'
            f'  <div id="root" data-composition-id="{cid}" data-width="1920" data-height="1080"></div>\n'
            f"  <script{kind}>{script}</script>\n</template>\n")


def copy_assets(hf, project, wav) -> None:
    assets = project / "assets"
    for sub in ("lib", "kit", "fonts"):
        (assets / sub).mkdir(parents=True, exist_ok=True)
    m = hf.modules
    shutil.copy2(m / "gsap" / "dist" / "gsap.min.js", assets / "lib")
    for name in ("three.module.js", "three.core.js"):
        shutil.copy2(m / "three" / "build" / name, assets / "lib")
    katex = assets / "lib" / "katex"
    if not katex.exists():
        katex.mkdir()
        shutil.copy2(m / "katex" / "dist" / "katex.min.js", katex)
        shutil.copy2(m / "katex" / "dist" / "katex.min.css", katex)
        shutil.copytree(m / "katex" / "dist" / "fonts", katex / "fonts")
    for folder, names in FONTS.items():
        for name in names:
            shutil.copy2(m / folder / name, assets / "fonts")
    for f in KIT.iterdir():
        if f.suffix in (".js", ".css"):
            shutil.copy2(f, assets / "kit")
    shutil.copy2(wav, assets / "narration.wav")


def compose(hf, project, plan, board, nar, lesson_id) -> dict:
    """Writes the HyperFrames project of a lesson. -> {"duration", "scenes": [{"id", "start", "dur", "template"}]}."""
    project = Path(project)
    if (project / "compositions").exists():
        shutil.rmtree(project / "compositions")
    (project / "compositions").mkdir(parents=True)
    copy_assets(hf, project, nar["wav"])
    duration = round(nar["duration"], 3)
    intro = nar["intro"]
    hosts = [_host("bg", 0, duration, 0), _host("intro", 0, intro, 10)]
    (project / "compositions" / "bg.html").write_text(_scene_file("bg", "MK.ground(\"bg\", " + _js(
        {"duration": duration, "start": intro, "end": nar["scenes"][-1]["end"]}) + ");"), encoding="utf-8")
    (project / "compositions" / "intro.html").write_text(_scene_file("intro", "MK.intro(\"intro\", " + _js(
        {"duration": intro, "kicker": f"Aula {lesson_id} · sotawhat", "title": plan.title, "sub": plan.objective}) + ");"),
        encoding="utf-8")
    scenes = []
    for n, ((start, dur), scene, nscene, bscene) in enumerate(zip(slots(nar), plan.scenes, nar["scenes"], board.scenes), 1):
        cid = f"s{n:02d}"
        data = {"num": n, "title": scene.title, "dur": dur, "template": bscene.template,
                "nodes": [x.model_dump() for x in bscene.nodes], "edges": [x.model_dump() for x in bscene.edges],
                "bars": [x.model_dump() for x in bscene.bars], "vectors": [x.model_dump() for x in bscene.vectors],
                "patches": bscene.patches.model_dump(), "formula": [x.model_dump() for x in bscene.formula],
                "actions": scene_actions(bscene, nscene, start)}
        if bscene.template == "vectors3d":
            script = (f'import {{ mount3d }} from "./assets/kit/scene3d.js"; mount3d("{cid}", {_js(data)}, {start});')
            (project / "compositions" / f"{cid}.html").write_text(_scene_file(cid, script, module=True), encoding="utf-8")
        else:
            (project / "compositions" / f"{cid}.html").write_text(_scene_file(cid, f'MK.scene("{cid}", {_js(data)});'),
                                                                   encoding="utf-8")
        hosts.append(_host(cid, start, dur, 20 + n))
        scenes.append({"id": cid, "start": start, "dur": dur, "template": bscene.template,
                       "beats": [(round(a - start, 3), round(b - start, 3)) for a, b in nscene["beats"]]})
    words = [w for s in nar["scenes"] for w in s["words"]]
    (project / "compositions" / "caps.html").write_text(_scene_file("caps", "MK.captions(\"caps\", " + _js(
        caption_groups(words)) + f", {duration});"), encoding="utf-8")
    hosts.append(_host("caps", 0, duration, 60, kind="captions"))
    index = "\n".join([
        "<!doctype html>", '<html lang="pt-BR">', "<head>", '<meta charset="utf-8">',
        '<link rel="stylesheet" href="assets/lib/katex/katex.min.css">',
        '<link rel="stylesheet" href="assets/kit/kit.css">',
        '<script src="assets/lib/gsap.min.js"></script>',
        '<script src="assets/lib/katex/katex.min.js"></script>',
        '<script src="assets/kit/kit.js"></script>',
        "<style>html, body { margin: 0; background: #0a101e; }</style>", "</head>", "<body>",
        f'<div id="root" data-composition-id="main" data-start="0" data-duration="{duration}" data-width="1920" '
        'data-height="1080">', *hosts,
        f'  <audio id="narration" class="clip" data-start="0" data-duration="{duration}" data-track-index="90" '
        'data-volume="1" src="assets/narration.wav"></audio>', "</div>",
        '<script>window.__timelines = window.__timelines || {}; '
        'window.__timelines["main"] = gsap.timeline({ paused: true });</script>', "</body>", "</html>", ""])
    (project / "index.html").write_text(index, encoding="utf-8")
    layout = {"duration": duration, "intro": intro, "scenes": scenes}
    (project / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=1), encoding="utf-8")
    return layout


# ---- CLI ---------------------------------------------------------------------------------------------------------
def _json_tail(text):
    start = text.find("{")
    while start >= 0:
        try:
            return json.loads(text[start:])
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
    return None


def check(hf, project) -> dict:
    """`hyperframes check --json` -> {"ok", "errors": [...], "warnings": [...]}."""
    out = hf.run(["check", str(project), "--json"], timeout=1800)
    data = _json_tail(out.stdout) or {}
    errors, warnings = [], []
    for part in ("lint", "runtime", "layout", "motion"):
        for f in (data.get(part) or {}).get("findings", []):
            sev = (f.get("severity") or f.get("level") or "").lower()
            line = f"{part}: {f.get('rule') or f.get('code') or ''} {f.get('message') or ''}".strip()
            (errors if sev == "error" else warnings).append(line)
    return {"ok": bool(data.get("ok")) and not errors, "errors": errors, "warnings": warnings,
            "raw": None if data else (out.stdout[-2000:] + out.stderr[-2000:])}


def snapshot(hf, project, times, out_dir) -> list:
    """PNG frames at the given times (seconds), via `hyperframes snapshot --at`."""
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    res = hf.run(["snapshot", str(project), "--at", ",".join(f"{t:.2f}" for t in times), "--no-end",
                  "--output", str(out_dir)], timeout=1800)
    made = sorted(out_dir.glob("*.png"))
    if res.returncode != 0 and not made:
        raise HFError(f"snapshot falhou: {(res.stderr or res.stdout)[-800:]}")
    return made


def render(hf, project, out, quality="looks", workers="auto") -> dict:
    out = Path(out)
    res = hf.run(["render", str(project), "--output", str(out), "--fps", str(FPS), "--quality", quality,
                  "--workers", str(workers)], timeout=4 * 3600)
    if res.returncode != 0 or not out.exists():
        raise HFError(f"render falhou: {(res.stderr or res.stdout)[-1500:]}")
    summary = [line.strip() for line in res.stdout.splitlines() if "rendered in" in line or "capture" in line][-2:]
    return {"path": str(out), "bytes": out.stat().st_size, "summary": summary}
