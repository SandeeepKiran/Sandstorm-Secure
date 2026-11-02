"""Make the product screenshots from the static demo (sample data only).

Writes:
- landing/assets/dashboard-demo.png  hero image in the landing page browser frame
- landing/assets/og-image.png        1200x630 Open Graph image
- docs/media/screenshots/*.png       README screenshots

The demo has only sample data, so no real device, key or enterprise can appear.
Run from the project folder:  python scripts/capture_screenshots.py
"""

from __future__ import annotations

import base64
import pathlib

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "demo"
LANDING_DIR = REPO_ROOT / "landing"
ASSETS_DIR = LANDING_DIR / "assets"
README_SHOTS_DIR = REPO_ROOT / "docs" / "media" / "screenshots"
INTER_FONT = REPO_ROOT / "sandstorm" / "web" / "static" / "vendor" / "inter-latin-wght-normal.woff2"


def _block_network(page: Page) -> None:
    def _route(route, request) -> None:  # type: ignore[no-untyped-def]
        if request.url.startswith(("file://", "data:")):
            route.continue_()
        else:
            route.abort()

    page.route("**/*", _route)


def _open(page: Page, path: pathlib.Path) -> None:
    page.goto(path.as_uri())
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")


def _clear_toasts(page: Page) -> None:
    page.evaluate("document.querySelectorAll('.toast').forEach((t) => t.remove())")


def _og_html(screenshot_png: bytes) -> str:
    shot = base64.b64encode(screenshot_png).decode("ascii")
    font = base64.b64encode(INTER_FONT.read_bytes()).decode("ascii")
    return f"""<!DOCTYPE html><html><head><style>
@font-face {{ font-family: Inter; font-weight: 100 900; src: url(data:font/woff2;base64,{font}) format("woff2"); }}
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1200px; height: 630px; overflow: hidden; background: #0b1220; color: #e2e8f0;
  font-family: Inter, "Segoe UI", sans-serif; position: relative; }}
.copy {{ position: absolute; left: 72px; top: 72px; width: 520px; }}
.brand {{ display: flex; align-items: center; gap: 14px; font-size: 26px; font-weight: 600; color: #fff; }}
.mark {{ width: 40px; height: 40px; border-radius: 10px; background: #c8a165; }}
.brand span {{ color: #c8a165; font-weight: 500; }}
h1 {{ margin-top: 56px; font-size: 54px; line-height: 1.08; letter-spacing: -0.035em; color: #fff; font-weight: 650; }}
h1 em {{ font-style: normal; color: #93c5fd; }}
p {{ margin-top: 24px; font-size: 22px; line-height: 1.5; color: #94a3b8; }}
.tag {{ position: absolute; left: 72px; bottom: 64px; font-size: 16px; color: #64748b; }}
.shot {{ position: absolute; left: 640px; top: 96px; width: 900px; border-radius: 12px;
  border: 1px solid #1e293b; box-shadow: 0 0 80px rgba(37, 99, 235, 0.25); }}
</style></head><body>
<div class="copy">
  <div class="brand"><div class="mark"></div><div>Sandstorm <span>Secure</span></div></div>
  <h1>Lock down company Android phones. <em>Google enforces the rules.</em></h1>
  <p>Forced VPN, no USB file copy, approved apps only and remote wipe.</p>
</div>
<div class="tag">Portfolio demo · screenshot shows sample data</div>
<img class="shot" src="data:image/png;base64,{shot}">
</body></html>"""


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    README_SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        for theme in ("light", "dark"):
            context = browser.new_context(
                viewport={"width": 1440, "height": 900}, color_scheme=theme
            )
            page = context.new_page()
            _block_network(page)

            _open(page, DEMO_DIR / "index.html")
            devices_png = page.screenshot()
            (README_SHOTS_DIR / f"devices-{theme}.png").write_bytes(devices_png)
            if theme == "light":
                (ASSETS_DIR / "dashboard-demo.png").write_bytes(devices_png)
                page.locator('tr[data-device-id="sample-motog54-03"] summary').click()
                page.screenshot(path=str(README_SHOTS_DIR / "device-actions-light.png"))

                _open(page, DEMO_DIR / "policies.html")
                page.uncheck("#screen_capture_disabled")
                page.screenshot(path=str(README_SHOTS_DIR / "policies-light.png"))

                _open(page, DEMO_DIR / "enroll.html")
                page.click("#generate-qr-btn")
                _clear_toasts(page)
                page.screenshot(path=str(README_SHOTS_DIR / "enroll-light.png"))

                _open(page, DEMO_DIR / "settings.html")
                page.screenshot(path=str(README_SHOTS_DIR / "settings-light.png"))

                _open(page, LANDING_DIR / "index.html")
                page.screenshot(path=str(README_SHOTS_DIR / "landing-light.png"))
            context.close()

        mobile = browser.new_context(viewport={"width": 375, "height": 812}, device_scale_factor=2)
        page = mobile.new_page()
        _block_network(page)
        _open(page, DEMO_DIR / "index.html")
        page.screenshot(path=str(README_SHOTS_DIR / "devices-mobile.png"))
        mobile.close()

        og = browser.new_context(viewport={"width": 1200, "height": 630})
        page = og.new_page()
        page.set_content(_og_html((ASSETS_DIR / "dashboard-demo.png").read_bytes()))
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(ASSETS_DIR / "og-image.png"))
        og.close()

        browser.close()

    for path in sorted([*ASSETS_DIR.glob("*.png"), *README_SHOTS_DIR.glob("*.png")]):
        print(path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
