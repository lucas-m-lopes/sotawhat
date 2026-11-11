# sotawhat/lessons/probe3d.py
"""The headless probe of a 3D scene written by the LLM (mechanism3d), run with the Python of the lessons tools
(Playwright and its Chromium live there; no sotawhat import, no API key in its environment).

    python probe3d.py ROOT PAGE OUTDIR --at 5.9,11.3,...

ROOT is served on 127.0.0.1 and nothing else is reachable from the page. PAGE (under ROOT) is the probe page of
the scene: the player in probe mode (motion_kit/player.js), which exposes window.__probe {ready, seek, check,
errors}. At each time it seeks the scene, collects the kit's layout check and saves a 960×540 JPEG.
Prints one JSON line: {"errors": [...], "issues": [[k, "..."]], "frames": ["…/f01.jpg", …]}."""
import argparse
import functools
import http.server
import json
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit


class Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript",
                      ".mjs": "text/javascript", ".json": "application/json", ".wav": "audio/wav",
                      ".woff2": "font/woff2"}

    def log_message(self, *args):
        pass


def main() -> int:
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("page")
    ap.add_argument("out")
    ap.add_argument("--at", required=True, help="times in seconds, comma separated")
    ns = ap.parse_args()
    times = [float(x) for x in ns.at.split(",") if x.strip()]
    out = Path(ns.out)
    out.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=ns.root))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    result = {"errors": [], "issues": [], "frames": []}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--use-angle=d3d11", "--ignore-gpu-blocklist"])
            page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=0.5)
            page.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).hostname == "127.0.0.1"
                       else route.abort())
            page.on("pageerror", lambda exc: result["errors"].append(f"erro de JavaScript: {exc}"))
            page.on("console", lambda m: result["errors"].append(f"console.error: {m.text}") if m.type == "error" else None)
            page.goto(f"http://127.0.0.1:{server.server_port}/{ns.page}")
            try:
                page.wait_for_function("window.__probe && window.__probe.ready === true", timeout=60000)
            except PlaywrightTimeout:
                result["errors"].append("a cena não montou em 60 s")
            result["errors"] += page.evaluate("window.__probe ? window.__probe.errors : []") or []
            if not result["errors"]:
                for k, t in enumerate(times, 1):
                    page.evaluate("t => window.__probe.seek(t)", t)
                    for issue in page.evaluate("t => window.__probe.check(t)", t) or []:
                        result["issues"].append([k, issue])
                    path = out / f"f{k:02d}.jpg"
                    page.screenshot(path=str(path), type="jpeg", quality=82)
                    result["frames"].append(str(path))
                result["errors"] += [e for e in page.evaluate("window.__probe.errors") or [] if e not in result["errors"]]
            browser.close()
    finally:
        server.shutdown()
    result["errors"] = list(dict.fromkeys(result["errors"]))[:8]
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
