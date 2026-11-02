"""Configuration and safety checks for Sandstorm (CO-01, CO-02, CO-08).

Reads the Google Cloud service-account key path from the SANDSTORM_SA_KEY
environment variable (or, if that is not set, from `sa_key_path` saved on the
dashboard Settings page) and manages local, git-ignored settings in
sandstorm.local.json (enterprise name, key path, test-device allow-list and
blocked devices).
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

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_LOCAL_CONFIG_PATH = PROJECT_ROOT / "sandstorm.local.json"
DEFAULT_POLICIES_DIR = PROJECT_ROOT / "policies"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

KEY_SOURCE_ENV = "env"
KEY_SOURCE_SETTINGS = "settings"
KEY_SOURCE_NONE = "none"

# Hard rule 1: never wipe, reset or lock a personal phone. Its ID is private, so it lives in the
# git-ignored local config (`blocked_devices`), not in the code. The block wins over the allow-list.


class ConfigError(Exception):
    """Raised when required configuration or credentials are missing or invalid."""


class SafetyError(ConfigError):
    """Raised when a destructive action targets a non-allow-listed or forbidden device."""


def get_sa_key_source(config_path: pathlib.Path | None = None) -> tuple[str, str]:
    """Return (source, raw_path) for the service-account key.

    The env var wins over the saved Settings value, so a CI or shell override
    always takes effect.
    """
    env_path = os.environ.get(SA_KEY_ENV_VAR, "").strip()
    if env_path:
        return KEY_SOURCE_ENV, env_path
    try:
        saved_path = str(load_local_config(config_path).get("sa_key_path", "")).strip()
    except ConfigError:
        saved_path = ""
    if saved_path:
        return KEY_SOURCE_SETTINGS, saved_path
    return KEY_SOURCE_NONE, ""


def get_sa_key_path(config_path: pathlib.Path | None = None) -> pathlib.Path:
    """Return the path to the service-account JSON key (CO-01).

    Reads SANDSTORM_SA_KEY first, then `sa_key_path` in sandstorm.local.json.
    """
    source, raw_path = get_sa_key_source(config_path)
    if source == KEY_SOURCE_NONE:
        raise ConfigError(
            f"Environment variable {SA_KEY_ENV_VAR} is not set, and no key path is saved "
            "on the Settings page. Set it to the path of your Google Cloud service-account "
            "JSON key file (kept outside this repository)."
        )

    origin = SA_KEY_ENV_VAR if source == KEY_SOURCE_ENV else "Settings"
    key_path = pathlib.Path(raw_path).expanduser()
    if not key_path.is_file():
        raise ConfigError(
            f"Service-account key file does not exist: '{key_path}' "
            f"(from {origin}). Check the file path and try again."
        )

    return key_path.resolve()


def is_inside_project(path: pathlib.Path) -> bool:
    """Return True if the path is inside the project folder."""
    try:
        path.expanduser().resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        return False
    return True


def validate_sa_key_file(key_path: pathlib.Path) -> dict[str, str]:
    """Check that a file is a usable service-account key. Return its public fields only.

    The return value never contains the private key, so callers can show it in the UI.
    The error messages never contain file contents.
    """
    if not key_path.is_file():
        raise ConfigError("The key file does not exist. Check the path and try again.")
    try:
        payload = json.loads(key_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError("The key file is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ConfigError("The key file is not valid JSON.")

    if payload.get("type") != "service_account":
        raise ConfigError(
            "The file is JSON, but it is not a service-account key "
            "(its \"type\" is not \"service_account\")."
        )
    project_id = payload.get("project_id")
    client_email = payload.get("client_email")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ConfigError("The key file has no \"project_id\".")
    if not isinstance(client_email, str) or not client_email.strip():
        raise ConfigError("The key file has no \"client_email\".")
    return {"project_id": project_id.strip(), "client_email": client_email.strip()}


def set_sa_key_path(raw_path: str, config_path: pathlib.Path | None = None) -> dict[str, str]:
    """Validate a key path and save it as `sa_key_path` in sandstorm.local.json.

    Returns the key's public fields (project_id, client_email).
    """
    cleaned = raw_path.strip().strip('"').strip()
    if not cleaned:
        raise ConfigError("Enter the full path to the key file.")
    key_path = pathlib.Path(cleaned).expanduser()
    if not key_path.is_absolute():
        raise ConfigError("Enter a full path (for example, one that starts with a drive letter).")
    # Hard rule 3: a key inside the repo can be committed by mistake.
    if is_inside_project(key_path):
        raise ConfigError(
            "Refused: this path is inside the project folder. A key there can be "
            "committed to git by mistake. Move the key to a folder outside the project."
        )
    public_fields = validate_sa_key_file(key_path)

    cfg = load_local_config(config_path)
    cfg["sa_key_path"] = str(key_path.resolve())
    save_local_config(cfg, config_path)
    return public_fields


def get_setup_status(config_path: pathlib.Path | None = None) -> dict[str, Any]:
    """Return the setup state used by the dashboard banner, checklist and disabled buttons."""
    source, raw_key_path = get_sa_key_source(config_path)
    status: dict[str, Any] = {
        "key_source": source,
        "key_ok": False,
        "key_error": "",
        "project_id": "",
        "client_email": "",
        "enterprise_ok": False,
        "enterprise_name": "",
        "has_test_device": False,
        "has_blocked_device": False,
        "config_error": "",
    }

    if source == KEY_SOURCE_NONE:
        status["key_error"] = "No key path is set."
    else:
        try:
            status.update(validate_sa_key_file(pathlib.Path(raw_key_path).expanduser()))
            status["key_ok"] = True
        except ConfigError as exc:
            status["key_error"] = str(exc)

    try:
        cfg = load_local_config(config_path)
        enterprise_name = str(cfg.get("enterprise_name", "")).strip()
        status["enterprise_ok"] = bool(enterprise_name)
        status["enterprise_name"] = enterprise_name
        status["has_test_device"] = bool(get_allowed_test_devices(config_path))
        status["has_blocked_device"] = bool(get_blocked_devices(config_path))
    except ConfigError as exc:
        status["config_error"] = str(exc)

    status["ready"] = status["key_ok"] and status["enterprise_ok"]
    return status


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
        raise ConfigError(f"Could not read local config '{path.name}': {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Local config '{path.name}' must contain a JSON object.")

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
            f"No enterprise_name found in '{path.name}'. "
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
            f"in '{path.name}'. Only explicitly allow-listed test devices may be wiped."
        )

    return short_id
