# capture.py — renders a three.js lesson scene frame by frame with Playwright and pipes it to FFmpeg.
# Usage: python capture.py ROOT PAGE OUT [--fps 30] [--lenient]
#   ROOT: the folder served on 127.0.0.1 (data/lessons); PAGE: path of the scene's index.html under ROOT.
# The page must expose window.__lesson = {duration, beats, renderAt(t), check(t)} and set window.__ready.
# Exit 3: JavaScript error; 4: layout problem (a label off screen, labels over each other); 5: timeout.
import argparse
import functools
import http.server
import subprocess
import sys
import threading
from urllib.parse import urlsplit

import imageio_ffmpeg
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright


class Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript",
                      ".mjs": "text/javascript", ".json": "application/json", ".wav": "audio/wav"}

    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("page")
    ap.add_argument("out")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--lenient", action="store_true", help="layout problems become warnings")
    ns = ap.parse_args()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=ns.root))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--use-angle=d3d11", "--ignore-gpu-blocklist"])
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).hostname == "127.0.0.1"
                       else route.abort())                     # the scene never reaches the internet
            page.on("pageerror", lambda exc: errors.append(f"erro de JavaScript: {exc}"))
            page.on("console", lambda msg: errors.append(f"console.error: {msg.text}") if msg.type == "error" else None)
            page.goto(f"http://127.0.0.1:{server.server_port}/{ns.page}?capture=1")
            try:
                page.wait_for_function("window.__ready === true", timeout=30000)
            except PlaywrightTimeout:
                print("a cena não inicializou em 30 s. " + " | ".join(errors[:5]), file=sys.stderr)
                return 3
            if errors:
                print(" | ".join(errors[:5]), file=sys.stderr)
                return 3
            lesson = page.evaluate("({duration: window.__lesson.duration, beats: window.__lesson.beats})")
            issues = []
            for n, beat in enumerate(lesson["beats"], 1):
                for issue in page.evaluate("t => window.__lesson.check(t)", max(beat["start"], beat["end"] - 0.05)):
                    issues.append(f"frase {n}: {issue}")
            if issues and not ns.lenient:
                print("problemas de layout:\n" + "\n".join(issues[:12]), file=sys.stderr)
                return 4
            for issue in issues:
                print(f"AVISO de layout: {issue}")
            frames = max(1, round(lesson["duration"] * ns.fps))
            ffmpeg = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "image2pipe",
                                       "-framerate", str(ns.fps), "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264",
                                       "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "veryfast", ns.out],
                                      stdin=subprocess.PIPE)
            for i in range(frames):
                page.evaluate("t => window.__lesson.renderAt(t)", i / ns.fps)
                ffmpeg.stdin.write(page.screenshot(type="jpeg", quality=90))
                if errors:
                    break
            ffmpeg.stdin.close()
            ffmpeg.wait()
            browser.close()
            if errors:
                print(" | ".join(errors[:5]), file=sys.stderr)
                return 3
            print(f"{frames} quadros")
            return 0
    finally:
        server.shutdown()


if __name__ == "__main__":
    sys.exit(main())
