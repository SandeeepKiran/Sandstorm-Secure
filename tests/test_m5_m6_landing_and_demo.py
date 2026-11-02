"""Offline Playwright + pytest suite for Milestones M5 (`landing/`) and M6 (`demo/`).

Verifies:
- M5 (LP-01 .. LP-07): Mock landing page content, honest wording (Hard rule 7),
  sign-up form fields, zero network requests on submit, exact confirmation message,
  375px responsive check, portfolio demo notice, and zero external scripts/fonts/CDNs.
- M6 (DM-01 .. DM-04): Static demo dashboard pages using sample data from
  `demo/sample-data.js`, clear "Demo data" ribbon on every page, zero real keys/IDs/paths,
  and visibly disabled wipe buttons.
- v5.1.0: one shared design system (identical copies), version match, Open Graph image.
"""

from __future__ import annotations

from collections.abc import Generator
import json
import pathlib
import tomllib
from typing import Any

from PIL import Image
from playwright.sync_api import Browser, Page

import pytest

from conftest import REPO_ROOT, SCREENSHOT_DIR

LANDING_DIR = REPO_ROOT / "landing"
LANDING_HTML = LANDING_DIR / "index.html"
DEMO_DIR = REPO_ROOT / "demo"
STATIC_DIR = REPO_ROOT / "sandstorm" / "web" / "static"
DEMO_PAGES = ("index.html", "policies.html", "enroll.html", "settings.html")
SHARED_FILES = (
    "style.css",
    "ui.js",
    "vendor/inter-latin-wght-normal.woff2",
    "vendor/LICENSE-inter-OFL.txt",
    "vendor/LICENSE-lucide.txt",
)

BANNED_BUZZWORDS = (
    "military-grade",
    "unhackable",
    "zero telemetry",
    "100% verified",
)


# The public GitHub Pages address of the landing page (lower case for comparison).
PAGES_LANDING_URL = "https://sandeeepkiran.github.io/sandstorm-secure/landing/"

def load_demo_data() -> dict[str, Any]:
    """Parse the strict-JSON object inside demo/sample-data.js."""
    source = (DEMO_DIR / "sample-data.js").read_text(encoding="utf-8")
    body = source[source.index("=", source.index("SANDSTORM_DEMO_DATA")) + 1 :].strip()
    return json.loads(body.rstrip(";"))


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

    # LP-07: No external scripts, fonts or CDNs in source.
    # The og:image and og:url tags must use the full public address, because social sites
    # ignore a relative path. Remove only those two tags (our own Pages site) before the check.
    lower_html = raw_html.lower()
    for own_url_tag in (
        '<meta property="og:image" content="' + PAGES_LANDING_URL + 'assets/og-image.png">',
        '<meta property="og:url" content="' + PAGES_LANDING_URL + '">',
    ):
        assert own_url_tag in lower_html
        lower_html = lower_html.replace(own_url_tag, "")
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


def test_landing_page_sections_order_faq_and_og_image(local_only_page: Page) -> None:
    """v5.1.0 product page: sections in order, working FAQ accordion, real hero screenshot, OG tags."""
    local_only_page.goto(LANDING_HTML.as_uri())
    section_ids = ["hero-headline", "features", "how-it-works", "transparency", "faq", "demo-signup"]
    tops = [
        local_only_page.locator(f"#{sid}").evaluate("el => el.getBoundingClientRect().top + window.scrollY")
        for sid in section_ids
    ]
    assert tops == sorted(tops), "Landing sections are out of order"

    nav_text = local_only_page.locator(".mkt-nav").inner_text()
    for label in ("Features", "How it works", "Transparency", "Get early access"):
        assert label in nav_text

    first_faq = local_only_page.locator(".faq-item").first
    assert first_faq.locator(".faq-answer").is_hidden()
    first_faq.locator("summary").click()
    assert first_faq.locator(".faq-answer").is_visible()

    hero_img = local_only_page.locator(".browser-frame img")
    assert int(hero_img.evaluate("el => el.naturalWidth")) >= 1200

    og_image = local_only_page.locator('meta[property="og:image"]').get_attribute("content")
    assert og_image
    assert og_image.lower().startswith(PAGES_LANDING_URL)
    with Image.open(LANDING_DIR / og_image[len(PAGES_LANDING_URL):]) as img:
        assert img.size == (1200, 630)
    assert local_only_page.locator('meta[name="twitter:card"]').get_attribute("content") == "summary_large_image"

    # No fake customer logos or testimonials
    body = local_only_page.locator("body").inner_text().lower()
    for phrase in ("trusted by", "testimonial", "customers love"):
        assert phrase not in body


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
    """DM-01, DM-02, DM-04: Demo pages open from file://, show 'Demo data' ribbon, and disable Wipe."""
    sample_data = load_demo_data()
    assert len(sample_data["devices"]) >= 2
    assert "baseline" in sample_data["policies"]
    assert "relaxed" in sample_data["policies"]

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    for page_name in DEMO_PAGES:
        html_path = DEMO_DIR / page_name
        assert html_path.is_file(), f"Missing demo/{page_name}"

        local_only_page.set_viewport_size({"width": 1280, "height": 850})
        local_only_page.goto(html_path.as_uri())

        # DM-02: Every demo page shows a clear "Demo data" ribbon
        banner = local_only_page.locator("#demo-data-banner")
        assert banner.is_visible(), f"Demo data ribbon not visible on {page_name}"
        assert "demo data" in banner.inner_text().lower()

        # Same shell as the real dashboard
        assert local_only_page.locator(".app .sidebar .nav-link").count() == 4
        assert f"v{sample_data['version']}" in local_only_page.locator(".sidebar-footer").inner_text()

        local_only_page.set_viewport_size({"width": 375, "height": 812})
        overflow = local_only_page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert overflow is False, f"Horizontal scroll at 375px on demo/{page_name}"

    # Devices page: rows and summary cards come from the sample data
    local_only_page.set_viewport_size({"width": 1280, "height": 850})
    local_only_page.goto((DEMO_DIR / "index.html").as_uri())
    rows = local_only_page.locator("#devices-table tbody tr")
    assert rows.count() == len(sample_data["devices"])
    assert local_only_page.locator("#stat-total").inner_text() == str(len(sample_data["devices"]))

    # DM-04: Dangerous buttons (wipe) are visibly disabled in demo mode, in every row's Danger zone
    for idx in range(rows.count()):
        row = rows.nth(idx)
        row.locator("summary").click()
        wipe_btn = row.locator(".danger-zone .wipe-demo-btn")
        assert wipe_btn.is_visible()
        assert wipe_btn.is_disabled(), f"Wipe button in row {idx} must be disabled in demo mode"
        local_only_page.keyboard.press("Escape")

    # Interactive policy switch works in demo mode
    row = local_only_page.locator('tr[data-device-id="sample-pixel6-01"]')
    row.locator("summary").click()
    row.locator('select[name="policy_name"]').select_option("relaxed")
    row.locator('.inline-switch-form button[type="submit"]').click()
    assert row.locator(".active-policy-tag").inner_text().strip() == "relaxed"
    assert "Nothing was sent to Google" in local_only_page.locator(".toast-success").inner_text()

    local_only_page.screenshot(
        path=str(SCREENSHOT_DIR / "m6-demo-devices-1280px.png"), full_page=True
    )

    # Interactive toggle in demo/policies.html updates JSON preview and shows the save bar
    local_only_page.goto((DEMO_DIR / "policies.html").as_uri())
    preview = local_only_page.locator("#policy-json-preview")
    assert '"screenCaptureDisabled": true' in preview.inner_text()
    assert local_only_page.locator("#policy-save-bar").is_hidden()
    local_only_page.uncheck("#screen_capture_disabled")
    assert '"screenCaptureDisabled": false' in preview.inner_text()
    assert local_only_page.locator("#policy-save-bar").is_visible()
    assert local_only_page.locator("#save-upload-policy-btn").is_disabled()
    local_only_page.screenshot(
        path=str(SCREENSHOT_DIR / "m6-demo-policies-1280px.png"), full_page=True
    )

    # Interactive QR preview in demo/enroll.html
    local_only_page.goto((DEMO_DIR / "enroll.html").as_uri())
    assert local_only_page.locator("#enrollment-result").is_hidden()
    local_only_page.click('label[for="mode-work-profile"]')
    local_only_page.select_option("#policy_name", "relaxed")
    local_only_page.click("#generate-qr-btn")
    assert local_only_page.locator("#enrollment-qr-img").is_visible()
    assert local_only_page.locator("#demo-enroll-mode").inner_text().strip() == "work-profile"
    assert "(sample)" in local_only_page.locator("#enrollment-expiry").inner_text()
    local_only_page.screenshot(
        path=str(SCREENSHOT_DIR / "m6-demo-enroll-1280px.png"), full_page=True
    )

    # Settings shows a filled, valid-looking state that is labelled "Demo data"
    local_only_page.goto((DEMO_DIR / "settings.html").as_uri())
    assert local_only_page.locator("#settings-demo-pill").inner_text() == "Demo data"
    assert local_only_page.locator("#key-project-id").inner_text() == sample_data["settings"]["project_id"]
    assert local_only_page.locator("#setup-checklist [data-state='ok']").count() == 4


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

    files_to_scan = list(DEMO_DIR.glob("*")) + list(LANDING_DIR.glob("*"))
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


# ---------------------------------------------------------------------------
# v5.1.0 — one design system, identical copies, version in sync
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target_dir", [DEMO_DIR, LANDING_DIR], ids=["demo", "landing"])
def test_shared_assets_are_identical(target_dir: pathlib.Path) -> None:
    """The demo and landing copies must match the dashboard (run scripts/sync_shared_assets.py)."""
    for relative in SHARED_FILES:
        master = (STATIC_DIR / relative).read_bytes()
        copy = (target_dir / relative).read_bytes()
        assert copy == master, f"{target_dir.name}/{relative} differs from sandstorm/web/static/{relative}"


def test_shared_assets_have_no_external_urls_or_teal_palette() -> None:
    css = (STATIC_DIR / "style.css").read_text(encoding="utf-8").lower()
    js = (STATIC_DIR / "ui.js").read_text(encoding="utf-8").lower()
    for text in (css, js):
        assert "http://" not in text and "https://" not in text
    for teal in ("#0f766e", "#134e4a", "#99f6e4", "linear-gradient"):
        assert teal not in css


def test_demo_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert load_demo_data()["version"] == pyproject["project"]["version"]
