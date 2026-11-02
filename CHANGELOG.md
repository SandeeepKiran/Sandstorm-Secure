# Changelog

All notable changes to Sandstorm Secure are documented in this file.

## [5.1.0] — 2026-11-02

### Added
- **Settings page** (`/settings`) with a "Google connection" card: save the path to the service-account key file as `sa_key_path` in the git-ignored `sandstorm.local.json`. The env var `SANDSTORM_SA_KEY` still wins, and the page shows which source is active.
- Key path validation on save: the file must exist, be JSON, have `"type": "service_account"`, `project_id` and `client_email`. A path inside the project folder is refused, so the key cannot be committed by mistake. Only `project_id` and `client_email` are ever shown.
- **Test connection** button: one read-only AMAPI call (`enterprises.get`, or `enterprises.list` before an enterprise exists) with a plain-English result (`amapi.check_connection`).
- **Setup checklist** on Settings: key valid, enterprise registered, test device allow-listed, personal phone blocked (optional), each with a one-line fix.
- **Setup banner** on every dashboard page: red when the key is missing or invalid, amber when the key is valid but no enterprise is registered. It replaces the raw "No enterprise_name found in …" error.
- Buttons that need Google (Refresh, Upload, Save and upload, Generate QR code) are disabled while setup is incomplete, with an accessible tooltip.
- Devices page summary cards: total devices, compliant, not compliant, last refresh (from real AMAPI data only; "—" when there is no data).
- Dark theme (follows the system setting, with a manual switch saved in the browser).
- `scripts/sync_shared_assets.py` (copies the shared design files to `demo/` and `landing/`) and `scripts/capture_screenshots.py` (README, landing hero and Open Graph images from the sample-data demo).
- README screenshots in `docs/media/screenshots/`, and a 1200×630 Open Graph image for the landing page.
- **Live site on GitHub Pages:** the landing page and the demo (`.github/workflows/pages.yml`). The dashboard is never published.
- Tests for the banners, Settings validation, disabled buttons and tooltips, the connection test, the theme switch, the 375 px layout and identical shared files.

### Changed
- **New professional design** for the dashboard, demo and landing page: one shared stylesheet (`style.css`) and script (`ui.js`), self-hosted Inter font (SIL OFL) and Lucide icons (ISC). Light grey-white main area, dark navy sidebar, blue actions, a sand-coloured brand mark, and red/amber/green only for status. The teal-green gradient is gone from this project.
- Dashboard layout: sidebar navigation, page headers, a clean device table (cards below 960 px), a row actions menu with a red **Danger zone** for wipe, toast messages instead of text banners, toggle switches with a sticky "unsaved changes" bar on Policies, and a 3-step stepper with "Download PNG" on Enroll.
- The wipe dialog keeps the typed confirmation and allow-list check, and now traps keyboard focus and returns focus when it closes.
- Device times show as `15 Oct 2026, 09:00 UTC` (the raw AMAPI value stays in the `datetime` attribute). Compliance shows as "Compliant", "Not compliant" (with the setting name) or "Not reported".
- Demo (`demo/`): same shell and styles as the real dashboard, a "Demo data" ribbon on every page, a new Settings page with a labelled sample state, and five sample devices. Sample data now lives in one file, `demo/sample-data.js`.
- Landing page rebuilt as a product page: hero with a real demo screenshot, features, how it works, transparency, FAQ, mock sign-up form and footer. No fake logos, testimonials or numbers.
- Error messages no longer contain full local paths, only the file name `sandstorm.local.json`.

### Removed
- `demo/devices.html` (a copy of `demo/index.html`) and `demo/sample-data.json` (replaced by `demo/sample-data.js`).

## [5.0.0] — 2026-10-17

### Added
- Launch video in the README (`docs/media/`), made from the real demo and landing pages.

### Changed
- Version jumps to **5.0.0**: the first public release of Sandstorm Secure.

## [0.4.0] — 2026-10-17

### Changed
- Renamed the app to **Sandstorm Secure** (dashboard, CLI, landing page and demo).
- A device that must never be wiped, reset or locked now goes in `blocked_devices` in the local, git-ignored `sandstorm.local.json`. It is no longer written in the code. The block still wins over the allow-list.

### Removed
- Business-planning notes (product brief, risks) moved out of the repo. They are private.

## [0.3.0] — 2026-10-15

### Added
- Milestone M5 mock landing page (`landing/index.html`) with plain-language headline, audience description, 5 AMAPI capability bullets, honest disclosure of what an MDM administrator can and cannot see, portfolio demo banner, and a 5-field mock sign-up form that sends zero network requests (`LP-01` through `LP-07`).
- Milestone M6 static sample-data demo dashboard (`demo/sample-data.json`, `demo/index.html`, `demo/devices.html`, `demo/policies.html`, `demo/enroll.html`, `demo/demo.js`, `demo/style.css`) with a prominent `"Demo data"` banner on every page, interactive in-memory policy switching and toggle editing, sample QR preview, zero real IDs/keys/paths, and visibly disabled wipe buttons (`DM-01` through `DM-04`).
- Offline Playwright + `pytest` test suite (`tests/test_m5_m6_landing_and_demo.py`) covering `LP-01` through `LP-07` and `DM-01` through `DM-04`.

### Changed
- Polished Milestone M2 web dashboard UI/UX (`sandstorm/web/static/style.css` and `sandstorm/web/templates/*.html`): grouped policy editor sections with an active-rule summary strip, side-by-side QR enrollment layout, warning badge and `Escape` key support in the remote wipe modal, and distinct compliance status pills.

## [0.2.0] — 2026-10-15

### Added
- Milestone M2 local web dashboard (`sandstorm/web/app.py`, Jinja2 templates, and `static/style.css`) bound strictly to `127.0.0.1` via `sandstorm web` (`DB-01`, `DB-02`).
- Devices page (`/devices`): live device table with `CO-06` fields, refresh button, empty-state enrollment instructions, inline policy switching (`DB-03`, `DB-06`, `DB-08`), and allow-list-only device wipe with a typed-confirmation dialog (`DB-07`).
- Policies page (`/policies`): readable toggle editor for AMAPI policy rules (`alwaysOnVpnPackage`, `usbFileTransferDisabled`, `playStoreMode`, `screenCaptureDisabled`, `factoryResetDisabled`, `passwordRequirements`, `applications`) that saves new or updated policy JSON files (`DB-04`).
- Enroll page (`/enroll`): mode + policy selector that creates an AMAPI enrollment token and displays the QR PNG alongside its expiry time (`DB-05`).
- Owner's teal-green visual palette with responsive layout down to `375 px` phone width (no horizontal scroll) and version in the footer (`DB-09`).
- Offline Playwright + `pytest` test suite (`tests/test_m2_web_dashboard.py`) covering `DB-01` through `DB-09`.

## [0.1.0] — 2026-10-15

### Added
- Initial project layout (`sandstorm`, `policies`, `tests`, `landing`, `demo`, `docs/FINDINGS.md`).
- `sandstorm/config.py`: service-account key validation via `SANDSTORM_SA_KEY`, local config storage in `sandstorm.local.json`, and test-device allow-list safety checks (`CO-01`, `CO-02`, `CO-08`).
- `sandstorm/amapi.py`: single wrapper around Google Android Management API v1 for enterprise signup, policy management, QR enrollment tokens, device listing, policy switching, and remote wipe (`CO-02`, `CO-04 … CO-09`).
- `sandstorm/cli.py`: CLI commands (`create-enterprise`, `apply-policy`, `list-policies`, `enroll-qr`, `list-devices`, `switch-policy`, `wipe`, `--version`) with explicit pre-action explanations and typed confirmation on device wipe (`CO-01 … CO-10`).
- `policies/baseline.json` and `policies/relaxed.json`: AMAPI v1 policy definitions for locked-down and relaxed states (`CO-03`).
- Offline `pytest` test suite covering `CO-01` through `CO-10` with mocked AMAPI calls (`CO-09`).
