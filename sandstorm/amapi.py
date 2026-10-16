"""Single wrapper around Google's Android Management API (AMAPI) v1 (CO-09).

All Google API calls and policy transformations in Sandstorm go through this
module so offline pytest tests can mock a single seam and both the CLI (M1)
and web dashboard (M2) share identical logic (DB-02).
"""

from __future__ import annotations

import copy
import json
import pathlib
import re
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
import qrcode

from sandstorm.config import (
    SafetyError,
    extract_short_device_id,
    get_enterprise_name,
    get_sa_key_path,
    read_project_id_from_sa_key,
    resolve_output_dir,
    resolve_policies_dir,
    set_enterprise_name,
    verify_device_allowed_for_wipe,
)

AMAPI_SCOPES = ["https://www.googleapis.com/auth/androidmanagement"]
DEFAULT_CALLBACK_URL = "https://localhost/callback"

ENROLLMENT_MODE_TO_PERSONAL_USAGE = {
    "fully-managed": "PERSONAL_USAGE_DISALLOWED",
    "work-profile": "PERSONAL_USAGE_ALLOWED",
}

VALID_POLICY_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

DEFAULT_STATUS_REPORTING = {
    "applicationReportsEnabled": True,
    "deviceSettingsEnabled": True,
    "displayInfoEnabled": True,
    "hardwareStatusEnabled": True,
    "memoryInfoEnabled": True,
    "networkInfoEnabled": True,
    "powerManagementEventsEnabled": True,
    "softwareInfoEnabled": True,
}


def build_amapi_service(sa_key_path: pathlib.Path | None = None) -> Any:
    """Authenticate with the service-account key and return an AMAPI v1 client."""
    resolved_key = sa_key_path or get_sa_key_path()
    credentials = service_account.Credentials.from_service_account_file(
        str(resolved_key),
        scopes=AMAPI_SCOPES,
    )
    return build(
        "androidmanagement",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


def normalize_policy_id(policy_ref: str) -> str:
    """Extract the short policy name from 'baseline' or 'enterprises/.../policies/baseline'."""
    cleaned = policy_ref.strip().strip("/")
    if "/policies/" in cleaned:
        return cleaned.split("/policies/")[-1].strip()
    if cleaned.startswith("policies/"):
        return cleaned.split("policies/", 1)[-1].strip()
    if cleaned.endswith(".json"):
        return pathlib.Path(cleaned).stem
    return cleaned


def full_policy_resource_name(enterprise_name: str, policy_ref: str) -> str:
    """Return 'enterprises/<id>/policies/<policy_id>'."""
    short_id = normalize_policy_id(policy_ref)
    if not short_id:
        raise ValueError("Policy name cannot be empty.")
    return f"{enterprise_name.rstrip('/')}/policies/{short_id}"


def full_device_resource_name(enterprise_name: str, device_ref: str) -> str:
    """Return 'enterprises/<id>/devices/<device_id>'."""
    short_id = extract_short_device_id(device_ref)
    if not short_id:
        raise ValueError("Device ID cannot be empty.")
    return f"{enterprise_name.rstrip('/')}/devices/{short_id}"


def create_signup_url(
    project_id: str | None = None,
    callback_url: str = DEFAULT_CALLBACK_URL,
    service: Any | None = None,
) -> dict[str, str]:
    """Start the enterprise sign-up flow by creating a Google signup URL (CO-02).

    Returns a dict with 'name' (e.g. 'signupUrls/C...') and 'url'.
    """
    resolved_project_id = project_id or read_project_id_from_sa_key()
    amapi = service or build_amapi_service()
    response = (
        amapi.signupUrls()
        .create(projectId=resolved_project_id, callbackUrl=callback_url)
        .execute()
    )
    return {
        "name": str(response["name"]),
        "url": str(response["url"]),
    }


def complete_enterprise_signup(
    signup_url_name: str,
    enterprise_token: str,
    project_id: str | None = None,
    enterprise_display_name: str = "Sandstorm Secure",
    config_path: pathlib.Path | None = None,
    service: Any | None = None,
) -> str:
    """Finish enterprise registration and save enterprise_name to sandstorm.local.json (CO-02)."""
    clean_token = enterprise_token.strip()
    if not clean_token:
        raise ValueError("Enterprise token cannot be empty.")

    resolved_project_id = project_id or read_project_id_from_sa_key()
    amapi = service or build_amapi_service()
    enterprise = (
        amapi.enterprises()
        .create(
            projectId=resolved_project_id,
            signupUrlName=signup_url_name.strip(),
            enterpriseToken=clean_token,
            body={"enterpriseDisplayName": enterprise_display_name},
        )
        .execute()
    )
    enterprise_name = str(enterprise["name"])
    set_enterprise_name(enterprise_name, config_path=config_path)
    return enterprise_name


def load_policy_file(
    policy_file: pathlib.Path | str,
    policies_dir: pathlib.Path | None = None,
) -> tuple[str, dict[str, Any]]:
    """Read and validate a policy JSON file, returning (policy_id, policy_dict) (CO-03)."""
    path = pathlib.Path(policy_file)
    if not path.is_file():
        base_dir = resolve_policies_dir(policies_dir)
        candidate = base_dir / f"{path.stem}.json"
        if candidate.is_file():
            path = candidate
        else:
            raise FileNotFoundError(f"Policy file not found: '{policy_file}'")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Policy file '{path}' is not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or not data:
        raise ValueError(f"Policy file '{path}' must contain a non-empty JSON object.")

    return path.stem, data


def policy_to_toggles(policy_data: dict[str, Any]) -> dict[str, Any]:
    """Convert an AMAPI policy dictionary into readable UI toggles (DB-04)."""
    vpn = policy_data.get("alwaysOnVpnPackage") or {}
    vpn_package = str(vpn.get("packageName", "")).strip()
    vpn_enabled = bool(vpn_package)
    vpn_lockdown = bool(vpn.get("lockdownEnabled", False)) if vpn_enabled else False

    play_store_mode = str(policy_data.get("playStoreMode", "BLACKLIST")).upper()
    play_store_whitelist_only = play_store_mode == "WHITELIST"

    pw_req = policy_data.get("passwordRequirements") or {}
    pw_min_length = int(pw_req.get("passwordMinimumLength", 0) or 0)
    pw_quality = str(pw_req.get("passwordQuality", "NUMERIC"))

    apps = policy_data.get("applications") or []
    allowed_packages = [
        str(app.get("packageName", "")).strip()
        for app in apps
        if isinstance(app, dict) and str(app.get("packageName", "")).strip()
    ]

    return {
        "vpn_enabled": vpn_enabled,
        "vpn_package": vpn_package or "com.wireguard.android",
        "vpn_lockdown": vpn_lockdown,
        "usb_file_transfer_disabled": bool(policy_data.get("usbFileTransferDisabled", False)),
        "play_store_whitelist_only": play_store_whitelist_only,
        "play_store_mode": play_store_mode,
        "screen_capture_disabled": bool(policy_data.get("screenCaptureDisabled", False)),
        "factory_reset_disabled": bool(policy_data.get("factoryResetDisabled", False)),
        "password_min_length": pw_min_length,
        "password_quality": pw_quality,
        "allowed_packages": allowed_packages,
    }


def list_local_policies(policies_dir: pathlib.Path | None = None) -> list[dict[str, Any]]:
    """List all policy JSON files in policies/ with their readable toggles (DB-04)."""
    base_dir = resolve_policies_dir(policies_dir)
    if not base_dir.is_dir():
        return []

    items: list[dict[str, Any]] = []
    for path in sorted(base_dir.glob("*.json")):
        try:
            policy_id, data = load_policy_file(path, policies_dir=base_dir)
        except (OSError, ValueError):
            continue
        items.append(
            {
                "id": policy_id,
                "path": path,
                "raw": data,
                "toggles": policy_to_toggles(data),
            }
        )
    return items


def save_policy_from_toggles(
    policy_id: str,
    toggles: dict[str, Any],
    policies_dir: pathlib.Path | None = None,
) -> tuple[pathlib.Path, dict[str, Any]]:
    """Build or update a policy JSON file in policies/ from readable toggles (DB-04)."""
    clean_id = normalize_policy_id(policy_id)
    if not clean_id or not VALID_POLICY_ID_RE.match(clean_id):
        raise ValueError(
            "Policy name must contain only letters, numbers, hyphens, or underscores."
        )

    base_dir = resolve_policies_dir(policies_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    target_path = base_dir / f"{clean_id}.json"

    if target_path.is_file():
        _, policy_dict = load_policy_file(target_path, policies_dir=base_dir)
        policy_dict = copy.deepcopy(policy_dict)
    else:
        policy_dict = {"statusReportingSettings": copy.deepcopy(DEFAULT_STATUS_REPORTING)}

    vpn_enabled = bool(toggles.get("vpn_enabled", False))
    vpn_package = str(toggles.get("vpn_package", "com.wireguard.android")).strip()
    vpn_lockdown = bool(toggles.get("vpn_lockdown", False))

    if vpn_enabled and vpn_package:
        policy_dict["alwaysOnVpnPackage"] = {
            "packageName": vpn_package,
            "lockdownEnabled": vpn_lockdown,
        }
    else:
        policy_dict.pop("alwaysOnVpnPackage", None)

    policy_dict["usbFileTransferDisabled"] = bool(
        toggles.get("usb_file_transfer_disabled", False)
    )
    policy_dict["playStoreMode"] = (
        "WHITELIST" if toggles.get("play_store_whitelist_only", False) else "BLACKLIST"
    )
    policy_dict["screenCaptureDisabled"] = bool(
        toggles.get("screen_capture_disabled", False)
    )
    policy_dict["factoryResetDisabled"] = bool(
        toggles.get("factory_reset_disabled", False)
    )

    pw_min_len = int(toggles.get("password_min_length", 6) or 0)
    pw_quality = str(toggles.get("password_quality", "NUMERIC_COMPLEX")).strip() or "NUMERIC"
    pw_req = dict(policy_dict.get("passwordRequirements") or {})
    pw_req["passwordMinimumLength"] = pw_min_len
    pw_req["passwordQuality"] = pw_quality
    pw_req.setdefault("passwordScope", "SCOPE_DEVICE")
    policy_dict["passwordRequirements"] = pw_req

    raw_packages = toggles.get("allowed_packages", [])
    if isinstance(raw_packages, str):
        package_list = [
            pkg.strip()
            for pkg in raw_packages.replace(",", "\n").splitlines()
            if pkg.strip()
        ]
    else:
        package_list = [str(pkg).strip() for pkg in raw_packages if str(pkg).strip()]

    if vpn_enabled and vpn_package and vpn_package not in package_list:
        package_list.insert(0, vpn_package)

    existing_apps_by_pkg = {
        str(app.get("packageName")): dict(app)
        for app in (policy_dict.get("applications") or [])
        if isinstance(app, dict) and app.get("packageName")
    }
    applications: list[dict[str, Any]] = []
    for pkg in package_list:
        if pkg in existing_apps_by_pkg:
            applications.append(existing_apps_by_pkg[pkg])
        else:
            app_entry: dict[str, Any] = {
                "packageName": pkg,
                "installType": "AVAILABLE",
            }
            if pkg == vpn_package and vpn_enabled:
                app_entry["defaultPermissionPolicy"] = "GRANT"
            applications.append(app_entry)
    policy_dict["applications"] = applications
    policy_dict.setdefault(
        "statusReportingSettings", copy.deepcopy(DEFAULT_STATUS_REPORTING)
    )

    target_path.write_text(json.dumps(policy_dict, indent=2) + "\n", encoding="utf-8")
    return target_path, policy_dict


def apply_policy(
    policy_file: pathlib.Path | str,
    policy_id: str | None = None,
    enterprise_name: str | None = None,
    config_path: pathlib.Path | None = None,
    policies_dir: pathlib.Path | None = None,
    service: Any | None = None,
) -> dict[str, Any]:
    """Upload (patch) a policy JSON file to AMAPI and return the API response (CO-04)."""
    inferred_id, policy_body = load_policy_file(policy_file, policies_dir=policies_dir)
    target_id = normalize_policy_id(policy_id) if policy_id else inferred_id
    ent_name = enterprise_name or get_enterprise_name(config_path=config_path)
    resource_name = full_policy_resource_name(ent_name, target_id)

    # Remove 'name' from body if present so AMAPI uses the URL resource name cleanly.
    body_copy = {k: v for k, v in policy_body.items() if k != "name"}

    amapi = service or build_amapi_service()
    result = (
        amapi.enterprises()
        .policies()
        .patch(name=resource_name, body=body_copy)
        .execute()
    )
    return dict(result)


def list_policies(
    enterprise_name: str | None = None,
    config_path: pathlib.Path | None = None,
    service: Any | None = None,
) -> list[dict[str, Any]]:
    """Return all policies registered in the enterprise from AMAPI (CO-04)."""
    ent_name = enterprise_name or get_enterprise_name(config_path=config_path)
    amapi = service or build_amapi_service()
    response = amapi.enterprises().policies().list(parent=ent_name).execute()
    policies = response.get("policies", [])
    return list(policies) if isinstance(policies, list) else []


def create_enrollment_qr(
    mode: str,
    policy_name: str,
    output_dir: pathlib.Path | None = None,
    duration: str = "3600s",
    enterprise_name: str | None = None,
    config_path: pathlib.Path | None = None,
    service: Any | None = None,
) -> dict[str, Any]:
    """Create an AMAPI enrollment token and render a QR PNG in output/ (CO-05, DB-05).

    mode must be 'fully-managed' or 'work-profile'.
    """
    normalized_mode = mode.strip().lower()
    if normalized_mode not in ENROLLMENT_MODE_TO_PERSONAL_USAGE:
        valid = ", ".join(sorted(ENROLLMENT_MODE_TO_PERSONAL_USAGE))
        raise ValueError(f"Invalid enrollment mode '{mode}'. Choose from: {valid}.")

    ent_name = enterprise_name or get_enterprise_name(config_path=config_path)
    short_policy = normalize_policy_id(policy_name)
    full_policy = full_policy_resource_name(ent_name, short_policy)
    allow_personal_usage = ENROLLMENT_MODE_TO_PERSONAL_USAGE[normalized_mode]

    token_body = {
        "policyName": full_policy,
        "allowPersonalUsage": allow_personal_usage,
        "duration": duration,
    }

    amapi = service or build_amapi_service()
    token_response = (
        amapi.enterprises()
        .enrollmentTokens()
        .create(parent=ent_name, body=token_body)
        .execute()
    )

    token_value = str(token_response.get("value", ""))
    qr_payload = token_response.get("qrCode")
    if not qr_payload:
        qr_payload = json.dumps(
            {
                "android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE": {
                    "com.google.android.apps.work.clouddpc.EXTRA_ENROLLMENT_TOKEN": token_value
                }
            }
        )

    target_dir = resolve_output_dir(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    qr_filename = f"enroll-{normalized_mode}-{short_policy}.png"
    qr_path = (target_dir / qr_filename).resolve()

    qr_img = qrcode.make(qr_payload)
    qr_img.save(str(qr_path))

    return {
        "token_name": str(token_response.get("name", "")),
        "token_value": token_value,
        "qr_code_payload": qr_payload,
        "qr_path": qr_path,
        "qr_filename": qr_filename,
        "mode": normalized_mode,
        "policy_name": full_policy,
        "short_policy": short_policy,
        "expiration_timestamp": str(token_response.get("expirationTimestamp", "")),
    }


def format_device_summary(raw_device: dict[str, Any]) -> dict[str, Any]:
    """Extract honest, API-sourced device fields required by CO-06 and DB-03/DB-08."""
    full_name = str(raw_device.get("name", ""))
    short_id = extract_short_device_id(full_name)

    hw_info = raw_device.get("hardwareInfo") or {}
    sw_info = raw_device.get("softwareInfo") or {}

    model = str(hw_info.get("model") or hw_info.get("hardware") or "Unknown")
    android_version = str(
        sw_info.get("androidVersion")
        or (f"API {raw_device['apiLevel']}" if "apiLevel" in raw_device else "Unknown")
    )

    raw_policy = str(
        raw_device.get("appliedPolicyName") or raw_device.get("policyName") or ""
    )
    short_policy = normalize_policy_id(raw_policy) if raw_policy else "None"

    last_seen = str(
        raw_device.get("lastStatusReportTime")
        or raw_device.get("lastPolicySyncTime")
        or raw_device.get("enrollmentTime")
        or "Never"
    )

    non_compliance = raw_device.get("nonComplianceDetails") or []
    policy_compliant = raw_device.get("policyCompliant")

    if policy_compliant is True and not non_compliance:
        compliance_state = "COMPLIANT"
    elif policy_compliant is False or non_compliance:
        settings = [
            str(item.get("settingName", "unknown"))
            for item in non_compliance
            if isinstance(item, dict)
        ]
        if settings:
            compliance_state = f"NON_COMPLIANT ({', '.join(settings)})"
        else:
            compliance_state = "NON_COMPLIANT"
    else:
        applied_state = raw_device.get("appliedState") or raw_device.get("state")
        compliance_state = f"UNREPORTED ({applied_state})" if applied_state else "UNREPORTED"

    return {
        "id": short_id,
        "name": full_name,
        "model": model,
        "android_version": android_version,
        "policy": short_policy,
        "policy_name": raw_policy,
        "last_seen": last_seen,
        "compliance_state": compliance_state,
        "management_mode": str(raw_device.get("managementMode", "")),
        "state": str(raw_device.get("appliedState") or raw_device.get("state") or ""),
    }


def list_devices(
    enterprise_name: str | None = None,
    config_path: pathlib.Path | None = None,
    service: Any | None = None,
) -> list[dict[str, Any]]:
    """Fetch all enrolled devices from AMAPI and return structured summaries (CO-06)."""
    ent_name = enterprise_name or get_enterprise_name(config_path=config_path)
    amapi = service or build_amapi_service()
    response = amapi.enterprises().devices().list(parent=ent_name).execute()
    raw_devices = response.get("devices", [])
    if not isinstance(raw_devices, list):
        return []
    return [format_device_summary(device) for device in raw_devices]


def switch_device_policy(
    device_id: str,
    policy_name: str,
    enterprise_name: str | None = None,
    config_path: pathlib.Path | None = None,
    service: Any | None = None,
) -> dict[str, Any]:
    """Assign a device to a different policy in AMAPI (CO-07, DB-06)."""
    ent_name = enterprise_name or get_enterprise_name(config_path=config_path)
    device_resource = full_device_resource_name(ent_name, device_id)
    policy_resource = full_policy_resource_name(ent_name, policy_name)

    amapi = service or build_amapi_service()
    updated = (
        amapi.enterprises()
        .devices()
        .patch(
            name=device_resource,
            updateMask="policyName",
            body={"policyName": policy_resource, "state": "ACTIVE"},
        )
        .execute()
    )
    return dict(updated)


def wipe_device(
    device_id: str,
    confirmed_device_id: str,
    enterprise_name: str | None = None,
    config_path: pathlib.Path | None = None,
    service: Any | None = None,
) -> dict[str, Any]:
    """Wipe a device via AMAPI enterprises.devices.delete (CO-08, DB-07, Hard rules 1 & 2).

    Refuses unless:
    1. device_id is in allowed_test_devices in sandstorm.local.json (and not forbidden), AND
    2. confirmed_device_id matches the target short device ID.
    """
    short_id = verify_device_allowed_for_wipe(device_id, config_path=config_path)
    typed = extract_short_device_id(confirmed_device_id) if confirmed_device_id else ""

    if typed != short_id:
        raise SafetyError(
            f"Wipe aborted: confirmation '{confirmed_device_id}' does not match "
            f"target device ID '{short_id}'."
        )

    ent_name = enterprise_name or get_enterprise_name(config_path=config_path)
    device_resource = full_device_resource_name(ent_name, short_id)

    amapi = service or build_amapi_service()
    result = amapi.enterprises().devices().delete(name=device_resource).execute()
    return {
        "wiped_device_id": short_id,
        "device_name": device_resource,
        "api_response": result if isinstance(result, dict) else {},
    }
