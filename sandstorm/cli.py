"""Command-line interface for Sandstorm (Milestones M1 & M2: CO-01..CO-10, DB-01).

Every command explains what it is about to do before calling Google's
Android Management API. Destructive actions require the target device ID to be
in the local allow-list and require typed confirmation from the user.
"""

from __future__ import annotations

import pathlib
from urllib.parse import parse_qs, urlparse

import click
import uvicorn

from sandstorm import amapi, get_version
from sandstorm.config import (
    ConfigError,
    SafetyError,
    extract_short_device_id,
    resolve_local_config_path,
    verify_device_allowed_for_wipe,
)
from sandstorm.web.app import LOOPBACK_HOST, create_app, validate_loopback_host


def _extract_enterprise_token(raw_input: str) -> str:
    """Extract enterpriseToken whether the user pastes the raw token or full callback URL."""
    cleaned = raw_input.strip()
    if "enterpriseToken=" in cleaned:
        parsed = urlparse(cleaned)
        query_params = parse_qs(parsed.query)
        tokens = query_params.get("enterpriseToken")
        if tokens and tokens[0].strip():
            return tokens[0].strip()
    return cleaned


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    version=get_version(),
    prog_name="sandstorm",
    message="%(prog)s %(version)s",
)
def main() -> None:
    """Sandstorm Secure: local Android phone-management (MDM) CLI built on Google AMAPI."""


@main.command("create-enterprise")
@click.option(
    "--project-id",
    default=None,
    help="Google Cloud project ID (defaults to project_id inside SANDSTORM_SA_KEY).",
)
@click.option(
    "--display-name",
    default="Sandstorm Secure",
    show_default=True,
    help="Enterprise display name shown during enrollment.",
)
@click.option(
    "--callback-url",
    default=amapi.DEFAULT_CALLBACK_URL,
    show_default=True,
    help="Callback URL registered with Google's enterprise signup flow.",
)
def create_enterprise_cmd(
    project_id: str | None,
    display_name: str,
    callback_url: str,
) -> None:
    """Walk through Google's enterprise signup flow and save to sandstorm.local.json (CO-02)."""
    click.echo(
        "About to request an enterprise signup URL from Google Android Management API "
        "and save the resulting enterprise name to sandstorm.local.json."
    )
    try:
        signup_info = amapi.create_signup_url(
            project_id=project_id,
            callback_url=callback_url,
        )
        click.echo("")
        click.echo(f"Signup URL resource: {signup_info['name']}")
        click.echo("1. Open this URL in your browser with your personal Google account:")
        click.echo(f"   {signup_info['url']}")
        click.echo(
            "2. Complete the registration steps. At the end, the browser redirects to "
            f"{callback_url}?enterpriseToken=<TOKEN>."
        )
        raw_token = click.prompt(
            "3. Paste the enterpriseToken (or the full redirected URL)"
        )
        token = _extract_enterprise_token(raw_token)

        click.echo("About to complete enterprise creation with Google AMAPI...")
        enterprise_name = amapi.complete_enterprise_signup(
            signup_url_name=signup_info["name"],
            enterprise_token=token,
            project_id=project_id,
            enterprise_display_name=display_name,
        )
        local_cfg = resolve_local_config_path()
        click.echo(f"Created enterprise: {enterprise_name}")
        click.echo(f"Saved enterprise_name to {local_cfg}")
    except (ConfigError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("apply-policy")
@click.argument(
    "policy_file",
    type=click.Path(exists=False, dir_okay=False, path_type=pathlib.Path),
)
@click.option(
    "--name",
    "policy_id",
    default=None,
    help="Optional policy ID override (defaults to the JSON filename stem).",
)
def apply_policy_cmd(policy_file: pathlib.Path, policy_id: str | None) -> None:
    """Upload a policy JSON file to AMAPI and print its resource name (CO-04)."""
    click.echo(
        f"About to upload policy file '{policy_file}' to Google Android Management API."
    )
    try:
        result = amapi.apply_policy(policy_file=policy_file, policy_id=policy_id)
        applied_name = result.get("name", "")
        click.echo(f"Applied policy: {applied_name}")
    except (ConfigError, FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("list-policies")
def list_policies_cmd() -> None:
    """List all policies currently stored in the enterprise on AMAPI (CO-04)."""
    click.echo("About to fetch all policies for this enterprise from Google AMAPI.")
    try:
        policies = amapi.list_policies()
        if not policies:
            click.echo("No policies found in this enterprise.")
            return
        for pol in policies:
            name = pol.get("name", "unknown")
            short_id = amapi.normalize_policy_id(str(name))
            version = pol.get("version", "?")
            play_mode = pol.get("playStoreMode", "UNSPECIFIED")
            usb_disabled = bool(pol.get("usbFileTransferDisabled", False))
            click.echo(
                f"- {short_id} ({name}) | version={version} "
                f"| playStoreMode={play_mode} | usbFileTransferDisabled={usb_disabled}"
            )
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("enroll-qr")
@click.option(
    "--mode",
    required=True,
    type=click.Choice(["fully-managed", "work-profile"], case_sensitive=False),
    help="Enrollment mode: 'fully-managed' (fresh device) or 'work-profile' (existing device).",
)
@click.option(
    "--policy",
    "policy_name",
    required=True,
    help="Policy name to apply upon enrollment (e.g. 'baseline' or 'relaxed').",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=pathlib.Path),
    default=None,
    help="Directory to write the QR PNG file (defaults to output/).",
)
def enroll_qr_cmd(
    mode: str,
    policy_name: str,
    output_dir: pathlib.Path | None,
) -> None:
    """Create an enrollment token and save a QR code PNG to output/ (CO-05)."""
    click.echo(
        f"About to create a '{mode}' enrollment token for policy '{policy_name}' "
        "and save its QR code PNG."
    )
    try:
        info = amapi.create_enrollment_qr(
            mode=mode,
            policy_name=policy_name,
            output_dir=output_dir,
        )
        click.echo(f"Enrollment mode:  {info['mode']}")
        click.echo(f"Applied policy:   {info['policy_name']}")
        if info["expiration_timestamp"]:
            click.echo(f"Token expires at: {info['expiration_timestamp']}")
        click.echo(f"Saved QR PNG to:  {info['qr_path']}")
    except (ConfigError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("list-devices")
def list_devices_cmd() -> None:
    """List enrolled devices with ID, model, Android version, policy, last-seen, and compliance (CO-06)."""
    click.echo("About to fetch enrolled devices and their status from Google AMAPI.")
    try:
        devices = amapi.list_devices()
        if not devices:
            click.echo("No enrolled devices found.")
            return
        header = (
            f"{'ID':<18} {'MODEL':<20} {'ANDROID':<10} "
            f"{'POLICY':<14} {'LAST SEEN':<24} {'COMPLIANCE'}"
        )
        click.echo(header)
        click.echo("-" * len(header))
        for dev in devices:
            click.echo(
                f"{dev['id']:<18} {dev['model']:<20} {dev['android_version']:<10} "
                f"{dev['policy']:<14} {dev['last_seen']:<24} {dev['compliance_state']}"
            )
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("switch-policy")
@click.argument("device_id")
@click.argument("policy_name")
def switch_policy_cmd(device_id: str, policy_name: str) -> None:
    """Switch an enrolled device to another policy (CO-07)."""
    short_device = extract_short_device_id(device_id)
    short_policy = amapi.normalize_policy_id(policy_name)
    click.echo(
        f"About to switch device '{short_device}' to policy '{short_policy}' via Google AMAPI."
    )
    try:
        updated = amapi.switch_device_policy(device_id=device_id, policy_name=policy_name)
        applied_policy = updated.get("policyName", short_policy)
        click.echo(f"Switched device '{short_device}' to policy: {applied_policy}")
    except (ConfigError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("wipe")
@click.argument("device_id")
def wipe_cmd(device_id: str) -> None:
    """Wipe an allow-listed test device after typed confirmation (CO-08)."""
    short_device = extract_short_device_id(device_id)
    click.echo(
        f"WARNING: About to remotely wipe device '{short_device}'. "
        "On a fully-managed device this performs a full factory reset; "
        "on a work-profile device it deletes the work profile."
    )
    try:
        verified_id = verify_device_allowed_for_wipe(device_id)
        typed_confirmation = click.prompt(
            f"To confirm, type the exact device ID ('{verified_id}')",
            default="",
            show_default=False,
        )
        result = amapi.wipe_device(
            device_id=verified_id,
            confirmed_device_id=typed_confirmation,
        )
        click.echo(f"Wipe command sent for device '{result['wiped_device_id']}'.")
    except (SafetyError, ConfigError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("web")
@click.option(
    "--host",
    default=LOOPBACK_HOST,
    show_default=True,
    help="Bind address (must be 127.0.0.1 per DB-01 / Hard rule 8).",
)
@click.option(
    "--port",
    default=8000,
    show_default=True,
    type=int,
    help="Local TCP port for the web dashboard.",
)
def web_cmd(host: str, port: int) -> None:
    """Start the local web dashboard on 127.0.0.1 only (DB-01)."""
    try:
        safe_host = validate_loopback_host(host)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        f"About to start the local Sandstorm Secure web dashboard on http://{safe_host}:{port} "
        "(bound strictly to 127.0.0.1; never exposed to the LAN or internet)."
    )
    uvicorn.run(create_app(), host=safe_host, port=port, log_level="info")
