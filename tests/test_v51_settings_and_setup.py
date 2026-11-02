"""Offline tests for v5.1.0: Settings page, setup banner, disabled Google buttons, theme, 375 px.

AMAPI stays mocked (conftest.py). Key files are fake and live in pytest's temp folder,
except one path that points inside the project on purpose (it is refused before it is read).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import httplib2
from googleapiclient.errors import HttpError
from playwright.sync_api import Page
import pytest

from conftest import FAKE_PRIVATE_KEY, REPO_ROOT, sample_devices, write_fake_sa_key
from sandstorm import amapi, config

TOOLTIP_TEXT = "Set up the Google key in Settings first."


def _write_local_config(path: pathlib.Path, **data: Any) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# Core: key path validation and source order (no browser)
# ---------------------------------------------------------------------------


def test_set_sa_key_path_refuses_missing_file(web_test_env: dict[str, Any]) -> None:
    missing = web_test_env["tmp_path"] / "missing-key.json"
    with pytest.raises(config.ConfigError, match="does not exist"):
        config.set_sa_key_path(str(missing))


def test_set_sa_key_path_refuses_wrong_type(web_test_env: dict[str, Any]) -> None:
    wrong = write_fake_sa_key(web_test_env["tmp_path"] / "oauth-client.json", type="authorized_user")
    with pytest.raises(config.ConfigError, match="not a service-account key"):
        config.set_sa_key_path(str(wrong))


def test_set_sa_key_path_refuses_invalid_json(web_test_env: dict[str, Any]) -> None:
    broken = web_test_env["tmp_path"] / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(config.ConfigError, match="not valid JSON"):
        config.set_sa_key_path(str(broken))


def test_set_sa_key_path_refuses_missing_fields(web_test_env: dict[str, Any]) -> None:
    no_email = write_fake_sa_key(web_test_env["tmp_path"] / "no-email.json", client_email="")
    with pytest.raises(config.ConfigError, match="client_email"):
        config.set_sa_key_path(str(no_email))


def test_set_sa_key_path_refuses_path_inside_project(web_test_env: dict[str, Any]) -> None:
    """Hard rule 3: a key inside the repo could be committed, so the path is refused."""
    inside = REPO_ROOT / "keys" / "sandstorm-key.json"
    with pytest.raises(config.ConfigError, match="inside the project folder"):
        config.set_sa_key_path(str(inside))
    saved = json.loads(web_test_env["local_config"].read_text(encoding="utf-8"))
    assert "sa_key_path" not in saved


def test_saved_key_path_is_used_and_env_var_wins(
    web_test_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    settings_key = write_fake_sa_key(web_test_env["tmp_path"] / "settings-key.json", project_id="from-settings")
    public = config.set_sa_key_path(str(settings_key))
    assert public == {
        "project_id": "from-settings",
        "client_email": "sandstorm@sandstorm-test-project.iam.gserviceaccount.com",
    }
    saved = json.loads(web_test_env["local_config"].read_text(encoding="utf-8"))
    assert saved["sa_key_path"] == str(settings_key.resolve())
    # Saving the path keeps the other local settings.
    assert saved["enterprise_name"] == "enterprises/LC00TEST99"

    # The env var is set by the fixture, so it wins.
    assert config.get_sa_key_source()[0] == config.KEY_SOURCE_ENV
    assert config.get_sa_key_path() == web_test_env["sa_key"].resolve()

    monkeypatch.delenv("SANDSTORM_SA_KEY")
    assert config.get_sa_key_source()[0] == config.KEY_SOURCE_SETTINGS
    assert config.get_sa_key_path() == settings_key.resolve()
    assert config.read_project_id_from_sa_key() == "from-settings"


def test_setup_status_never_contains_the_private_key(web_test_env: dict[str, Any]) -> None:
    status = config.get_setup_status()
    assert status["key_ok"] and status["enterprise_ok"] and status["ready"]
    assert "SANDSTORM-FAKE-SECRET-MARKER" not in json.dumps(status)


def test_check_connection_is_read_only_and_explains_errors(web_test_env: dict[str, Any]) -> None:
    service = web_test_env["service"]
    service.enterprises().get.return_value.execute.return_value = {"name": "enterprises/LC00TEST99"}

    result = amapi.check_connection()
    assert result["ok"] is True
    service.enterprises().get.assert_called_with(name="enterprises/LC00TEST99")
    service.enterprises().devices().delete.assert_not_called()
    service.enterprises().policies().patch.assert_not_called()

    service.enterprises().get.return_value.execute.side_effect = HttpError(
        resp=httplib2.Response({"status": 403}), content=b"{}"
    )
    refused = amapi.check_connection()
    assert refused["ok"] is False
    assert "Android Management API is enabled" in refused["message"]


def test_check_connection_without_enterprise_lists_by_project(web_test_env: dict[str, Any]) -> None:
    _write_local_config(web_test_env["local_config"], allowed_test_devices=[])
    service = web_test_env["service"]
    service.enterprises().list.return_value.execute.return_value = {}

    result = amapi.check_connection()
    assert result["ok"] is True
    service.enterprises().list.assert_called_with(projectId="sandstorm-test-project", pageSize=1)


# ---------------------------------------------------------------------------
# Setup banner: red (no key), amber (key, no enterprise), none (both OK)
# ---------------------------------------------------------------------------


def test_red_banner_when_key_missing(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SANDSTORM_SA_KEY")
    service = web_test_env["service"]

    for route in ("/devices", "/policies", "/enroll"):
        page.goto(f"{live_server_url}{route}")
        banner = page.locator("#setup-banner")
        assert banner.is_visible(), route
        assert banner.get_attribute("data-state") == "no-key"
        assert "Google key not set up. Live features are off." in banner.inner_text()
        assert page.locator("#setup-banner-action").get_attribute("href") == "/settings"

    # No Google call is made and no raw config error or local path is shown.
    page.goto(f"{live_server_url}/devices")
    body = page.locator("body").inner_text()
    assert "No enterprise_name found" not in body
    assert "SANDSTORM_SA_KEY" not in body
    assert str(web_test_env["tmp_path"]) not in page.content()
    assert page.locator("#devices-setup-state").is_visible()
    assert page.locator("#stat-total").inner_text() == "—"
    service.enterprises().devices().list().execute.assert_not_called()

    page.click("#setup-banner-action")
    page.wait_for_url("**/settings")
    assert page.locator("#check-key").get_attribute("data-state") == "fail"


def test_red_banner_when_key_invalid(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    write_fake_sa_key(web_test_env["sa_key"], type="authorized_user")
    page.goto(f"{live_server_url}/devices")
    assert page.locator("#setup-banner").get_attribute("data-state") == "no-key"


def test_amber_banner_when_enterprise_missing(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    _write_local_config(web_test_env["local_config"], allowed_test_devices=["emulator-pixel6-001"])
    page.goto(f"{live_server_url}/devices")
    banner = page.locator("#setup-banner")
    assert banner.get_attribute("data-state") == "no-enterprise"
    assert "Key OK. Enterprise not registered yet." in banner.inner_text()
    assert "create-enterprise" in banner.inner_text()
    assert "No enterprise_name found" not in page.locator("body").inner_text()
    assert page.locator("#refresh-devices-btn").is_disabled()


def test_no_banner_when_key_and_enterprise_are_ok(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    web_test_env["service"].enterprises().devices().list().execute.return_value = {"devices": sample_devices()}
    for route in ("/devices", "/policies", "/enroll", "/settings"):
        page.goto(f"{live_server_url}{route}")
        assert page.locator("#setup-banner").count() == 0, route
    page.goto(f"{live_server_url}/devices")
    assert page.locator("#refresh-devices-btn").is_enabled()
    assert page.locator(".needs-setup").count() == 0


# ---------------------------------------------------------------------------
# Google buttons are disabled with an accessible tooltip while setup is incomplete
# ---------------------------------------------------------------------------


def test_google_buttons_disabled_with_tooltip(
    page: Page,
    live_server_url: str,
    monkeypatch: pytest.MonkeyPatch,
    web_test_env: dict[str, Any],
) -> None:
    monkeypatch.delenv("SANDSTORM_SA_KEY")
    checks = {
        "/devices": ["#refresh-devices-btn"],
        "/policies": ["#upload-policy-header-btn", "#save-upload-policy-btn"],
        "/enroll": ["#generate-qr-btn"],
    }
    for route, selectors in checks.items():
        page.goto(f"{live_server_url}{route}")
        for selector in selectors:
            button = page.locator(selector)
            assert button.is_disabled(), f"{selector} on {route}"
            tip_id = button.get_attribute("aria-describedby")
            tooltip = page.locator(f"#{tip_id}")
            assert tooltip.get_attribute("role") == "tooltip"
            assert tooltip.text_content().strip() == TOOLTIP_TEXT

    # The wrapper takes keyboard focus and shows the tooltip.
    page.goto(f"{live_server_url}/devices")
    wrapper = page.locator(".needs-setup").first
    tooltip = page.locator("#refresh-devices-btn-tip")
    assert tooltip.evaluate("el => getComputedStyle(el).visibility") == "hidden"
    wrapper.focus()
    page.wait_for_function("() => getComputedStyle(document.querySelector('#refresh-devices-btn-tip')).opacity === '1'")
    assert tooltip.is_visible()


# ---------------------------------------------------------------------------
# Settings page: save the key path (validation in the UI) and test the connection
# ---------------------------------------------------------------------------


def test_settings_page_validates_and_saves_key_path(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SANDSTORM_SA_KEY")
    tmp_path: pathlib.Path = web_test_env["tmp_path"]
    page.goto(f"{live_server_url}/settings")
    assert "No key is set" in page.locator("#key-source").inner_text()
    assert page.locator("#test-connection-btn").is_disabled()

    cases = [
        (str(tmp_path / "missing.json"), "does not exist"),
        (str(write_fake_sa_key(tmp_path / "wrong-type.json", type="authorized_user")), "not a service-account key"),
        (str(REPO_ROOT / "sandstorm-key.json"), "inside the project folder"),
    ]
    for raw_path, expected in cases:
        page.fill("#sa_key_path", raw_path)
        page.click("#save-key-btn")
        error = page.locator("#key-path-error")
        assert expected in error.inner_text(), raw_path
        assert page.locator("#sa_key_path").get_attribute("aria-invalid") == "true"
        assert page.locator("#sa_key_path").input_value() == raw_path
    saved = json.loads(web_test_env["local_config"].read_text(encoding="utf-8"))
    assert "sa_key_path" not in saved

    good_key = write_fake_sa_key(tmp_path / "good-key.json")
    page.fill("#sa_key_path", str(good_key))
    page.click("#save-key-btn")
    page.wait_for_url("**/settings?notice=*")
    assert "Key path saved" in page.locator(".toast-success").inner_text()
    assert page.locator("#setup-banner").count() == 0
    assert page.locator("#key-status-pill").inner_text() == "Key valid"
    assert "path saved on this page" in page.locator("#key-source").inner_text()
    assert page.locator("#key-project-id").inner_text() == "sandstorm-test-project"
    assert page.locator("#check-key").get_attribute("data-state") == "ok"
    assert page.locator("#check-enterprise").get_attribute("data-state") == "ok"
    assert page.locator("#check-test-device").get_attribute("data-state") == "ok"
    assert page.locator("#check-blocked-device").get_attribute("data-state") == "optional"

    # Never show the private key.
    assert "SANDSTORM-FAKE-SECRET-MARKER" not in page.content()
    assert FAKE_PRIVATE_KEY.splitlines()[0] not in page.content()

    saved = json.loads(web_test_env["local_config"].read_text(encoding="utf-8"))
    assert saved["sa_key_path"] == str(good_key.resolve())


def test_settings_shows_env_var_as_active_source(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    page.goto(f"{live_server_url}/settings")
    assert "environment variable SANDSTORM_SA_KEY" in page.locator("#key-source").inner_text()
    assert page.locator("#key-client-email").inner_text() == "sandstorm@sandstorm-test-project.iam.gserviceaccount.com"


def test_settings_test_connection_shows_result(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    service = web_test_env["service"]
    service.enterprises().get.return_value.execute.return_value = {"name": "enterprises/LC00TEST99"}
    page.goto(f"{live_server_url}/settings")
    page.click("#test-connection-btn")
    result = page.locator("#connection-result")
    assert result.get_attribute("data-ok") == "true"
    assert "Connected" in result.inner_text()

    service.enterprises().get.return_value.execute.side_effect = HttpError(
        resp=httplib2.Response({"status": 401}), content=b"{}"
    )
    page.click("#test-connection-btn")
    assert page.locator("#connection-result").get_attribute("data-ok") == "false"
    assert "Google rejected the key" in page.locator("#connection-result").inner_text()


# ---------------------------------------------------------------------------
# Theme toggle and 375 px layout
# ---------------------------------------------------------------------------


def test_theme_toggle_switches_and_persists(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    page.goto(f"{live_server_url}/settings")
    assert page.evaluate("() => getComputedStyle(document.body).backgroundColor") == "rgb(248, 250, 252)"
    toggle = page.locator(".topbar [data-theme-toggle]")
    assert toggle.get_attribute("aria-label") == "Switch to dark theme"
    toggle.click()
    assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"
    assert page.evaluate("() => getComputedStyle(document.body).backgroundColor") == "rgb(11, 18, 32)"
    page.reload()
    assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"
    assert page.locator(".topbar [data-theme-toggle]").get_attribute("aria-label") == "Switch to light theme"


def test_375px_layout_uses_top_bar_menu_and_card_rows(
    page: Page,
    live_server_url: str,
    web_test_env: dict[str, Any],
) -> None:
    web_test_env["service"].enterprises().devices().list().execute.return_value = {"devices": sample_devices()}
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(f"{live_server_url}/devices")

    toggle = page.locator("[data-nav-toggle]")
    sidebar = page.locator("#app-sidebar")
    assert toggle.is_visible()
    assert sidebar.is_hidden()
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    page.locator("#app-sidebar.is-open").wait_for(state="visible")
    assert sidebar.locator('a[href="/settings"]').is_visible()
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "false"

    # The table header is hidden and each device is a card with labels.
    assert page.locator("#devices-table thead").is_hidden()
    assert page.locator('tr[data-device-id="emulator-pixel6-001"]').is_visible()

    for route in ("/devices", "/policies", "/enroll", "/settings"):
        page.goto(f"{live_server_url}{route}")
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        assert overflow is False, f"Horizontal scroll at 375px on {route}"
