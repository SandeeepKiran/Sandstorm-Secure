"""Render the Sandstorm Secure launch video from composition/index.html.

Usage (from any folder):
  python render.py stills 1.5 7.0 12.0 OUT_DIR   -> PNG stills at the given seconds
  python render.py video                          -> ../brag.mp4 (needs soundtrack.wav, see music.py)

Frames go straight from the headless browser into ffmpeg through a pipe,
so no raw frame files are written to disk.
Needs: Python 3.11+, playwright (python -m playwright install chromium), ffmpeg on PATH.
"""
import functools
import http.server
import subprocess
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
COMPOSITION = HERE / "composition"
OUTPUT_DIR = HERE.parent
FPS = 30


def start_server():
    # The demo pages load in iframes; a local server keeps them same-origin with the stage.
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(QuietHandler, directory=str(COMPOSITION))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def open_stage(playwright, port):
    browser = playwright.chromium.launch()
    context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1, color_scheme="light")
    page = context.new_page()
    page.goto(f"http://127.0.0.1:{port}/index.html")
    page.evaluate("window.__ready")
    return browser, page


def render_stills(times, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    server = start_server()
    with sync_playwright() as p:
        browser, page = open_stage(p, server.server_address[1])
        try:
            for t in sorted(times):
                page.evaluate(f"window.seek({t})")
                page.screenshot(path=str(out_dir / f"still_{t:06.2f}.png"))
        finally:
            browser.close()
    server.shutdown()


def render_video():
    audio = HERE / "soundtrack.wav"
    raw = HERE / "brag-raw.mp4"
    server = start_server()
    with sync_playwright() as p:
        browser, page = open_stage(p, server.server_address[1])
        duration = page.evaluate("window.DURATION")
        total = int(round(duration * FPS))
        ffmpeg = subprocess.Popen([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png", "-i", "-",
            "-i", str(audio),
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(raw),
        ], stdin=subprocess.PIPE)
        try:
            for i in range(total):
                page.evaluate(f"window.seek({i / FPS})")
                ffmpeg.stdin.write(page.screenshot(type="png"))
                if i % 60 == 0:
                    print(f"frame {i}/{total}", flush=True)
        finally:
            ffmpeg.stdin.close()
            ffmpeg.wait()
            browser.close()
    server.shutdown()
    print("wrote", raw)


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        render_stills([float(x) for x in sys.argv[2:-1]], sys.argv[-1])
    else:
        render_video()
