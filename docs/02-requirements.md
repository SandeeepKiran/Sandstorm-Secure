# 02 — Requirements

> Written as testable requirements, the way a QA engineer would check them.
> Each one has an ID, a requirement, and how to verify it. All are MUST unless marked SHOULD.
> Rewritten 2026-10-15: the goal is a working app + portfolio piece (see `03-decisions.md`).

## M1 — Core + CLI

| ID | Requirement | How to verify |
|---|---|---|
| CO-01 | The app MUST read the service-account key path from env var `SANDSTORM_SA_KEY` and fail with a clear message if it is missing or the file does not exist. | Run with the var unset → readable error, exit code ≠ 0. |
| CO-02 | `sandstorm create-enterprise` MUST walk through Google's signup-URL flow and save the enterprise name to `sandstorm.local.json` (git-ignored). | File exists after the flow; `git status` does not show it. |
| CO-03 | Policies MUST live as JSON files in `policies\`. Provide `baseline.json` (rules below) and `relaxed.json`. | Files exist and pass a shape test. |
| CO-04 | `sandstorm apply-policy <file>` MUST upload a policy and print its name. `sandstorm list-policies` MUST list them. | Policy appears in `list-policies`. |
| CO-05 | `sandstorm enroll-qr --mode fully-managed\|work-profile --policy <name>` MUST create an enrollment token and save a QR PNG to `output\`. | PNG opens; emulator setup wizard accepts it. |
| CO-06 | `sandstorm list-devices` MUST show each device: ID, model, Android version, policy, last-seen time, compliance state — all from the API. | Enrolled emulator appears with real values. |
| CO-07 | `sandstorm switch-policy <device> <policy>` MUST move a device to another policy. | Change visible on the emulator within minutes. |
| CO-08 | `sandstorm wipe <device>` MUST refuse unless the device ID is in the test-device allow-list in `sandstorm.local.json` AND the user types the device ID to confirm. | Unit tests: non-listed ID → refused; wrong confirmation → refused. |
| CO-09 | All Google API calls MUST go through `sandstorm\amapi.py` so pytest can mock them. `pytest` MUST pass with the network off. | `pytest` green offline. |
| CO-10 | `sandstorm --version` MUST print the version from `pyproject.toml`. | Output matches the file. |

**Baseline policy rules to try** (record each result in `docs\FINDINGS.md` — a rule that does not
work in some mode is itself a finding):

- Always-on VPN, with lockdown (no traffic without VPN)
- USB file transfer disabled
- App install allow-list only
- Screen capture disabled
- Factory reset blocked for the user (fully managed only)
- Minimum screen-lock strength
- Remote wipe works

## M2 — Local web dashboard

| ID | Requirement | How to verify |
|---|---|---|
| DB-01 | `sandstorm web` MUST start the dashboard on `127.0.0.1` only (never `0.0.0.0`). | Startup log shows 127.0.0.1; another device on the LAN cannot open it. |
| DB-02 | The dashboard MUST use the same core layer as the CLI — no second copy of API logic. | Code review: web routes call `sandstorm` core functions. |
| DB-03 | **Devices page**: table of devices with the CO-06 fields and a "Refresh" button. Empty state explains how to enroll. | Playwright: page renders with mocked data and with zero devices. |
| DB-04 | **Policies page**: list policies; view a policy as readable toggles; edit toggles and save as a new or updated policy JSON. | Playwright: change a toggle → saved JSON changes. |
| DB-05 | **Enroll page**: choose mode + policy → shows the QR code and the token's expiry time. | QR image appears; expiry shown. |
| DB-06 | **Switch policy** from the device row. | Playwright with mock: request sent with correct device + policy. |
| DB-07 | **Wipe** button only for allow-listed devices, with a typed-confirmation dialog (same rule as CO-08). | Playwright: button hidden for non-listed devices; wrong text → no request. |
| DB-08 | Every status on screen MUST come from API data. No hard-coded "verified", "secure" or counts. | Code review + test with mocked data that changes. |
| DB-09 | Owner's palette, works at 375 px with no sideways scroll, version in the footer. | Playwright screenshots at 375 px and 1280 px. |

## M3 — End-to-end proof on the emulator (fully managed)

| ID | Requirement | How to verify |
|---|---|---|
| E2E-01 | The `Pixel_6` emulator (factory-fresh image) enrolls by scanning the dashboard's QR code. | Device appears in the Devices page. |
| E2E-02 | With `baseline` applied, at least USB file transfer block and the app allow-list are **seen enforced** on the emulator. | Owner watches it; screenshot in FINDINGS. |
| E2E-03 | Switching to `relaxed` from the dashboard visibly changes the emulator (e.g. a blocked app becomes available). | Owner watches it; time-to-apply noted. |
| E2E-04 | Wipe from the dashboard resets the emulator (allow-listed). | Emulator returns to setup wizard. |
| E2E-05 | `docs\FINDINGS.md` records every baseline rule: worked / did not / partly, Android version, notes. | File filled in. |

A short screen recording of E2E-01 … E2E-03 is the portfolio video (SHOULD).

## M4 — Work-profile mode

| ID | Requirement | How to verify |
|---|---|---|
| WP-01 | A work profile can be added on an already-set-up emulator via the dashboard's enrollment flow (no reset). | Work profile (briefcase apps) appears. |
| WP-02 | FINDINGS records which baseline rules apply in work-profile mode and which do not. | FINDINGS has a work-profile column. |
| WP-03 | Removing the work profile from the dashboard leaves the personal side untouched. | Personal apps/data still there. |

A real phone is NOT used here unless the owner decides so later.

## M5 — Mock landing page (`landing\`)

| ID | Requirement | How to verify |
|---|---|---|
| LP-01 | One static page: headline, who it is for, 3–5 bullets of what it does, what it can and cannot see, sign-up form. | Visual check. |
| LP-02 | Wording MUST follow hard rule 7 (honest; no "military-grade", no fake numbers). | Text review. |
| LP-03 | Form fields: name, email, company type, phone count, "biggest worry". | Form check. |
| LP-04 | The form MUST send nothing anywhere: on submit it shows "Thanks — this is a demo, nothing was sent or stored." No backend, no form service, no storage. | Network tab: no request on submit. |
| LP-05 | Works at 375 px width with no sideways scroll. | Playwright screenshot. |
| LP-06 | A visible note says this is a portfolio demo and no data is collected. | Visual check. |
| LP-07 | No external scripts, fonts or CDNs. | View source / network tab. |

## M6 — Demo mode (`demo\`)

| ID | Requirement | How to verify |
|---|---|---|
| DM-01 | A demo build of the dashboard pages that uses sample data from a JSON file — no Google account, no device. | Opens from the file system / static host. |
| DM-02 | Every demo page shows a clear "Demo data" banner. | Visual check on every page. |
| DM-03 | Demo build contains no keys, enterprise names, device IDs or local paths from the real setup. | `grep` the build for the real values → nothing. |
| DM-04 | Dangerous buttons (wipe) are visibly disabled in demo mode. | Playwright check. |

## Out of scope (for now)

iOS / Apple, customer accounts, login system, billing, multi-customer support, public hosting of
the real dashboard, our own Android agent app, custom OS, hardware.
