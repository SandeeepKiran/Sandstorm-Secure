"""Shared offline fixtures for the dashboard UI tests.

The live server runs on 127.0.0.1 with `sandstorm.amapi.build_amapi_service` mocked,
so no test ever reaches Google. Every test gets its own temporary key, local config,
policies folder and output folder.
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

from playwright.sync_api import Browser, Page, sync_playwright
import pytest
import uvicorn

from sandstorm import amapi
from sandstorm.web.app import LOOPBACK_HOST, create_app

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = REPO_ROOT / "output" / "screenshots"

FAKE_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nSANDSTORM-FAKE-SECRET-MARKER\n-----END PRIVATE KEY-----\n"


def write_fake_sa_key(path: pathlib.Path, **overrides: Any) -> pathlib.Path:
    """Write a fake service-account key. It has a fake private key, to prove it is never shown."""
    payload: dict[str, Any] = {
        "type": "service_account",
        "project_id": "sandstorm-test-project",
        "private_key_id": "fake-key-id",
        "private_key": FAKE_PRIVATE_KEY,
        "client_email": "sandstorm@sandstorm-test-project.iam.gserviceaccount.com",
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _get_free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((LOOPBACK_HOST, 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def web_test_env(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Set up isolated local config, policies copy, output dir, and mocked AMAPI service."""
    sa_key_file = write_fake_sa_key(tmp_path / "fake-sa-key.json")

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
        "tmp_path": tmp_path,
        "sa_key": sa_key_file,
        "local_config": local_cfg_file,
        "policies_dir": policies_dir,
        "output_dir": output_dir,
        "service": service,
    }


@pytest.fixture(scope="module")
def playwright_browser() -> Generator[Browser, None, None]:
    """Launch one headless Chromium per test module."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture()
def live_server_url(web_test_env: dict[str, Any]) -> Generator[str, None, None]:
    """Start the FastAPI app on 127.0.0.1:<free_port> in a background thread."""
    port = _get_free_loopback_port()
    server = uvicorn.Server(
        uvicorn.Config(create_app(), host=LOOPBACK_HOST, port=port, log_level="warning")
    )
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


def sample_devices() -> list[dict[str, Any]]:
    """Two AMAPI device records: one allow-listed and compliant, one not."""
    return [
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
