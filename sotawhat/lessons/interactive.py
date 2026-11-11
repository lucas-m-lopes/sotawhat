# sotawhat/lessons/interactive.py
"""The 3D of a lesson to open anywhere (2026-11-11): data/lessons/<id>/interativo.html, one self-contained file.

One tab per 3D scene of the lesson (vectors3d, volume3d and the mechanism3d scenes whose module passed the
probe), running the same code as the video: the kit (scene3d.js) and the scene modules bundled with three.js by
the esbuild that HyperFrames ships, plus GSAP, kit.js, the player, the fonts and the narration of each scene (an
MP3 cut from the lesson's narration) embedded. Nothing is fetched: it opens from the Telegram document on a phone
or from the Aulas tab of the local interface. On it you hear the scene, drag the timeline, drag to turn the
camera and pinch or scroll to zoom (the kit's own orbit, so the labels stay on their parts)."""
import base64
import html
import re
import subprocess
from pathlib import Path

from sotawhat.lessons import hyperframes as hfm
from sotawhat.lessons.storyboard import TEMPLATES_3D

NAME = "interativo.html"
BUNDLE_TIMEOUT = 300


class InteractiveError(Exception):
    pass


def esbuild(hf) -> Path:
    exe = hf.modules / "@esbuild" / "win32-x64" / "esbuild.exe"
    return exe if exe.exists() else hf.modules / ".bin" / "esbuild"


def scenes_3d(board, codes) -> list:
    """The scene numbers shown on the page: the 3D templates, a mechanism3d scene only with its checked module."""
    return [n for n, s in enumerate(board.scenes, 1)
            if s.template in TEMPLATES_3D and (s.template != "mechanism3d" or n in codes)]


def entry_source(codes, shown) -> str:
    lines = ['import { mount3d, mountVolume, mountFree, orbit } from "../hf/assets/kit/scene3d.js";']
    names = []
    for n in shown:
        if n in codes:
            lines.append(f'import b{n:02d} from "./{Path(codes[n]).name}";')
            names.append(f"s{n:02d}: b{n:02d}")
    lines.append("window.__interactive = { mount3d, mountVolume, mountFree, orbit, builds: { " + ", ".join(names) + " } };")
    return "\n".join(lines) + "\n"


def bundle(hf, work, codes, shown) -> str:
    """The kit, three.js and the scene modules as one minified script (IIFE)."""
    folder = work / "3d"
    folder.mkdir(parents=True, exist_ok=True)
    entry, out = folder / "interactive-entry.js", folder / "interactive-bundle.js"
    entry.write_text(entry_source(codes, shown), encoding="utf-8")
    done = subprocess.run([str(esbuild(hf)), str(entry), "--bundle", "--minify", "--format=iife", "--target=es2020",
                           "--legal-comments=none", "--log-level=error", f"--outfile={out}"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=BUNDLE_TIMEOUT,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if done.returncode != 0 or not out.exists():
        raise InteractiveError(f"esbuild falhou: {(done.stderr or done.stdout)[-800:]}")
    return out.read_text(encoding="utf-8")


def scene_audio(ffmpeg, wav, start, dur, out) -> str:
    """The narration of one scene as a data URL (MP3, mono, 64 kb/s)."""
    done = subprocess.run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-t",
                           f"{dur:.3f}", "-i", str(wav), "-ac", "1", "-b:a", "64k", str(out)],
                          capture_output=True, text=True, timeout=300, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if done.returncode != 0 or not Path(out).exists():
        raise InteractiveError(f"o áudio da cena não saiu: {done.stderr[-400:]}")
    return "data:audio/mpeg;base64," + base64.b64encode(Path(out).read_bytes()).decode("ascii")


def inline_css(hf) -> str:
    """kit.css with its fonts as data URLs, and the player's CSS."""
    fonts = {name: hf.modules / folder / name for folder, names in hfm.FONTS.items() for name in names}

    def font(m):
        path = fonts.get(m.group(1))
        if path is None or not path.exists():
            return m.group(0)
        return 'url("data:font/woff2;base64,' + base64.b64encode(path.read_bytes()).decode("ascii") + '")'

    css = re.sub(r'url\("\.\./fonts/([^"]+)"\)', font, (hfm.KIT / "kit.css").read_text(encoding="utf-8"))
    return css + "\n" + (hfm.KIT / "player.css").read_text(encoding="utf-8")


def _script(js) -> str:
    return "<script>" + js.replace("</script", "<\\/script") + "</script>"


def page(title, kicker, css, scripts, scenes) -> str:
    boot = ("(function () {\n  var I = window.__interactive, S = " + hfm._js(scenes) + ";\n"
            "  PLAYER.start({ kicker: " + hfm._js(kicker) + ", title: " + hfm._js(title) + ", orbit: I.orbit, "
            "scenes: S.map(function (s) {\n"
            "    return { id: s.id, num: s.num, title: s.title, dur: s.dur, captions: s.captions, audio: s.audio,\n"
            "      mount: function () {\n"
            '        if (s.template === "vectors3d") I.mount3d(s.id, s.data, 0);\n'
            '        else if (s.template === "volume3d") I.mountVolume(s.id, s.data, 0);\n'
            "        else I.mountFree(s.id, s.data, 0, I.builds[s.id]);\n"
            "      } };\n  }) });\n})();")
    return ("<!doctype html>\n<html lang=\"pt-BR\">\n<head>\n<meta charset=\"utf-8\">\n"
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f"<title>{html.escape(title)} · 3D interativo · SOTA What</title>\n"
            f"<style>{css}</style>\n</head>\n<body>\n" + "\n".join(_script(s) for s in scripts) + "\n"
            + _script(boot) + "\n</body>\n</html>\n")


def build(hf, ffmpeg, work, plan, board, nar, lesson_id, codes) -> dict | None:
    """Writes interativo.html for the lesson. -> {"path", "bytes", "scenes"}, or None (no 3D scene)."""
    work = Path(work)
    target = work / NAME
    shown = scenes_3d(board, codes)
    if not shown:
        target.unlink(missing_ok=True)
        return None
    hfm.copy_assets(hf, work / "hf", nar["wav"])
    js = bundle(hf, work, codes, shown)
    scenes = []
    for n, ((start, dur), scene, nscene, bscene) in enumerate(zip(hfm.slots(nar), plan.scenes, nar["scenes"],
                                                                 board.scenes), 1):
        if n not in shown:
            continue
        cid = f"s{n:02d}"
        scenes.append({"id": cid, "num": n, "title": scene.title, "dur": dur, "template": bscene.template,
                       "data": hfm.scene_data(n, scene, bscene, nscene, start, dur),
                       "captions": hfm.scene_captions(nscene, start),
                       "audio": scene_audio(ffmpeg, nar["wav"], start, dur, work / "3d" / f"{cid}.mp3")})
    scripts = [(hf.modules / "gsap" / "dist" / "gsap.min.js").read_text(encoding="utf-8"),
               (hfm.KIT / "kit.js").read_text(encoding="utf-8"), (hfm.KIT / "player.js").read_text(encoding="utf-8"), js]
    doc = page(plan.title, f"SOTA What · aula {lesson_id} · 3D interativo", inline_css(hf), scripts, scenes)
    target.write_text(doc, encoding="utf-8")
    return {"path": str(target), "bytes": target.stat().st_size, "scenes": shown}
