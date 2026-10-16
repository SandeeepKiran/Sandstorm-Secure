"""Local FastAPI web dashboard for Sandstorm (Milestone M2: DB-01 through DB-09).

Security rule (Hard rule 8 & DB-01): The dashboard can wipe phones and is never
hosted on the internet. It binds strictly to 127.0.0.1.
Architecture rule (DB-02): All Google API and policy operations call the shared
core modules (`sandstorm.amapi` and `sandstorm.config`).
"""

from __future__ import annotations

import pathlib
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

    def _base_context(request: Request, active_nav: str) -> dict[str, object]:
        return {
            "request": request,
            "active_nav": active_nav,
            "version": get_version(),
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
        devices: list[dict[str, object]] = []
        api_error = error
        allowed_ids: set[str] = set()

        try:
            allowed_ids = config.get_allowed_test_devices()
        except config.ConfigError as exc:
            if not api_error:
                api_error = str(exc)

        try:
            raw_devices = amapi.list_devices()
            for dev in raw_devices:
                dev_copy = dict(dev)
                dev_copy["is_wipe_allowed"] = dev["id"] in allowed_ids
                devices.append(dev_copy)
        except config.ConfigError as exc:
            if not api_error:
                api_error = str(exc)

        ctx = _base_context(request, active_nav="devices")
        ctx.update(
            {
                "devices": devices,
                "policy_names": _collect_policy_names(),
                "notice": notice,
                "error": api_error,
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

        ctx = _base_context(request, active_nav="policies")
        ctx.update(
            {
                "policies": local_policies,
                "selected_id": selected_id,
                "toggles": toggles,
                "raw_json": raw_json,
                "notice": notice,
                "error": error,
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
        ctx = _base_context(request, active_nav="enroll")
        ctx.update(
            {
                "policy_names": _collect_policy_names(),
                "selected_mode": "fully-managed",
                "selected_policy": "baseline",
                "enrollment": None,
                "error": error,
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

        ctx = _base_context(request, active_nav="enroll")
        ctx.update(
            {
                "policy_names": _collect_policy_names(),
                "selected_mode": mode,
                "selected_policy": policy_name,
                "enrollment": enrollment,
                "error": error,
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

    return app
