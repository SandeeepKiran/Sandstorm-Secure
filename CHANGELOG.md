# Changelog

All notable changes to Sandstorm Secure are documented in this file.

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
