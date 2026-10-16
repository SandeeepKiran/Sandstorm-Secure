"""Offline Playwright + pytest suite for Milestones M5 (`landing/`) and M6 (`demo/`).

Verifies:
- M5 (LP-01 .. LP-07): Mock landing page content, honest wording (Hard rule 7),
  sign-up form fields, zero network requests on submit, exact confirmation message,
  375px responsive check, portfolio demo notice, and zero external scripts/fonts/CDNs.
- M6 (DM-01 .. DM-04): Static demo dashboard pages using sample data from
  `demo/sample-data.json`, clear "Demo data" banner on every page, zero real keys/IDs/paths,
  and visibly disabled wipe buttons.
"""

from __future__ import annotations

from collections.abc import Generator
import json
import pathlib
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LANDING_HTML = REPO_ROOT / "landing" / "index.html"
DEMO_DIR = REPO_ROOT / "demo"
SCREENSHOT_DIR = REPO_ROOT / "output" / "screenshots"

BANNED_BUZZWORDS = (
    "military-grade",
    "unhackable",
    "zero telemetry",
    "100% verified",
)


@pytest.fixture(scope="module")
def playwright_browser() -> Generator[Browser, None, None]:
    """Launch a single headless Chromium instance for M5 and M6 tests."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture()
def local_only_page(playwright_browser: Browser) -> Generator[Page, None, None]:
    """Provide a Playwright page that aborts and fails on any http/https network request."""
    context = playwright_browser.new_context(viewport={"width": 1280, "height": 850})

    def _block_network(route: Any, request: Any) -> None:
        url = request.url
        if url.startswith(("file://", "data:")):
            route.continue_()
            return
        route.abort()
        raise AssertionError(f"Unexpected network request in static offline test: {url}")

    context.route("**/*", _block_network)
    page = context.new_page()
    yield page
    context.close()


# ---------------------------------------------------------------------------
# M5 — Mock landing page (LP-01 .. LP-07)
# ---------------------------------------------------------------------------


def test_lp01_lp02_lp06_lp07_landing_page_content_honesty_and_no_externals(
    local_only_page: Page,
) -> None:
    """LP-01, LP-02, LP-06, LP-07: Headline, audience, 3-5 bullets, visibility, honest wording, no CDNs."""
    assert LANDING_HTML.is_file(), "landing/index.html must exist"
    raw_html = LANDING_HTML.read_text(encoding="utf-8")

    # LP-07: No external scripts, fonts or CDNs in source
    lower_html = raw_html.lower()
    assert "http://" not in lower_html
    assert "https://" not in lower_html
    assert "fonts.googleapis.com" not in lower_html
    assert "cdn." not in lower_html

    local_only_page.goto(LANDING_HTML.as_uri())

    # LP-06: Visible note says this is a portfolio demo and no data is collected
    demo_note = local_only_page.locator("#portfolio-demo-note")
    assert demo_note.is_visible()
    assert "portfolio demo" in demo_note.inner_text().lower()
    assert "no data is collected" in demo_note.inner_text().lower()

    # LP-01: Headline, who it is for, 3-5 bullets, what MDM can and cannot see
    assert local_only_page.locator("#hero-headline").is_visible()
    assert local_only_page.locator("#who-it-is-for").is_visible()

    bullets = local_only_page.locator("#capabilities-list li")
    assert 3 <= bullets.count() <= 5

    can_see = local_only_page.locator("#what-mdm-can-see").inner_text().lower()
    cannot_see = local_only_page.locator("#what-mdm-cannot-see").inner_text().lower()
    assert "model" in can_see
    assert "application" in can_see
    assert "sms" in cannot_see
    assert "photos" in cannot_see

    # LP-02 / Hard rule 7: Honest wording only
    body_text = local_only_page.locator("body").inner_text().lower()
    for banned in BANNED_BUZZWORDS:
        assert banned not in body_text


def test_lp03_lp04_signup_form_fields_and_submit_sends_nothing(
    local_only_page: Page,
) -> None:
    """LP-03 & LP-04: Form has all 5 required fields and shows demo message on submit without sending anything."""
    local_only_page.goto(LANDING_HTML.as_uri())

    # LP-03 fields: name, email, company type, phone count, biggest worry
    local_only_page.fill('input[name="name"]', "Jordan Taylor")
    local_only_page.fill('input[name="email"]', "jordan@example.com")
    local_only_page.select_option('select[name="company_type"]', "clinic-healthcare")
    local_only_page.fill('input[name="phone_count"]', "18")
    local_only_page.fill(
        'textarea[name="biggest_worry"]',
        "Lost phones with clinic schedules and unapproved USB file copies.",
    )

    confirmation = local_only_page.locator("#signup-confirmation")
    assert confirmation.is_hidden()

    requests_seen: list[str] = []
    local_only_page.on("request", lambda req: requests_seen.append(req.url))

    local_only_page.click("#signup-submit-btn")

    # LP-04: No network request made on submit, exact message shown
    assert requests_seen == []
    assert confirmation.is_visible()
    assert (
        confirmation.inner_text().strip()
        == "Thanks — this is a demo, nothing was sent or stored."
    )


def test_lp05_landing_page_responsive_375px_and_screenshots(
    local_only_page: Page,
) -> None:
    """LP-05: Landing page works at 375px width with no sideways scroll."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    local_only_page.set_viewport_size({"width": 1280, "height": 850})
    local_only_page.goto(LANDING_HTML.as_uri())
    local_only_page.screenshot(
        path=str(SCREENSHOT_DIR / "m5-landing-1280px.png"), full_page=True
    )

    local_only_page.set_viewport_size({"width": 375, "height": 812})
    local_only_page.goto(LANDING_HTML.as_uri())
    overflow = local_only_page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert overflow is False, "Horizontal scroll detected at 375px on landing/index.html"
    local_only_page.screenshot(
        path=str(SCREENSHOT_DIR / "m5-landing-375px.png"), full_page=True
    )


# ---------------------------------------------------------------------------
# M6 — Demo mode (`demo/`, DM-01 .. DM-04)
# ---------------------------------------------------------------------------


def test_dm01_dm02_dm04_demo_pages_open_from_filesystem_show_banner_and_disable_wipe(
    local_only_page: Page,
) -> None:
    """DM-01, DM-02, DM-04: Demo pages open from file://, show 'Demo data' banner, and disable Wipe."""
    sample_json_path = DEMO_DIR / "sample-data.json"
    assert sample_json_path.is_file()
    sample_data = json.loads(sample_json_path.read_text(encoding="utf-8"))
    assert len(sample_data["devices"]) >= 2
    assert "baseline" in sample_data["policies"]
    assert "relaxed" in sample_data["policies"]

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    for page_name in ("index.html", "devices.html", "policies.html", "enroll.html"):
        html_path = DEMO_DIR / page_name
        assert html_path.is_file(), f"Missing demo/{page_name}"

        local_only_page.set_viewport_size({"width": 1280, "height": 850})
        local_only_page.goto(html_path.as_uri())

        # DM-02: Every demo page shows a clear "Demo data" banner
        banner = local_only_page.locator("#demo-data-banner")
        assert banner.is_visible(), f"Demo data banner not visible on {page_name}"
        assert "demo data" in banner.inner_text().lower()

        # Check 375px responsiveness on every demo page
        local_only_page.set_viewport_size({"width": 375, "height": 812})
        overflow = local_only_page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert overflow is False, f"Horizontal scroll at 375px on demo/{page_name}"

    # DM-04: Dangerous buttons (wipe) are visibly disabled in demo mode
    local_only_page.set_viewport_size({"width": 1280, "height": 850})
    local_only_page.goto((DEMO_DIR / "index.html").as_uri())
    wipe_buttons = local_only_page.locator(".wipe-demo-btn")
    assert wipe_buttons.count() >= 1
    for idx in range(wipe_buttons.count()):
        btn = wipe_buttons.nth(idx)
        assert btn.is_visible()
        assert btn.is_disabled(), f"Wipe button {idx} must be disabled in demo mode"

    # Interactive policy switch works in demo mode
    row = local_only_page.locator('tr[data-device-id="sample-pixel6-01"]')
    row.locator('select[name="policy_name"]').select_option("relaxed")
    row.locator('button[type="submit"]').click()
    assert row.locator(".active-policy-tag").inner_text().strip() == "relaxed"
    assert local_only_page.locator("#demo-action-notice").is_visible()

    local_only_page.screenshot(
        path=str(SCREENSHOT_DIR / "m6-demo-devices-1280px.png"), full_page=True
    )

    # Interactive toggle in demo/policies.html updates JSON preview
    local_only_page.goto((DEMO_DIR / "policies.html").as_uri())
    assert '"screenCaptureDisabled": true' in local_only_page.locator(
        "#policy-json-preview"
    ).inner_text()
    local_only_page.uncheck("#screen_capture_disabled")
    assert '"screenCaptureDisabled": false' in local_only_page.locator(
        "#policy-json-preview"
    ).inner_text()
    local_only_page.screenshot(
        path=str(SCREENSHOT_DIR / "m6-demo-policies-1280px.png"), full_page=True
    )

    # Interactive QR preview in demo/enroll.html
    local_only_page.goto((DEMO_DIR / "enroll.html").as_uri())
    qr_img = local_only_page.locator("#enrollment-qr-img")
    assert qr_img.is_visible()
    local_only_page.select_option("#mode", "work-profile")
    local_only_page.select_option("#policy_name", "relaxed")
    local_only_page.click("#generate-qr-btn")
    assert (
        local_only_page.locator("#demo-enroll-mode").inner_text().strip()
        == "work-profile"
    )
    local_only_page.screenshot(
        path=str(SCREENSHOT_DIR / "m6-demo-enroll-1280px.png"), full_page=True
    )


def test_dm03_demo_and_landing_contain_no_real_keys_ids_or_local_paths() -> None:
    """DM-03 & Hard rule 6: Grep demo/ and landing/ for forbidden device IDs, keys, or local paths."""
    forbidden_substrings = (
        "blocked_devices",
        "c:\\users\\",
        "c:/users/",
        "private_key",
        "-----begin private key-----",
        "sandstorm.local.json",
    )

    files_to_scan = list(DEMO_DIR.glob("*")) + list((REPO_ROOT / "landing").glob("*"))
    scanned_count = 0
    for file_path in files_to_scan:
        if not file_path.is_file() or file_path.name == ".gitkeep":
            continue
        scanned_count += 1
        content_lower = file_path.read_text(encoding="utf-8").lower()
        for forbidden in forbidden_substrings:
            assert (
                forbidden not in content_lower
            ), f"Found forbidden string '{forbidden}' in {file_path}"
        for banned in BANNED_BUZZWORDS:
            assert (
                banned not in content_lower
            ), f"Found banned buzzword '{banned}' in {file_path}"

    assert scanned_count >= 5
