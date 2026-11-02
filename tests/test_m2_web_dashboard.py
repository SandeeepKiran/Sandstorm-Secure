"""Offline Playwright + pytest suite for Milestone M2: Local web dashboard (DB-01 .. DB-09).

Runs a real local FastAPI/Uvicorn server on 127.0.0.1 with `sandstorm.amapi.build_amapi_service`
mocked (fixtures in conftest.py), and drives the UI with headless Chromium via Playwright.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

from click.testing import CliRunner
from playwright.sync_api import Page
import pytest

from conftest import SCREENSHOT_DIR, sample_devices
from sandstorm import __version__, config
from sandstorm.cli import main
from sandstorm.web.app import validate_loopback_host


def _open_row_menu(page: Page, device_id: str) -> Any:
    row = page.locator(f'tr[data-device-id="{device_id}"]')
    row.locator("summary").click()
    return row


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
    assert "amapi.check_connection" in source


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

    # 1. Empty state (zero devices). Zero is real data, so the cards show 0, not "—".
    service.enterprises().devices().list().execute.return_value = {"devices": []}
    page.goto(f"{live_server_url}/devices")
    empty_box = page.locator("#devices-empty-state")
    assert empty_box.is_visible()
    assert "No enrolled devices" in empty_box.inner_text()
    assert "Enroll a device" in empty_box.inner_text()
    assert page.locator("#stat-total").inner_text() == "0"

    # 2. Populate mocked API data and click Refresh
    service.enterprises().devices().list().execute.return_value = {"devices": sample_devices()}
    page.click("#refresh-devices-btn")
    table = page.locator("#devices-table")
    table_text = table.inner_text()
    assert "emulator-pixel6-001" in table_text
    assert "Pixel 6" in table_text
    assert "14" in table_text
    assert "15 Oct 2026, 09:00 UTC" in table_text
    assert table.locator('time[datetime="2026-10-15T09:00:00Z"]').count() == 1
    assert "unlisted-phone-777" in table_text

    pixel_row = page.locator('tr[data-device-id="emulator-pixel6-001"]')
    assert pixel_row.locator(".compliance-pill.pill-success").inner_text() == "Compliant"
    moto_row = page.locator('tr[data-device-id="unlisted-phone-777"]')
    assert moto_row.locator(".compliance-pill.pill-danger").inner_text() == "Not compliant"
    assert "passwordRequirements" in moto_row.inner_text()

    assert page.locator("#stat-total").inner_text() == "2"
    assert page.locator("#stat-compliant").inner_text() == "1"
    assert page.locator("#stat-non-compliant").inner_text() == "1"
    assert "UTC" in page.locator("#stat-last-refresh").inner_text()

    # 3. DB-08: status and counts follow the API when its data changes
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
    assert "15 Oct 2026, 09:05 UTC" in updated_text
    assert "Not compliant" in updated_text
    assert "alwaysOnVpnPackage" in updated_text
    assert page.locator("#stat-total").inner_text() == "1"
    assert page.locator("#stat-compliant").inner_text() == "0"
    assert page.locator("#stat-non-compliant").inner_text() == "1"

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
    assert page.locator("#screen_capture_disabled").get_attribute("role") == "switch"

    # The save bar appears only after a change
    save_bar = page.locator("#policy-save-bar")
    assert save_bar.is_hidden()
    page.uncheck("#screen_capture_disabled")
    assert save_bar.is_visible()
    page.check("#screen_capture_disabled")
    assert save_bar.is_hidden()

    page.uncheck("#screen_capture_disabled")
    page.click("#save-policy-btn")

    page.wait_for_url("**/policies?policy=baseline*")
    assert not page.locator("#screen_capture_disabled").is_checked()
    assert "Saved policy JSON" in page.locator(".toast-success").inner_text()

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
    assert page.locator("#enroll-stepper .step.is-current").count() == 1
    page.click('label[for="mode-fully-managed"]')
    page.select_option("#policy_name", "baseline")
    page.click("#generate-qr-btn")

    qr_img = page.locator("#enrollment-qr-img")
    qr_img.wait_for(state="visible")
    assert int(qr_img.evaluate("el => el.naturalWidth")) > 50

    expiry = page.locator("#enrollment-expiry")
    assert "15 Oct 2026, 10:30 UTC" in expiry.inner_text()
    assert expiry.locator("time").get_attribute("datetime") == "2026-10-15T10:30:00Z"

    # Step 3 is now current, and the page shows a file name but no local folder path
    assert "Scan on the emulator" in page.locator("#enroll-stepper .step.is-current").inner_text()
    assert page.locator("#download-qr-btn").get_attribute("download") == "enroll-fully-managed-baseline.png"
    assert str(web_test_env["output_dir"]) not in page.content()


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
    service.enterprises().devices().list().execute.return_value = {"devices": sample_devices()[:1]}
    patch_mock = service.enterprises().devices().patch
    patch_mock.return_value.execute.return_value = {
        "name": "enterprises/LC00TEST99/devices/emulator-pixel6-001",
        "policyName": "enterprises/LC00TEST99/policies/relaxed",
    }

    page.goto(f"{live_server_url}/devices")
    row = _open_row_menu(page, "emulator-pixel6-001")
    row.locator('select[name="policy_name"]').select_option("relaxed")
    row.locator('.inline-switch-form button[type="submit"]').click()

    patch_mock.assert_called_with(
        name="enterprises/LC00TEST99/devices/emulator-pixel6-001",
        updateMask="policyName",
        body={
            "policyName": "enterprises/LC00TEST99/policies/relaxed",
            "state": "ACTIVE",
        },
    )
    assert "Switched device 'emulator-pixel6-001' to policy 'relaxed'" in page.locator(
        ".toast-success"
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
    service.enterprises().devices().list().execute.return_value = {"devices": sample_devices()}
    delete_mock = service.enterprises().devices().delete
    delete_mock.return_value.execute.return_value = {}

    page.goto(f"{live_server_url}/devices")

    # Non-listed device has NO wipe button in its Danger zone
    unlisted_row = _open_row_menu(page, "unlisted-phone-777")
    danger_zone = unlisted_row.locator(".danger-zone")
    assert danger_zone.is_visible()
    assert unlisted_row.locator(".open-wipe-modal-btn").count() == 0
    assert "Not in wipe allow-list" in danger_zone.inner_text()
    page.keyboard.press("Escape")

    # Allow-listed device has a Wipe button in its Danger zone
    allowed_row = _open_row_menu(page, "emulator-pixel6-001")
    wipe_btn = allowed_row.locator(".danger-zone .open-wipe-modal-btn")
    assert wipe_btn.count() == 1

    wipe_requests: list[str] = []
    page.on(
        "request",
        lambda req: wipe_requests.append(req.url) if "/wipe" in req.url else None,
    )

    # Open modal and enter wrong confirmation -> no network request sent
    wipe_btn.click()
    assert page.locator("#wipe-modal-backdrop").is_visible()
    assert page.locator("#wipe-confirmation-input").evaluate("el => el === document.activeElement")
    page.fill("#wipe-confirmation-input", "wrong-device-id")
    page.click("#wipe-submit-btn")

    assert page.locator("#wipe-mismatch-error").is_visible()
    assert wipe_requests == []
    delete_mock.assert_not_called()

    # Escape closes the dialog without sending anything
    page.keyboard.press("Escape")
    assert page.locator("#wipe-modal-backdrop").is_hidden()
    assert wipe_requests == []

    # Now type exact device ID -> request sent and AMAPI delete called
    _open_row_menu(page, "emulator-pixel6-001")
    wipe_btn.click()
    page.fill("#wipe-confirmation-input", "emulator-pixel6-001")
    page.click("#wipe-submit-btn")

    assert len(wipe_requests) == 1
    delete_mock.assert_called_once_with(
        name="enterprises/LC00TEST99/devices/emulator-pixel6-001"
    )
    assert "Wipe command sent for device 'emulator-pixel6-001'" in page.locator(
        ".toast-success"
    ).inner_text()


# ---------------------------------------------------------------------------
# DB-09: Palette, 375px responsive check (no sideways scroll), footer version, screenshots
# ---------------------------------------------------------------------------


def test_db09_palette_responsive_375px_and_screenshots(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    """DB-09: Project palette (no teal gradient), works at 375px, version in the sidebar footer."""
    service = web_test_env["service"]
    service.enterprises().devices().list().execute.return_value = {"devices": sample_devices()}

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(f"{live_server_url}/devices")

    assert f"v{__version__}" in page.locator(".sidebar-footer").inner_text()

    # v5.1.0 palette: light grey-white page, dark navy sidebar, blue primary, no gradients
    body_style = page.evaluate(
        "() => { const s = getComputedStyle(document.body); return [s.backgroundColor, s.backgroundImage]; }"
    )
    assert body_style == ["rgb(248, 250, 252)", "none"]  # #f8fafc
    sidebar_bg = page.evaluate("() => getComputedStyle(document.querySelector('.sidebar')).backgroundColor")
    assert sidebar_bg == "rgb(11, 18, 32)"  # #0b1220
    primary_bg = page.evaluate("() => getComputedStyle(document.querySelector('.btn-primary')).backgroundColor")
    assert primary_bg == "rgb(37, 99, 235)"  # #2563eb
    page_source = page.content().lower()
    assert "#0f766e" not in page_source and "#99f6e4" not in page_source

    page.screenshot(path=str(SCREENSHOT_DIR / "dashboard-1280px.png"), full_page=True)

    _open_row_menu(page, "emulator-pixel6-001")
    page.locator(".open-wipe-modal-btn").first.click()
    page.locator("#wipe-modal-backdrop").wait_for(state="visible")
    page.screenshot(path=str(SCREENSHOT_DIR / "m2-wipe-modal-1280px.png"), full_page=False)
    page.click("#wipe-cancel-btn")

    page.goto(f"{live_server_url}/policies?policy=baseline")
    page.screenshot(path=str(SCREENSHOT_DIR / "m2-policies-1280px.png"), full_page=True)

    service.enterprises().enrollmentTokens().create().execute.return_value = {
        "name": "enterprises/LC00TEST99/enrollmentTokens/tok99",
        "value": "ENROLL_TOKEN_VALUE_99",
        "qrCode": '{"android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE":{}}',
        "expirationTimestamp": "2026-10-15T10:30:00Z",
    }
    page.goto(f"{live_server_url}/enroll")
    page.click("#generate-qr-btn")
    page.locator("#enrollment-qr-img").wait_for(state="visible")
    page.screenshot(path=str(SCREENSHOT_DIR / "m2-enroll-qr-1280px.png"), full_page=True)

    # 375 px phone width: no sideways scroll on any page
    page.set_viewport_size({"width": 375, "height": 812})
    for route in ("/devices", "/policies", "/enroll", "/settings"):
        page.goto(f"{live_server_url}{route}")
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert overflow is False, f"Horizontal scroll detected at 375px on {route}"

    page.goto(f"{live_server_url}/devices")
    page.screenshot(path=str(SCREENSHOT_DIR / "dashboard-375px.png"), full_page=True)
