"""Local FastAPI web dashboard for Sandstorm (Milestone M2: DB-01 through DB-09).

Security rule (Hard rule 8 & DB-01): The dashboard can wipe phones and is never
hosted on the internet. It binds strictly to 127.0.0.1.
Architecture rule (DB-02): All Google API and policy operations call the shared
core modules (`sandstorm.amapi` and `sandstorm.config`).
"""

from __future__ import annotations

from datetime import datetime, timezone
import pathlib
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sandstorm import amapi, config, get_version

LOOPBACK_HOST = "127.0.0.1"
WEB_DIR = pathlib.Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

COMPLIANT = "compliant"
NON_COMPLIANT = "non_compliant"
UNREPORTED = "unreported"


def validate_loopback_host(host: str) -> str:
    """Enforce Hard rule 8 and DB-01: the dashboard may only listen on 127.0.0.1."""
    cleaned = host.strip()
    if cleaned != LOOPBACK_HOST:
        raise config.ConfigError(
            f"Refusing to bind web dashboard to '{cleaned}'. "
            f"For security (DB-01 / Hard rule 8), Sandstorm Secure only listens on {LOOPBACK_HOST}."
        )
    return LOOPBACK_HOST


def _collect_policy_names() -> list[str]:
    """Return sorted policy short names from local policies/ (and AMAPI if available)."""
    names = {item["id"] for item in amapi.list_local_policies()}
    if not names:
        names = {"baseline", "relaxed"}
    return sorted(names)


def format_timestamp(raw: str) -> str:
    """Show an AMAPI ISO timestamp as '15 Oct 2026, 09:00 UTC'. Unknown formats pass through."""
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except (AttributeError, ValueError):
        return raw
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%d %b %Y, %H:%M UTC")


def _compliance_view(compliance_state: str) -> dict[str, str]:
    """Split the CO-06 compliance string into a pill tone, a label and a detail (DB-08)."""
    state = compliance_state.strip()
    detail = ""
    if "(" in state and state.endswith(")"):
        detail = state[state.index("(") + 1 : -1]
    if state.startswith("NON_COMPLIANT"):
        return {"tone": NON_COMPLIANT, "label": "Not compliant", "detail": detail}
    if state.startswith("COMPLIANT"):
        return {"tone": COMPLIANT, "label": "Compliant", "detail": detail}
    return {"tone": UNREPORTED, "label": "Not reported", "detail": detail}


def _summarize_devices(devices: list[dict[str, Any]]) -> dict[str, int]:
    tones = [dev["compliance"]["tone"] for dev in devices]
    return {
        "total": len(devices),
        "compliant": tones.count(COMPLIANT),
        "non_compliant": tones.count(NON_COMPLIANT),
    }


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Sandstorm Secure Dashboard",
        version=get_version(),
        docs_url=None,
        redoc_url=None,
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.filters["timestamp"] = format_timestamp

    def _base_context(
        request: Request,
        active_nav: str,
        notice: str = "",
        error: str = "",
    ) -> dict[str, object]:
        return {
            "request": request,
            "active_nav": active_nav,
            "version": get_version(),
            "setup": config.get_setup_status(),
            "notice": notice,
            "error": error,
        }

    @app.get("/", response_class=HTMLResponse)
    def index_redirect() -> RedirectResponse:
        return RedirectResponse(url="/devices", status_code=302)

    @app.get("/devices", response_class=HTMLResponse)
    def devices_page(
        request: Request,
        notice: str = "",
        error: str = "",
    ) -> HTMLResponse:
        """DB-03, DB-06, DB-07, DB-08: Devices table with API status, policy switch, and wipe."""
        ctx = _base_context(request, "devices", notice, error)
        setup = ctx["setup"]
        devices: list[dict[str, Any]] = []
        summary: dict[str, int] | None = None
        last_refresh = ""
        load_error = ""

        # Without a key and an enterprise the setup banner explains what to do,
        # so do not call Google and do not show a raw config error.
        if setup["ready"]:
            try:
                allowed_ids = config.get_allowed_test_devices()
                for dev in amapi.list_devices():
                    dev_copy = dict(dev)
                    dev_copy["is_wipe_allowed"] = dev["id"] in allowed_ids
                    dev_copy["compliance"] = _compliance_view(str(dev["compliance_state"]))
                    devices.append(dev_copy)
                summary = _summarize_devices(devices)
                last_refresh = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
            except config.ConfigError as exc:
                load_error = str(exc)

        ctx.update(
            {
                "devices": devices,
                "summary": summary,
                "last_refresh": last_refresh,
                "load_error": load_error,
                "policy_names": _collect_policy_names(),
            }
        )
        return templates.TemplateResponse(request, "devices.html", ctx)

    @app.post("/devices/{device_id}/switch-policy")
    def switch_device_policy_route(
        device_id: str,
        policy_name: str = Form(...),
    ) -> RedirectResponse:
        """DB-06: Switch an enrolled device to another policy via core layer."""
        try:
            updated = amapi.switch_device_policy(
                device_id=device_id,
                policy_name=policy_name,
            )
            short_dev = config.extract_short_device_id(device_id)
            applied = amapi.normalize_policy_id(
                str(updated.get("policyName", policy_name))
            )
            query = urlencode(
                {"notice": f"Switched device '{short_dev}' to policy '{applied}'."}
            )
        except (config.ConfigError, ValueError) as exc:
            query = urlencode({"error": str(exc)})
        return RedirectResponse(url=f"/devices?{query}", status_code=303)

    @app.post("/devices/{device_id}/wipe")
    def wipe_device_route(
        device_id: str,
        confirmed_device_id: str = Form(""),
    ) -> RedirectResponse:
        """DB-07 & CO-08: Wipe an allow-listed test device after typed confirmation."""
        try:
            result = amapi.wipe_device(
                device_id=device_id,
                confirmed_device_id=confirmed_device_id,
            )
            query = urlencode(
                {
                    "notice": (
                        f"Wipe command sent for device '{result['wiped_device_id']}'."
                    )
                }
            )
        except (config.SafetyError, config.ConfigError, ValueError) as exc:
            query = urlencode({"error": str(exc)})
        return RedirectResponse(url=f"/devices?{query}", status_code=303)

    @app.get("/policies", response_class=HTMLResponse)
    def policies_page(
        request: Request,
        policy: str = "baseline",
        notice: str = "",
        error: str = "",
    ) -> HTMLResponse:
        """DB-04: List policies, view readable toggles, and edit/save policy JSON."""
        local_policies = amapi.list_local_policies()
        selected_id = amapi.normalize_policy_id(policy) if policy else "baseline"

        selected_policy = next(
            (item for item in local_policies if item["id"] == selected_id),
            local_policies[0] if local_policies else None,
        )

        if selected_policy is not None:
            selected_id = str(selected_policy["id"])
            toggles = selected_policy["toggles"]
            raw_json = selected_policy["raw"]
        else:
            toggles = amapi.policy_to_toggles({})
            raw_json = {}

        ctx = _base_context(request, "policies", notice, error)
        ctx.update(
            {
                "policies": local_policies,
                "selected_id": selected_id,
                "toggles": toggles,
                "raw_json": raw_json,
            }
        )
        return templates.TemplateResponse(request, "policies.html", ctx)

    @app.post("/policies/save")
    def save_policy_route(
        policy_id: str = Form(...),
        vpn_enabled: bool = Form(False),
        vpn_package: str = Form("com.wireguard.android"),
        vpn_lockdown: bool = Form(False),
        usb_file_transfer_disabled: bool = Form(False),
        play_store_whitelist_only: bool = Form(False),
        screen_capture_disabled: bool = Form(False),
        factory_reset_disabled: bool = Form(False),
        password_min_length: int = Form(6),
        password_quality: str = Form("NUMERIC_COMPLEX"),
        allowed_packages: str = Form(""),
        upload_to_amapi: bool = Form(False),
    ) -> RedirectResponse:
        """DB-04: Save edited policy toggles as a new or updated policy JSON file."""
        toggles = {
            "vpn_enabled": vpn_enabled,
            "vpn_package": vpn_package,
            "vpn_lockdown": vpn_lockdown,
            "usb_file_transfer_disabled": usb_file_transfer_disabled,
            "play_store_whitelist_only": play_store_whitelist_only,
            "screen_capture_disabled": screen_capture_disabled,
            "factory_reset_disabled": factory_reset_disabled,
            "password_min_length": password_min_length,
            "password_quality": password_quality,
            "allowed_packages": allowed_packages,
        }
        try:
            saved_path, _ = amapi.save_policy_from_toggles(
                policy_id=policy_id,
                toggles=toggles,
            )
            clean_id = saved_path.stem
            msg = f"Saved policy JSON to policies/{clean_id}.json."
            if upload_to_amapi:
                applied = amapi.apply_policy(saved_path, policy_id=clean_id)
                msg += f" Uploaded to AMAPI ({applied.get('name', clean_id)})."
            query = urlencode({"policy": clean_id, "notice": msg})
        except (config.ConfigError, ValueError, OSError) as exc:
            clean_id = amapi.normalize_policy_id(policy_id) or "baseline"
            query = urlencode({"policy": clean_id, "error": str(exc)})
        return RedirectResponse(url=f"/policies?{query}", status_code=303)

    @app.get("/enroll", response_class=HTMLResponse)
    def enroll_page(
        request: Request,
        error: str = "",
    ) -> HTMLResponse:
        """DB-05: Choose enrollment mode + policy to generate a QR code and expiry."""
        ctx = _base_context(request, "enroll", error=error)
        ctx.update(
            {
                "policy_names": _collect_policy_names(),
                "selected_mode": "fully-managed",
                "selected_policy": "baseline",
                "enrollment": None,
            }
        )
        return templates.TemplateResponse(request, "enroll.html", ctx)

    @app.post("/enroll", response_class=HTMLResponse)
    def generate_enroll_qr_route(
        request: Request,
        mode: str = Form("fully-managed"),
        policy_name: str = Form("baseline"),
    ) -> HTMLResponse:
        """DB-05: Create enrollment token via AMAPI and display QR PNG + expiry timestamp."""
        enrollment: dict[str, object] | None = None
        error = ""
        try:
            enrollment = amapi.create_enrollment_qr(
                mode=mode,
                policy_name=policy_name,
            )
        except (config.ConfigError, ValueError) as exc:
            error = str(exc)

        ctx = _base_context(request, "enroll", error=error)
        ctx.update(
            {
                "policy_names": _collect_policy_names(),
                "selected_mode": mode,
                "selected_policy": policy_name,
                "enrollment": enrollment,
            }
        )
        return templates.TemplateResponse(request, "enroll.html", ctx)

    @app.get("/enroll/qr/{filename}")
    def serve_qr_png(filename: str) -> FileResponse:
        """Serve a generated QR PNG from the local output directory."""
        safe_name = pathlib.Path(filename).name
        if safe_name != filename or not safe_name.endswith(".png"):
            raise HTTPException(status_code=400, detail="Invalid QR filename.")
        qr_path = config.resolve_output_dir() / safe_name
        if not qr_path.is_file():
            raise HTTPException(status_code=404, detail="QR image not found.")
        return FileResponse(qr_path, media_type="image/png")

    def _render_settings(
        request: Request,
        notice: str = "",
        error: str = "",
        key_path_value: str | None = None,
        key_path_error: str = "",
        connection: dict[str, Any] | None = None,
    ) -> HTMLResponse:
        ctx = _base_context(request, "settings", notice, error)
        if key_path_value is None:
            try:
                key_path_value = str(config.load_local_config().get("sa_key_path", ""))
            except config.ConfigError:
                key_path_value = ""
        ctx.update(
            {
                "key_path_value": key_path_value,
                "key_path_error": key_path_error,
                "connection": connection,
                "env_var_name": config.SA_KEY_ENV_VAR,
            }
        )
        return templates.TemplateResponse(request, "settings.html", ctx)

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request, notice: str = "", error: str = "") -> HTMLResponse:
        """Settings: Google key path, connection test and setup checklist."""
        return _render_settings(request, notice, error)

    @app.post("/settings/key", response_class=HTMLResponse)
    def save_key_path_route(
        request: Request,
        sa_key_path: str = Form(""),
    ) -> HTMLResponse:
        """Validate and save the service-account key path (never the key itself)."""
        try:
            config.set_sa_key_path(sa_key_path)
        except config.ConfigError as exc:
            return _render_settings(
                request,
                key_path_value=sa_key_path,
                key_path_error=str(exc),
            )
        return RedirectResponse(
            url="/settings?" + urlencode({"notice": "Key path saved. The key file is valid."}),
            status_code=303,
        )

    @app.post("/settings/test-connection", response_class=HTMLResponse)
    def test_connection_route(request: Request) -> HTMLResponse:
        """Make one read-only AMAPI call and show the plain-English result."""
        return _render_settings(request, connection=amapi.check_connection())

    return app
