"""Offline pytest suite for Milestone M1: Core + CLI (CO-01 through CO-10).

All Google Android Management API calls are mocked at `sandstorm.amapi.build_amapi_service`,
and network sockets are blocked to prove tests pass completely offline (CO-09).
"""

from __future__ import annotations

import json
import pathlib
import socket
import tomllib
from typing import Any
from unittest.mock import MagicMock

from click.testing import CliRunner
from PIL import Image
import pytest

from sandstorm import __version__, amapi, config
from sandstorm.cli import main

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantee every test runs 100% offline (CO-09)."""

    def _deny_socket(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Network access is forbidden during offline unit tests (CO-09).")

    monkeypatch.setattr(socket, "socket", _deny_socket)
    monkeypatch.setattr(socket, "create_connection", _deny_socket)


@pytest.fixture()
def fake_env(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, pathlib.Path]:
    """Provide isolated fake service-account key and local config path."""
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
    monkeypatch.setenv("SANDSTORM_SA_KEY", str(sa_key_file))
    monkeypatch.setenv("SANDSTORM_LOCAL_CONFIG", str(local_cfg_file))
    return {"sa_key": sa_key_file, "local_config": local_cfg_file}


@pytest.fixture()
def mock_amapi_service(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock `sandstorm.amapi.build_amapi_service` so no Google API calls leave the process."""
    service = MagicMock(name="AMAPIService")
    monkeypatch.setattr(amapi, "build_amapi_service", lambda sa_key_path=None: service)
    return service


# ---------------------------------------------------------------------------
# CO-01: Service-account key env var validation
# ---------------------------------------------------------------------------


def test_co01_missing_sa_key_env_var_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    """CO-01: Unset SANDSTORM_SA_KEY fails with a clear message and non-zero exit code."""
    monkeypatch.delenv("SANDSTORM_SA_KEY", raising=False)

    with pytest.raises(config.ConfigError, match="SANDSTORM_SA_KEY is not set"):
        config.get_sa_key_path()

    runner = CliRunner()
    result = runner.invoke(main, ["create-enterprise"])
    assert result.exit_code != 0
    assert "SANDSTORM_SA_KEY is not set" in result.output


def test_co01_nonexistent_sa_key_file_fails_clearly(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CO-01: Non-existent SANDSTORM_SA_KEY path fails with a clear error and exit code != 0."""
    missing_file = tmp_path / "does-not-exist.json"
    monkeypatch.setenv("SANDSTORM_SA_KEY", str(missing_file))

    with pytest.raises(config.ConfigError, match="does not exist"):
        config.get_sa_key_path()

    runner = CliRunner()
    result = runner.invoke(main, ["create-enterprise"])
    assert result.exit_code != 0
    assert "does not exist" in result.output


# ---------------------------------------------------------------------------
# CO-02: Enterprise sign-up flow and saving to sandstorm.local.json
# ---------------------------------------------------------------------------


def test_co02_create_enterprise_saves_to_local_config(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_amapi_service: MagicMock,
) -> None:
    """CO-02: `sandstorm create-enterprise` walks signup flow and writes sandstorm.local.json."""
    sa_key_file = tmp_path / "sa.json"
    sa_key_file.write_text(json.dumps({"project_id": "my-gcp-proj"}), encoding="utf-8")
    local_cfg_file = tmp_path / "sandstorm.local.json"
    monkeypatch.setenv("SANDSTORM_SA_KEY", str(sa_key_file))
    monkeypatch.setenv("SANDSTORM_LOCAL_CONFIG", str(local_cfg_file))

    mock_amapi_service.signupUrls().create().execute.return_value = {
        "name": "signupUrls/C123456789",
        "url": "https://enterprise.google.com/android/enroll?token=xyz",
    }
    mock_amapi_service.enterprises().create().execute.return_value = {
        "name": "enterprises/LC0998877",
    }

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["create-enterprise"],
        input="https://localhost/callback?enterpriseToken=ETOK_ABC123\n",
    )

    assert result.exit_code == 0, result.output
    assert "https://enterprise.google.com/android/enroll?token=xyz" in result.output
    assert "enterprises/LC0998877" in result.output
    assert local_cfg_file.is_file()

    saved = json.loads(local_cfg_file.read_text(encoding="utf-8"))
    assert saved["enterprise_name"] == "enterprises/LC0998877"

    # Also verify .gitignore ignores sandstorm.local.json
    gitignore_text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "sandstorm.local.json" in gitignore_text


# ---------------------------------------------------------------------------
# CO-03: Policy JSON files in policies/ pass shape validation
# ---------------------------------------------------------------------------


def test_co03_policies_exist_and_pass_amapi_schema_shape() -> None:
    """CO-03: policies/baseline.json and policies/relaxed.json exist and match AMAPI v1 Policy schema."""
    import googleapiclient.discovery_cache.documents as docs_pkg

    discovery_path = pathlib.Path(list(docs_pkg.__path__)[0]) / "androidmanagement.v1.json"
    discovery_doc = json.loads(discovery_path.read_text(encoding="utf-8"))
    valid_policy_keys = set(discovery_doc["schemas"]["Policy"]["properties"].keys())

    baseline_path = REPO_ROOT / "policies" / "baseline.json"
    relaxed_path = REPO_ROOT / "policies" / "relaxed.json"
    assert baseline_path.is_file()
    assert relaxed_path.is_file()

    _, baseline = amapi.load_policy_file(baseline_path)
    _, relaxed = amapi.load_policy_file(relaxed_path)

    # Every key in both policy files must be a genuine AMAPI v1 Policy field
    assert set(baseline.keys()).issubset(valid_policy_keys)
    assert set(relaxed.keys()).issubset(valid_policy_keys)

    # Verify baseline rules from docs/02-requirements.md
    assert baseline["alwaysOnVpnPackage"]["lockdownEnabled"] is True
    assert baseline["alwaysOnVpnPackage"]["packageName"]
    assert baseline["usbFileTransferDisabled"] is True
    assert baseline["playStoreMode"] == "WHITELIST"
    assert isinstance(baseline["applications"], list) and len(baseline["applications"]) >= 1
    assert baseline["screenCaptureDisabled"] is True
    assert baseline["factoryResetDisabled"] is True
    assert baseline["passwordRequirements"]["passwordMinimumLength"] >= 6

    # Verify relaxed policy relaxes those constraints
    assert relaxed["usbFileTransferDisabled"] is False
    assert relaxed["screenCaptureDisabled"] is False
    assert relaxed["factoryResetDisabled"] is False


# ---------------------------------------------------------------------------
# CO-04: apply-policy and list-policies
# ---------------------------------------------------------------------------


def test_co04_apply_and_list_policies(
    fake_env: dict[str, pathlib.Path],
    mock_amapi_service: MagicMock,
) -> None:
    """CO-04: `sandstorm apply-policy` uploads a policy and `sandstorm list-policies` lists it."""
    mock_amapi_service.enterprises().policies().patch().execute.return_value = {
        "name": "enterprises/LC00TEST99/policies/baseline",
        "version": "1",
    }
    mock_amapi_service.enterprises().policies().list().execute.return_value = {
        "policies": [
            {
                "name": "enterprises/LC00TEST99/policies/baseline",
                "version": "1",
                "playStoreMode": "WHITELIST",
                "usbFileTransferDisabled": True,
            },
            {
                "name": "enterprises/LC00TEST99/policies/relaxed",
                "version": "1",
                "playStoreMode": "BLACKLIST",
                "usbFileTransferDisabled": False,
            },
        ]
    }

    runner = CliRunner()
    baseline_file = REPO_ROOT / "policies" / "baseline.json"
    apply_res = runner.invoke(main, ["apply-policy", str(baseline_file)])
    assert apply_res.exit_code == 0, apply_res.output
    assert "enterprises/LC00TEST99/policies/baseline" in apply_res.output

    list_res = runner.invoke(main, ["list-policies"])
    assert list_res.exit_code == 0, list_res.output
    assert "baseline (enterprises/LC00TEST99/policies/baseline)" in list_res.output
    assert "relaxed (enterprises/LC00TEST99/policies/relaxed)" in list_res.output


# ---------------------------------------------------------------------------
# CO-05: enroll-qr creates token and saves valid QR PNG to output/
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "expected_personal_usage"),
    [
        ("fully-managed", "PERSONAL_USAGE_DISALLOWED"),
        ("work-profile", "PERSONAL_USAGE_ALLOWED"),
    ],
)
def test_co05_enroll_qr_creates_png(
    tmp_path: pathlib.Path,
    fake_env: dict[str, pathlib.Path],
    mock_amapi_service: MagicMock,
    mode: str,
    expected_personal_usage: str,
) -> None:
    """CO-05: `sandstorm enroll-qr` creates an enrollment token and writes a valid QR PNG."""
    qr_json = json.dumps(
        {
            "android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE": {
                "com.google.android.apps.work.clouddpc.EXTRA_ENROLLMENT_TOKEN": "tok-12345"
            }
        }
    )
    create_mock = mock_amapi_service.enterprises().enrollmentTokens().create
    create_mock.return_value.execute.return_value = {
        "name": "enterprises/LC00TEST99/enrollmentTokens/et1",
        "value": "tok-12345",
        "qrCode": qr_json,
        "expirationTimestamp": "2026-10-15T10:00:00Z",
    }

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "enroll-qr",
            "--mode",
            mode,
            "--policy",
            "baseline",
            "--output-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output

    create_mock.assert_called_with(
        parent="enterprises/LC00TEST99",
        body={
            "policyName": "enterprises/LC00TEST99/policies/baseline",
            "allowPersonalUsage": expected_personal_usage,
            "duration": "3600s",
        },
    )

    expected_png = tmp_path / f"enroll-{mode}-baseline.png"
    assert expected_png.is_file()
    with Image.open(expected_png) as img:
        assert img.format == "PNG"
        assert img.width > 50 and img.height > 50


# ---------------------------------------------------------------------------
# CO-06: list-devices displays API fields honestly
# ---------------------------------------------------------------------------


def test_co06_list_devices_shows_required_fields(
    fake_env: dict[str, pathlib.Path],
    mock_amapi_service: MagicMock,
) -> None:
    """CO-06: `sandstorm list-devices` shows ID, model, Android version, policy, last-seen, compliance."""
    mock_amapi_service.enterprises().devices().list().execute.return_value = {
        "devices": [
            {
                "name": "enterprises/LC00TEST99/devices/emulator-pixel6-001",
                "hardwareInfo": {"model": "Pixel 6"},
                "softwareInfo": {"androidVersion": "14"},
                "appliedPolicyName": "enterprises/LC00TEST99/policies/baseline",
                "lastStatusReportTime": "2026-10-15T08:40:00Z",
                "policyCompliant": True,
                "appliedState": "ACTIVE",
            },
            {
                "name": "enterprises/LC00TEST99/devices/emulator-pixel6-002",
                "hardwareInfo": {"model": "sdk_gphone64_x86_64"},
                "softwareInfo": {"androidVersion": "15"},
                "policyName": "enterprises/LC00TEST99/policies/relaxed",
                "lastPolicySyncTime": "2026-10-15T08:42:00Z",
                "policyCompliant": False,
                "nonComplianceDetails": [{"settingName": "alwaysOnVpnPackage"}],
            },
        ]
    }

    runner = CliRunner()
    result = runner.invoke(main, ["list-devices"])
    assert result.exit_code == 0, result.output
    assert "emulator-pixel6-001" in result.output
    assert "Pixel 6" in result.output
    assert "14" in result.output
    assert "baseline" in result.output
    assert "2026-10-15T08:40:00Z" in result.output
    assert "COMPLIANT" in result.output
    assert "NON_COMPLIANT (alwaysOnVpnPackage)" in result.output


# ---------------------------------------------------------------------------
# CO-07: switch-policy moves a device to another policy
# ---------------------------------------------------------------------------


def test_co07_switch_policy_updates_device(
    fake_env: dict[str, pathlib.Path],
    mock_amapi_service: MagicMock,
) -> None:
    """CO-07: `sandstorm switch-policy <device> <policy>` patches the device's policyName."""
    patch_mock = mock_amapi_service.enterprises().devices().patch
    patch_mock.return_value.execute.return_value = {
        "name": "enterprises/LC00TEST99/devices/emulator-pixel6-001",
        "policyName": "enterprises/LC00TEST99/policies/relaxed",
    }

    runner = CliRunner()
    result = runner.invoke(
        main, ["switch-policy", "emulator-pixel6-001", "relaxed"]
    )
    assert result.exit_code == 0, result.output
    patch_mock.assert_called_with(
        name="enterprises/LC00TEST99/devices/emulator-pixel6-001",
        updateMask="policyName",
        body={
            "policyName": "enterprises/LC00TEST99/policies/relaxed",
            "state": "ACTIVE",
        },
    )
    assert "enterprises/LC00TEST99/policies/relaxed" in result.output


# ---------------------------------------------------------------------------
# CO-08: wipe refuses unless allow-listed AND confirmed by typing device ID
# ---------------------------------------------------------------------------


def test_co08_wipe_refuses_non_allowlisted_device(
    fake_env: dict[str, pathlib.Path],
    mock_amapi_service: MagicMock,
) -> None:
    """CO-08: Wiping a device not in allowed_test_devices is refused without calling AMAPI."""
    delete_mock = mock_amapi_service.enterprises().devices().delete
    runner = CliRunner()
    result = runner.invoke(
        main, ["wipe", "unlisted-device-999"], input="unlisted-device-999\n"
    )
    assert result.exit_code != 0
    assert "not in 'allowed_test_devices'" in result.output
    delete_mock.assert_not_called()


def test_co08_wipe_refuses_personal_phone_even_if_in_config(
    fake_env: dict[str, pathlib.Path],
    mock_amapi_service: MagicMock,
) -> None:
    """Hard rule 1 + CO-08: a device in blocked_devices is refused, even if also allow-listed."""
    fake_env["local_config"].write_text(
        json.dumps(
            {
                "enterprise_name": "enterprises/LC00TEST99",
                "allowed_test_devices": ["personal-phone-01"],
                "blocked_devices": ["personal-phone-01"],
            }
        ),
        encoding="utf-8",
    )
    delete_mock = mock_amapi_service.enterprises().devices().delete
    runner = CliRunner()
    result = runner.invoke(main, ["wipe", "personal-phone-01"], input="personal-phone-01\n")
    assert result.exit_code != 0
    assert "permanently blocked by hard rule 1" in result.output
    delete_mock.assert_not_called()


def test_co08_wipe_refuses_wrong_typed_confirmation(
    fake_env: dict[str, pathlib.Path],
    mock_amapi_service: MagicMock,
) -> None:
    """CO-08: Allow-listed device is NOT wiped if typed confirmation does not match ID."""
    delete_mock = mock_amapi_service.enterprises().devices().delete
    runner = CliRunner()
    result = runner.invoke(
        main, ["wipe", "emulator-pixel6-001"], input="wrong-id\n"
    )
    assert result.exit_code != 0
    assert "does not match" in result.output
    delete_mock.assert_not_called()


def test_co08_wipe_succeeds_for_allowlisted_device_with_matching_confirmation(
    fake_env: dict[str, pathlib.Path],
    mock_amapi_service: MagicMock,
) -> None:
    """CO-08: Allow-listed device with exact typed device ID calls enterprises.devices.delete."""
    delete_mock = mock_amapi_service.enterprises().devices().delete
    delete_mock.return_value.execute.return_value = {}

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["wipe", "emulator-pixel6-001"],
        input="emulator-pixel6-001\n",
    )
    assert result.exit_code == 0, result.output
    delete_mock.assert_called_once_with(
        name="enterprises/LC00TEST99/devices/emulator-pixel6-001"
    )
    assert "Wipe command sent for device 'emulator-pixel6-001'" in result.output


# ---------------------------------------------------------------------------
# CO-10: sandstorm --version prints version from pyproject.toml
# ---------------------------------------------------------------------------


def test_co10_version_matches_pyproject_toml() -> None:
    """CO-10: `sandstorm --version` prints the exact version from pyproject.toml."""
    pyproject_data = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    expected_version = pyproject_data["project"]["version"]
    assert __version__ == expected_version

    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert expected_version in result.output
