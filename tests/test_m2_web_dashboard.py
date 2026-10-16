"""Offline Playwright + pytest suite for Milestone M2: Local web dashboard (DB-01 .. DB-09).

Runs a real local FastAPI/Uvicorn server on 127.0.0.1 with `sandstorm.amapi.build_amapi_service`
mocked, and drives the UI with headless Chromium via Playwright.
"""

from __future__ import annotations

from collections.abc import Generator
import json
import pathlib
import shutil
import socket
import threading
import time
from typing import Any
from unittest.mock import MagicMock

from click.testing import CliRunner
from playwright.sync_api import Browser, Page, sync_playwright
import pytest
import uvicorn

from sandstorm import __version__, amapi, config
from sandstorm.cli import main
from sandstorm.web.app import LOOPBACK_HOST, create_app, validate_loopback_host

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = REPO_ROOT / "output" / "screenshots"


def _get_free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((LOOPBACK_HOST, 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def web_test_env(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Set up isolated local config, policies copy, output dir, and mocked AMAPI service."""
    sa_key_file = tmp_path / "fake-sa-key.json"
    sa_key_file.write_text(
        json.dumps(
            {
                "type": "service_account",
                "project_id": "sandstorm-test-project",
                "private_key_id": "fake-key-id",
                "client_email": "sandstorm@sandstorm-test-project.iam.gserviceaccount.com",
            }
        ),
        encoding="utf-8",
    )

    local_cfg_file = tmp_path / "sandstorm.local.json"
    local_cfg_file.write_text(
        json.dumps(
            {
                "enterprise_name": "enterprises/LC00TEST99",
                "allowed_test_devices": ["emulator-pixel6-001"],
            }
        ),
        encoding="utf-8",
    )

    policies_dir = tmp_path / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)
    for src in (REPO_ROOT / "policies").glob("*.json"):
        shutil.copy2(src, policies_dir / src.name)

    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("SANDSTORM_SA_KEY", str(sa_key_file))
    monkeypatch.setenv("SANDSTORM_LOCAL_CONFIG", str(local_cfg_file))
    monkeypatch.setenv("SANDSTORM_POLICIES_DIR", str(policies_dir))
    monkeypatch.setenv("SANDSTORM_OUTPUT_DIR", str(output_dir))

    service = MagicMock(name="AMAPIService")
    monkeypatch.setattr(amapi, "build_amapi_service", lambda sa_key_path=None: service)

    return {
        "sa_key": sa_key_file,
        "local_config": local_cfg_file,
        "policies_dir": policies_dir,
        "output_dir": output_dir,
        "service": service,
    }


@pytest.fixture(scope="module")
def playwright_browser() -> Generator[Browser, None, None]:
    """Launch a single headless Chromium instance for all M2 UI tests."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture()
def live_server_url(web_test_env: dict[str, Any]) -> Generator[str, None, None]:
    """Start the FastAPI app on 127.0.0.1:<free_port> in a background thread."""
    port = _get_free_loopback_port()
    app = create_app()
    uv_config = uvicorn.Config(
        app,
        host=LOOPBACK_HOST,
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(uv_config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10.0
    while not server.started and time.time() < deadline:
        time.sleep(0.05)

    yield f"http://{LOOPBACK_HOST}:{port}"

    server.should_exit = True
    thread.join(timeout=5.0)


@pytest.fixture()
def page(playwright_browser: Browser) -> Generator[Page, None, None]:
    """Provide a Playwright page that blocks any non-loopback network request."""
    context = playwright_browser.new_context(viewport={"width": 1280, "height": 800})

    def _only_loopback(route: Any, request: Any) -> None:
        if not request.url.startswith(f"http://{LOOPBACK_HOST}:"):
            route.abort()
            raise AssertionError(
                f"External request blocked in offline dashboard test: {request.url}"
            )
        route.continue_()

    context.route("**/*", _only_loopback)
    new_page = context.new_page()
    yield new_page
    context.close()


# ---------------------------------------------------------------------------
# DB-01 & DB-02: Loopback binding and shared core architecture
# ---------------------------------------------------------------------------


def test_db01_web_binds_to_127_0_0_1_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """DB-01: `sandstorm web` refuses 0.0.0.0 and binds strictly to 127.0.0.1."""
    assert validate_loopback_host("127.0.0.1") == "127.0.0.1"

    with pytest.raises(config.ConfigError, match="127.0.0.1"):
        validate_loopback_host("0.0.0.0")

    runner = CliRunner()
    bad_res = runner.invoke(main, ["web", "--host", "0.0.0.0"])
    assert bad_res.exit_code != 0
    assert "127.0.0.1" in bad_res.output

    recorded: dict[str, Any] = {}

    def _fake_uvicorn_run(app: Any, host: str, port: int, log_level: str) -> None:
        recorded["host"] = host
        recorded["port"] = port

    monkeypatch.setattr("sandstorm.cli.uvicorn.run", _fake_uvicorn_run)
    ok_res = runner.invoke(main, ["web", "--port", "8123"])
    assert ok_res.exit_code == 0, ok_res.output
    assert "http://127.0.0.1:8123" in ok_res.output
    assert recorded["host"] == "127.0.0.1"
    assert recorded["port"] == 8123


def test_db02_web_routes_use_shared_core_layer() -> None:
    """DB-02: Web dashboard imports and calls `sandstorm.amapi` / `sandstorm.config` directly."""
    import sandstorm.web.app as web_app_mod

    source = pathlib.Path(web_app_mod.__file__).read_text(encoding="utf-8")
    assert "googleapiclient" not in source
    assert "service_account" not in source
    assert "amapi.list_devices" in source
    assert "amapi.switch_device_policy" in source
    assert "amapi.wipe_device" in source
    assert "amapi.create_enrollment_qr" in source
    assert "amapi.save_policy_from_toggles" in source


# ---------------------------------------------------------------------------
# DB-03 & DB-08: Devices page (populated, empty state, and dynamic API data)
# ---------------------------------------------------------------------------


def test_db03_and_db08_devices_page_renders_mocked_data_and_empty_state(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    """DB-03 & DB-08: Devices page renders zero-device empty state and changing API data."""
    service = web_test_env["service"]

    # 1. Empty state (zero devices)
    service.enterprises().devices().list().execute.return_value = {"devices": []}
    page.goto(f"{live_server_url}/devices")
    empty_box = page.locator("#devices-empty-state")
    assert empty_box.is_visible()
    assert "No enrolled devices" in empty_box.inner_text()
    assert "Enroll" in empty_box.inner_text()

    # 2. Populate mocked API data and click Refresh
    service.enterprises().devices().list().execute.return_value = {
        "devices": [
            {
                "name": "enterprises/LC00TEST99/devices/emulator-pixel6-001",
                "hardwareInfo": {"model": "Pixel 6"},
                "softwareInfo": {"androidVersion": "14"},
                "appliedPolicyName": "enterprises/LC00TEST99/policies/baseline",
                "lastStatusReportTime": "2026-10-15T09:00:00Z",
                "policyCompliant": True,
                "appliedState": "ACTIVE",
            },
            {
                "name": "enterprises/LC00TEST99/devices/unlisted-phone-777",
                "hardwareInfo": {"model": "Moto G"},
                "softwareInfo": {"androidVersion": "13"},
                "appliedPolicyName": "enterprises/LC00TEST99/policies/relaxed",
                "lastStatusReportTime": "2026-10-15T09:01:00Z",
                "policyCompliant": False,
                "nonComplianceDetails": [{"settingName": "passwordRequirements"}],
            },
        ]
    }
    page.click("#refresh-devices-btn")
    table_text = page.locator("#devices-table").inner_text()
    assert "emulator-pixel6-001" in table_text
    assert "Pixel 6" in table_text
    assert "14" in table_text
    assert "2026-10-15T09:00:00Z" in table_text
    assert "COMPLIANT" in table_text
    assert "unlisted-phone-777" in table_text
    assert "NON_COMPLIANT (passwordRequirements)" in table_text

    # 3. DB-08: Verify status updates when API data changes and no banned buzzwords exist
    service.enterprises().devices().list().execute.return_value = {
        "devices": [
            {
                "name": "enterprises/LC00TEST99/devices/emulator-pixel6-001",
                "hardwareInfo": {"model": "Pixel 6"},
                "softwareInfo": {"androidVersion": "14"},
                "appliedPolicyName": "enterprises/LC00TEST99/policies/relaxed",
                "lastStatusReportTime": "2026-10-15T09:05:00Z",
                "policyCompliant": False,
                "nonComplianceDetails": [{"settingName": "alwaysOnVpnPackage"}],
            }
        ]
    }
    page.click("#refresh-devices-btn")
    updated_text = page.locator("#devices-table").inner_text()
    assert "2026-10-15T09:05:00Z" in updated_text
    assert "NON_COMPLIANT (alwaysOnVpnPackage)" in updated_text

    full_body = page.locator("body").inner_text().lower()
    for banned in ("military-grade", "unhackable", "zero telemetry", "100% verified"):
        assert banned not in full_body


# ---------------------------------------------------------------------------
# DB-04: Policies page toggle view & edit saves updated JSON
# ---------------------------------------------------------------------------


def test_db04_policies_page_toggle_change_updates_saved_json(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    """DB-04: Changing a policy toggle in the UI updates the saved JSON file on disk."""
    policies_dir: pathlib.Path = web_test_env["policies_dir"]
    baseline_path = policies_dir / "baseline.json"

    before_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert before_data["screenCaptureDisabled"] is True

    page.goto(f"{live_server_url}/policies?policy=baseline")
    assert page.locator("#policy-list").is_visible()
    assert page.locator("#screen_capture_disabled").is_checked()

    # Uncheck screenCaptureDisabled and save
    page.uncheck("#screen_capture_disabled")
    page.click("#save-policy-btn")

    page.wait_for_url("**/policies?policy=baseline*")
    assert not page.locator("#screen_capture_disabled").is_checked()

    after_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert after_data["screenCaptureDisabled"] is False


# ---------------------------------------------------------------------------
# DB-05: Enroll page generates QR image and shows token expiry time
# ---------------------------------------------------------------------------


def test_db05_enroll_page_displays_qr_and_expiry(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    """DB-05: Selecting mode + policy shows the QR code PNG and expiration timestamp."""
    service = web_test_env["service"]
    service.enterprises().enrollmentTokens().create().execute.return_value = {
        "name": "enterprises/LC00TEST99/enrollmentTokens/tok99",
        "value": "ENROLL_TOKEN_VALUE_99",
        "qrCode": '{"android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE":{}}',
        "expirationTimestamp": "2026-10-15T10:30:00Z",
    }

    page.goto(f"{live_server_url}/enroll")
    page.select_option("#mode", "fully-managed")
    page.select_option("#policy_name", "baseline")
    page.click("#generate-qr-btn")

    qr_img = page.locator("#enrollment-qr-img")
    qr_img.wait_for(state="visible")
    assert qr_img.is_visible()
    natural_width = qr_img.evaluate("el => el.naturalWidth")
    assert int(natural_width) > 50

    expiry_text = page.locator("#enrollment-expiry").inner_text()
    assert "2026-10-15T10:30:00Z" in expiry_text


# ---------------------------------------------------------------------------
# DB-06: Switch policy from the device row
# ---------------------------------------------------------------------------


def test_db06_switch_policy_from_device_row(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    """DB-06: Switching policy from a device row calls AMAPI with the right device + policy."""
    service = web_test_env["service"]
    service.enterprises().devices().list().execute.return_value = {
        "devices": [
            {
                "name": "enterprises/LC00TEST99/devices/emulator-pixel6-001",
                "hardwareInfo": {"model": "Pixel 6"},
                "softwareInfo": {"androidVersion": "14"},
                "appliedPolicyName": "enterprises/LC00TEST99/policies/baseline",
                "lastStatusReportTime": "2026-10-15T09:00:00Z",
                "policyCompliant": True,
            }
        ]
    }
    patch_mock = service.enterprises().devices().patch
    patch_mock.return_value.execute.return_value = {
        "name": "enterprises/LC00TEST99/devices/emulator-pixel6-001",
        "policyName": "enterprises/LC00TEST99/policies/relaxed",
    }

    page.goto(f"{live_server_url}/devices")
    row = page.locator('tr[data-device-id="emulator-pixel6-001"]')
    row.locator('select[name="policy_name"]').select_option("relaxed")
    row.locator('button[type="submit"]').click()

    patch_mock.assert_called_with(
        name="enterprises/LC00TEST99/devices/emulator-pixel6-001",
        updateMask="policyName",
        body={
            "policyName": "enterprises/LC00TEST99/policies/relaxed",
            "state": "ACTIVE",
        },
    )
    assert "Switched device 'emulator-pixel6-001' to policy 'relaxed'" in page.locator(
        ".banner-notice"
    ).inner_text()


# ---------------------------------------------------------------------------
# DB-07: Wipe button visibility and typed-confirmation dialog
# ---------------------------------------------------------------------------


def test_db07_wipe_button_allowlist_and_typed_confirmation(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    """DB-07: Wipe button hidden for non-listed devices; wrong confirmation sends no request."""
    service = web_test_env["service"]
    service.enterprises().devices().list().execute.return_value = {
        "devices": [
            {
                "name": "enterprises/LC00TEST99/devices/emulator-pixel6-001",
                "hardwareInfo": {"model": "Pixel 6"},
                "softwareInfo": {"androidVersion": "14"},
                "appliedPolicyName": "enterprises/LC00TEST99/policies/baseline",
                "lastStatusReportTime": "2026-10-15T09:00:00Z",
                "policyCompliant": True,
            },
            {
                "name": "enterprises/LC00TEST99/devices/non-listed-device-222",
                "hardwareInfo": {"model": "Other Phone"},
                "softwareInfo": {"androidVersion": "14"},
                "appliedPolicyName": "enterprises/LC00TEST99/policies/baseline",
                "lastStatusReportTime": "2026-10-15T09:00:00Z",
                "policyCompliant": True,
            },
        ]
    }
    delete_mock = service.enterprises().devices().delete
    delete_mock.return_value.execute.return_value = {}

    page.goto(f"{live_server_url}/devices")

    # Non-listed device has NO wipe button
    unlisted_row = page.locator('tr[data-device-id="non-listed-device-222"]')
    assert unlisted_row.locator(".open-wipe-modal-btn").count() == 0
    assert "Not in wipe allow-list" in unlisted_row.inner_text()

    # Allow-listed device has a Wipe button
    allowed_row = page.locator('tr[data-device-id="emulator-pixel6-001"]')
    wipe_btn = allowed_row.locator(".open-wipe-modal-btn")
    assert wipe_btn.count() == 1

    wipe_requests: list[str] = []
    page.on(
        "request",
        lambda req: wipe_requests.append(req.url) if "/wipe" in req.url else None,
    )

    # Open modal and enter wrong confirmation -> no network request sent
    wipe_btn.click()
    assert page.locator("#wipe-modal-backdrop").is_visible()
    page.fill("#wipe-confirmation-input", "wrong-device-id")
    page.click("#wipe-submit-btn")

    assert page.locator("#wipe-mismatch-error").is_visible()
    assert wipe_requests == []
    delete_mock.assert_not_called()

    # Now type exact device ID -> request sent and AMAPI delete called
    page.fill("#wipe-confirmation-input", "emulator-pixel6-001")
    page.click("#wipe-submit-btn")

    assert len(wipe_requests) == 1
    delete_mock.assert_called_once_with(
        name="enterprises/LC00TEST99/devices/emulator-pixel6-001"
    )
    assert "Wipe command sent for device 'emulator-pixel6-001'" in page.locator(
        ".banner-notice"
    ).inner_text()


# ---------------------------------------------------------------------------
# DB-09: Palette, 375px responsive check (no sideways scroll), footer version, screenshots
# ---------------------------------------------------------------------------


def test_db09_palette_responsive_375px_and_screenshots(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    """DB-09: Owner's palette, works at 375px with no sideways scroll, version in footer."""
    service = web_test_env["service"]
    service.enterprises().devices().list().execute.return_value = {
        "devices": [
            {
                "name": "enterprises/LC00TEST99/devices/emulator-pixel6-001",
                "hardwareInfo": {"model": "Pixel 6"},
                "softwareInfo": {"androidVersion": "14"},
                "appliedPolicyName": "enterprises/LC00TEST99/policies/baseline",
                "lastStatusReportTime": "2026-10-15T09:00:00Z",
                "policyCompliant": True,
            }
        ]
    }

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # 1280 px desktop check + screenshot
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(f"{live_server_url}/devices")

    footer_text = page.locator(".site-footer").inner_text()
    assert f"v{__version__}" in footer_text

    bg_image = page.evaluate("() => getComputedStyle(document.body).backgroundImage")
    assert "rgb(15, 118, 110)" in bg_image  # #0f766e

    desktop_shot = SCREENSHOT_DIR / "dashboard-1280px.png"
    page.screenshot(path=str(desktop_shot), full_page=True)
    assert desktop_shot.is_file()

    # Capture Wipe modal screenshot on /devices
    page.locator(".open-wipe-modal-btn").first.click()
    page.locator("#wipe-modal-backdrop").wait_for(state="visible")
    wipe_modal_shot = SCREENSHOT_DIR / "m2-wipe-modal-1280px.png"
    page.screenshot(path=str(wipe_modal_shot), full_page=False)
    assert wipe_modal_shot.is_file()
    page.click("#wipe-cancel-btn")

    # Capture /policies screenshot at 1280px
    page.goto(f"{live_server_url}/policies?policy=baseline")
    policies_shot = SCREENSHOT_DIR / "m2-policies-1280px.png"
    page.screenshot(path=str(policies_shot), full_page=True)
    assert policies_shot.is_file()

    # Capture /enroll screenshot with generated QR code at 1280px
    service.enterprises().enrollmentTokens().create().execute.return_value = {
        "name": "enterprises/LC00TEST99/enrollmentTokens/tok99",
        "value": "ENROLL_TOKEN_VALUE_99",
        "qrCode": '{"android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE":{}}',
        "expirationTimestamp": "2026-10-15T10:30:00Z",
    }
    page.goto(f"{live_server_url}/enroll")
    page.click("#generate-qr-btn")
    page.locator("#enrollment-qr-img").wait_for(state="visible")
    enroll_shot = SCREENSHOT_DIR / "m2-enroll-qr-1280px.png"
    page.screenshot(path=str(enroll_shot), full_page=True)
    assert enroll_shot.is_file()

    # 375 px phone width check across all three pages + screenshot
    page.set_viewport_size({"width": 375, "height": 812})
    for route in ("/devices", "/policies", "/enroll"):
        page.goto(f"{live_server_url}{route}")
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert overflow is False, f"Horizontal scroll detected at 375px on {route}"

    page.goto(f"{live_server_url}/devices")
    mobile_shot = SCREENSHOT_DIR / "dashboard-375px.png"
    page.screenshot(path=str(mobile_shot), full_page=True)
    assert mobile_shot.is_file()
