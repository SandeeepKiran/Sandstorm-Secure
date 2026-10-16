"""Configuration and safety checks for Sandstorm (CO-01, CO-02, CO-08).

Reads the Google Cloud service-account key path from the SANDSTORM_SA_KEY
environment variable and manages local, git-ignored settings in
sandstorm.local.json (enterprise name, test-device allow-list and blocked devices).
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Any

SA_KEY_ENV_VAR = "SANDSTORM_SA_KEY"
LOCAL_CONFIG_ENV_VAR = "SANDSTORM_LOCAL_CONFIG"
POLICIES_DIR_ENV_VAR = "SANDSTORM_POLICIES_DIR"
OUTPUT_DIR_ENV_VAR = "SANDSTORM_OUTPUT_DIR"

DEFAULT_LOCAL_CONFIG_PATH = (
    pathlib.Path(__file__).resolve().parent.parent / "sandstorm.local.json"
)
DEFAULT_POLICIES_DIR = pathlib.Path(__file__).resolve().parent.parent / "policies"
DEFAULT_OUTPUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "output"

# Hard rule 1: never wipe, reset or lock a personal phone. Its ID is private, so it lives in the
# git-ignored local config (`blocked_devices`), not in the code. The block wins over the allow-list.


class ConfigError(Exception):
    """Raised when required configuration or credentials are missing or invalid."""


class SafetyError(ConfigError):
    """Raised when a destructive action targets a non-allow-listed or forbidden device."""


def get_sa_key_path() -> pathlib.Path:
    """Return the validated path to the service-account JSON key from SANDSTORM_SA_KEY (CO-01)."""
    raw_path = os.environ.get(SA_KEY_ENV_VAR, "").strip()
    if not raw_path:
        raise ConfigError(
            f"Environment variable {SA_KEY_ENV_VAR} is not set. "
            "Set it to the path of your Google Cloud service-account JSON key file "
            "(kept outside this repository)."
        )

    key_path = pathlib.Path(raw_path).expanduser()
    if not key_path.is_file():
        raise ConfigError(
            f"Service-account key file does not exist: '{key_path}' "
            f"(from {SA_KEY_ENV_VAR}). Check the file path and try again."
        )

    return key_path.resolve()


def read_project_id_from_sa_key(key_path: pathlib.Path | None = None) -> str:
    """Read the Google Cloud project_id from the service-account JSON key file."""
    resolved_path = key_path or get_sa_key_path()
    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(
            f"Failed to parse service-account key file '{resolved_path}' as JSON: {exc}"
        ) from exc

    project_id = payload.get("project_id")
    if not project_id or not isinstance(project_id, str):
        raise ConfigError(
            f"Service-account key file '{resolved_path}' is missing a valid 'project_id' field."
        )
    return project_id.strip()


def resolve_local_config_path(config_path: pathlib.Path | None = None) -> pathlib.Path:
    """Determine the path to sandstorm.local.json."""
    if config_path is not None:
        return pathlib.Path(config_path)
    env_override = os.environ.get(LOCAL_CONFIG_ENV_VAR, "").strip()
    if env_override:
        return pathlib.Path(env_override).expanduser()
    return DEFAULT_LOCAL_CONFIG_PATH


def resolve_policies_dir(policies_dir: pathlib.Path | None = None) -> pathlib.Path:
    """Determine the directory containing policy JSON files."""
    if policies_dir is not None:
        return pathlib.Path(policies_dir)
    env_override = os.environ.get(POLICIES_DIR_ENV_VAR, "").strip()
    if env_override:
        return pathlib.Path(env_override).expanduser()
    return DEFAULT_POLICIES_DIR


def resolve_output_dir(output_dir: pathlib.Path | None = None) -> pathlib.Path:
    """Determine the directory for generated QR PNGs and logs."""
    if output_dir is not None:
        return pathlib.Path(output_dir)
    env_override = os.environ.get(OUTPUT_DIR_ENV_VAR, "").strip()
    if env_override:
        return pathlib.Path(env_override).expanduser()
    return DEFAULT_OUTPUT_DIR


def load_local_config(config_path: pathlib.Path | None = None) -> dict[str, Any]:
    """Load sandstorm.local.json if it exists, or return default empty structure."""
    path = resolve_local_config_path(config_path)
    if not path.is_file():
        return {
            "enterprise_name": "",
            "allowed_test_devices": [],
            "blocked_devices": [],
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Could not read local config '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Local config '{path}' must contain a JSON object.")

    data.setdefault("enterprise_name", "")
    data.setdefault("allowed_test_devices", [])
    data.setdefault("blocked_devices", [])
    return data


def save_local_config(
    data: dict[str, Any], config_path: pathlib.Path | None = None
) -> pathlib.Path:
    """Save local settings to sandstorm.local.json."""
    path = resolve_local_config_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = {
        "enterprise_name": data.get("enterprise_name", ""),
        "allowed_test_devices": list(data.get("allowed_test_devices", [])),
    }
    for key, value in data.items():
        if key not in merged:
            merged[key] = value
    path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return path


def get_enterprise_name(config_path: pathlib.Path | None = None) -> str:
    """Return the configured enterprise resource name (e.g. 'enterprises/LC012345')."""
    cfg = load_local_config(config_path)
    enterprise_name = str(cfg.get("enterprise_name", "")).strip()
    if not enterprise_name:
        path = resolve_local_config_path(config_path)
        raise ConfigError(
            f"No enterprise_name found in '{path}'. "
            "Run 'sandstorm create-enterprise' first to register your enterprise."
        )
    if not enterprise_name.startswith("enterprises/"):
        enterprise_name = f"enterprises/{enterprise_name}"
    return enterprise_name


def set_enterprise_name(
    enterprise_name: str, config_path: pathlib.Path | None = None
) -> pathlib.Path:
    """Save the enterprise resource name into sandstorm.local.json (CO-02)."""
    clean_name = enterprise_name.strip()
    if not clean_name:
        raise ConfigError("Enterprise name cannot be empty.")
    if not clean_name.startswith("enterprises/"):
        clean_name = f"enterprises/{clean_name}"

    cfg = load_local_config(config_path)
    cfg["enterprise_name"] = clean_name
    return save_local_config(cfg, config_path)


def extract_short_device_id(device_ref: str) -> str:
    """Return the trailing device ID from either '3a8b9c' or 'enterprises/.../devices/3a8b9c'."""
    cleaned = device_ref.strip().strip("/")
    if "/devices/" in cleaned:
        return cleaned.split("/devices/")[-1].strip()
    if cleaned.startswith("devices/"):
        return cleaned.split("devices/", 1)[-1].strip()
    return cleaned


def get_blocked_devices(config_path: pathlib.Path | None = None) -> set[str]:
    """Return the normalized device IDs that must never be wiped, reset or locked."""
    cfg = load_local_config(config_path)
    raw_blocklist = cfg.get("blocked_devices", [])
    if not isinstance(raw_blocklist, list):
        raise SafetyError("Local config 'blocked_devices' must be a list of device IDs.")
    return {extract_short_device_id(str(item)) for item in raw_blocklist if str(item).strip()}


def get_allowed_test_devices(config_path: pathlib.Path | None = None) -> set[str]:
    """Return the set of normalized allow-listed test device IDs, excluding blocked IDs."""
    cfg = load_local_config(config_path)
    blocked = get_blocked_devices(config_path)
    raw_allowlist = cfg.get("allowed_test_devices", [])
    if not isinstance(raw_allowlist, list):
        raise SafetyError("Local config 'allowed_test_devices' must be a list of device IDs.")

    return {
        extract_short_device_id(str(item))
        for item in raw_allowlist
        if str(item).strip()
        and extract_short_device_id(str(item)) not in blocked
    }


def verify_device_allowed_for_wipe(
    device_ref: str, config_path: pathlib.Path | None = None
) -> str:
    """Verify that a device is permitted to be wiped/reset/locked (Hard rules 1 & 2, CO-08).

    Returns the normalized short device ID if allowed, or raises SafetyError.
    """
    short_id = extract_short_device_id(device_ref)
    if not short_id:
        raise SafetyError("Device ID cannot be empty.")

    blocked = get_blocked_devices(config_path)
    if short_id in blocked or device_ref.strip() in blocked:
        raise SafetyError(
            f"Refusing operation: device '{short_id}' is permanently blocked by hard rule 1 "
            "(listed in 'blocked_devices', personal phone protection)."
        )

    normalized_allowlist = get_allowed_test_devices(config_path)

    if short_id not in normalized_allowlist:
        path = resolve_local_config_path(config_path)
        raise SafetyError(
            f"Refusing to wipe device '{short_id}': it is not in 'allowed_test_devices' "
            f"in '{path}'. Only explicitly allow-listed test devices may be wiped."
        )

    return short_id
