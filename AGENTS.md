# Sandstorm Secure: handoff for AI coding agents (Cursor, Claude Code, Codex)

> **Read this file first, every session.** Then read `docs\02-requirements.md` (what to build)
> and `docs\03-decisions.md` (what is already decided). The business side is **parked**; its
> notes are kept privately by the owner, outside this repo.
> The owner is a QA engineer who is newer to coding. Explain what you do in plain
> words, with a short "why". Small, reversible steps. Ask before anything hard to undo.

## What this project is

**Sandstorm Secure** is a **working Android
phone-management app (MDM)** built on Google's official **Android Management API (AMAPI)**.
It puts Android phones into a locked-down state (forced VPN, no USB data, app allow-list,
remote wipe) and lets the owner change those rules from a dashboard.

**Goal right now: a real, working app and a portfolio piece.** Not a business yet. Selling,
customers and pricing are parked (decided 2026-10-15). There is no deadline — build it well.

"Working" means **really enforced on a device**, not a dashboard that only shows switches.
Every claim the app or README makes must be something the owner has seen happen.

## Milestones (full, testable requirements in `docs\02-requirements.md`)

| # | Milestone | Done when |
|---|---|---|
| M1 | **Core + CLI**: Python layer that talks to AMAPI, with a CLI and offline pytest tests | CO-01 … CO-10 pass |
| M2 | **Local web dashboard** (FastAPI + HTML pages) on top of the core | DB-01 … DB-09 pass |
| M3 | **End-to-end proof on the emulator** (fully-managed mode) + `docs\FINDINGS.md` | E2E-01 … E2E-05 pass, screen recording made |
| M4 | **Work-profile mode** | WP-01 … WP-03 pass |
| M5 | **Mock landing page** with a sign-up form that sends nothing | LP-01 … LP-07 pass |
| M6 | **Demo mode** (labelled sample data) that can be shown as a static page | DM-01 … DM-04 pass |

Do them in order. **Stop after each milestone and show the owner** before starting the next.

## Hard rules: do not change without asking the owner

1. **Never wipe, factory-reset, lock or enroll a real, personal phone.** All device tests run on
   the **Android Studio emulator `Pixel_6`**. A device the owner wants to protect can be listed
   under `blocked_devices` in the local, git-ignored config; that block wins over the allow-list.
2. Any command or button that wipes, resets or locks a device must check the device against an
   **allow-list of test device IDs** in the local config, and must ask for typed confirmation
   (the user types the device ID).
3. **Secrets never go in the repo.** The Google Cloud service-account key (JSON) lives OUTSIDE
   this folder; its path comes from the env var `SANDSTORM_SA_KEY`, or else from `sa_key_path`
   saved on the dashboard Settings page (in the git-ignored local config). The Settings page
   refuses a path inside the project folder and never shows the private key. `.gitignore`
   already covers keys, `.env*`, `*.local.*` and the local config — do not weaken it.
4. Use a **personal Google account** for the Google Cloud project.
5. **No git at all from Cursor/Codex.** Do not run `git commit`, `git push`, or any git command
   that changes history. Claude Code does all git and GitHub work. Commits are by the owner only:
   no `Co-Authored-By`, no "Generated with" lines.
6. No personal data in repo files (employer, salary, phone numbers, real names, local paths like
   `C:\Users\...`). Private context lives outside the repo.
7. **Honest text only.** No "military-grade", no "unhackable", no "zero telemetry", no fixed
   numbers that look measured ("100% verified"). Every status on screen must come from real data
   (or, in demo mode, be clearly labelled "Demo data"). An MDM provider CAN see device info and
   app lists — say exactly what is visible.
8. **The dashboard is never hosted on the internet.** It can wipe phones. It listens on
   `127.0.0.1` only. Only the landing page (M5) and demo mode (M6) may ever be published.
9. No paid services, sign-ups or new API keys without asking. Free tiers only.
10. Do not write our own on-device agent app or reuse outside sample MDM servers. They tend to
    have fake status values and no security. We use Google's AMAPI for enforcement.

## Stack

| Part | Choice | Why |
|---|---|---|
| Language | **Python 3.11** | Owner reads Python and tests with pytest. |
| AMAPI client | `google-api-python-client` + `google-auth` | Google's official libraries. |
| Web dashboard | **FastAPI** + Jinja2 templates + plain CSS (a little vanilla JS is fine) | FastAPI is already installed; server-rendered pages keep it simple. No React/Next.js. |
| QR code | `qrcode` (PNG) | Enrollment QR for the emulator's setup wizard. |
| Tests | **pytest**, AMAPI mocked; **Playwright (Python)** for dashboard UI checks | Tests run offline with no Google account. |
| Packaging | `pyproject.toml` (version lives here) | One place for the version number. |
| Landing page | One static HTML + CSS file, no build step | Nothing to install or host-manage. |

## Folder layout

```
Project - Sandstorm Secure\
  AGENTS.md            <- this file
  README.md            <- public-safe; screenshots + steps in STE
  CHANGELOG.md
  pyproject.toml       <- version number lives here
  .gitignore
  docs\                <- requirements, decisions, FINDINGS.md
  sandstorm\           <- Python package
    amapi.py           <- the ONE wrapper around Google API calls (mocked in tests)
    config.py          <- reads SANDSTORM_SA_KEY + sandstorm.local.json
    cli.py
    web\               <- FastAPI app, templates\, static\ (MASTER style.css, ui.js, vendor\)
  policies\            <- baseline.json, relaxed.json
  scripts\             <- sync_shared_assets.py, capture_screenshots.py
  tests\               <- conftest.py holds the shared offline fixtures
  landing\             <- index.html, assets\ (hero + Open Graph image) — M5
  demo\                <- static demo build, sample-data.js = the one sample-data file — M6
```

Local, git-ignored files: `sandstorm.local.json` (enterprise name, key path `sa_key_path`,
test-device allow-list, blocked devices), `output\` (QR PNGs, logs, test screenshots).

The landing page and the demo are published on GitHub Pages by
`.github/workflows/pages.yml` (push to `main`): https://sandeeepkiran.github.io/Sandstorm-Secure/
The site root redirects to `landing/`. Only `landing\` and `demo\` are published, never the dashboard.
`og:image` and `og:url` in `landing\index.html` use the full public address (social sites ignore a
relative path); the LP-07 test allows only these two tags to contain `https://`.

## Versioning (owner's rule — every change)

- Version lives in `pyproject.toml`. Start at `0.1.0`.
- **Every change to app code bumps the version** and adds a line to `CHANGELOG.md`
  (patch = fix, minor = new feature or UI change). Docs-only changes need no bump.
- Show the version in the dashboard footer and in `sandstorm --version`.

## Code style

- Readable over clever. Descriptive names. Comments explain **why**, not what.
- Every CLI command and every dangerous button says what it is about to do before it does it.
- Write the README and any steps for the owner in **ASD-STE100 Simplified Technical English**:
  numbered, imperative, one action per step, condition before action.

## Visual style (dashboard, landing page, demo)

⚠️ **This project overrides the owner's default teal-green palette** (owner's decision,
2026-11-02, v5.1.0). Do not bring back the teal gradient, `#0f766e`, `#99f6e4` or any page
background gradient. Reference level: Kandji, Jamf, Linear, Stripe Dashboard.

- **One design system.** Master copies: `sandstorm\web\static\style.css` (all tokens as CSS
  custom properties) and `sandstorm\web\static\ui.js` (icons, theme, menus, toasts, dialogs).
  After you edit them, run `python scripts\sync_shared_assets.py` to copy them to `demo\`
  and `landing\`. A test fails if the copies differ.
- **Light theme is the default.** Dark theme follows `prefers-color-scheme`, plus a manual
  switch saved in `localStorage` (`sandstorm-theme`).
- Light colours: page `#f8fafc`, card `#ffffff`, border `#e2e8f0`, text `#0f172a`, muted
  `#64748b`. Sidebar `#0b1220`, text `#cbd5e1`, active `#ffffff` on `#1e293b`.
- Primary action (buttons, links, focus ring) `#2563eb`, hover `#1d4ed8`.
- Brand sand `#c8a165`: the logo mark and small brand details only. Never on buttons or status.
- Status colours are for status only, as soft pills: success `#16a34a`, warning `#d97706`,
  danger `#dc2626`, info `#0284c7`.
- Dark colours: page `#0b1220`, card `#111a2e`, border `#1f2a44`, text `#e2e8f0`, muted
  `#94a3b8`, primary `#3b82f6` (button fill stays `#2563eb` for AA contrast).
- Font: self-hosted Inter (`vendor\`, SIL OFL), fallback `"Segoe UI Variable", "Segoe UI",
  system-ui`. Sizes 12 / 14 (body) / 16 / 20 / 24 / 32. Monospace for IDs and policy keys.
- 4 px spacing grid. Radius 8 px cards, 6 px controls, 999 px pills. Soft shadows; 1 px borders.
- Icons: Lucide (ISC), inlined in `ui.js` (`<span class="icon" data-icon="name">`). No icon CDN.
- WCAG AA contrast, visible focus rings, `aria-label` on icon buttons, keyboard-usable
  dialogs, `prefers-reduced-motion` respected. Must work at 375 px and look right at 1440 px.
- No external CDNs, fonts or scripts anywhere.
- Screenshots: `python scripts\capture_screenshots.py` (demo only, sample data only).

## Owner's manual steps (Cursor gives STE steps, the owner clicks)

- Create the Google Cloud project, enable the Android Management API, create the service
  account + key, and save the key outside the repo. (Before M1's live test, not before coding.)
- Run the enterprise sign-up flow in the browser with a personal Google account.
- Start the `Pixel_6` emulator and scan the QR code (M3).

## Status

- 2026-10-09: Project folder and docs created by Claude Code.
- 2026-10-15: Direction changed after a planning session: goal = working app + portfolio, not
  business validation. Landing page and sign-up form kept as a **mock**. Private GitHub repo
  created by Claude Code.
- 2026-10-15: Project layout, `pyproject.toml` (`0.1.0`), `CHANGELOG.md`, `policies\`, and **M1
  (Core + CLI)** built (`sandstorm\config.py`, `sandstorm\amapi.py`, `sandstorm\cli.py`,
  `tests\test_m1_core_cli.py`). All 14 offline `pytest` checks for CO-01 … CO-10 pass.
- 2026-10-15: **M2 (Local web dashboard, `v0.2.0`)** built (`sandstorm\web\app.py`, templates,
  `static\style.css`, `sandstorm web` CLI command, and offline Playwright test suite in
  `tests\test_m2_web_dashboard.py`). All checks for DB-01 … DB-09 pass offline.
- 2026-10-15: **M5 (Mock landing page, `landing\index.html`)**, **M6 (Static sample-data demo
  dashboard, `demo\`)**, and **M2 UI/UX polish (`v0.3.0`)** completed with offline Playwright tests
  (`tests\test_m5_m6_landing_and_demo.py`) covering LP-01 … LP-07 and DM-01 … DM-04. Next: Google
  Cloud setup + live M1/M3/M4 emulator proof.
- 2026-10-17: **Renamed to Sandstorm Secure (`v0.4.0`).** Private business notes moved out of the
  repo; the personal-phone ID is no longer hard-coded (`blocked_devices` in the local config instead).
- 2026-10-17: **`v5.0.0`** first public release with the launch video.
- 2026-11-02: **Professional UI redesign + Settings (`v5.1.0`)** by Cursor. New shared design
  system (no teal), dark theme, sidebar shell, summary cards, row menus with a Danger zone,
  toasts, policy switches with a save bar, enroll stepper. New Settings page (key path, Test
  connection, setup checklist), red/amber setup banner, Google buttons disabled until setup is
  done. Demo uses the same design; landing page rebuilt as a product page. Requirements
  ST-01 … ST-06 added. 51 offline tests pass. Next: git + GitHub release by Claude Code, then
  Google Cloud setup and the live M3 emulator proof.

## Next steps (in order)

1. Read `docs\02-requirements.md` and `docs\03-decisions.md`.
2. Create `pyproject.toml` (version `0.1.0`), `CHANGELOG.md`, and the folder layout above.
3. Build **M1** to CO-01 … CO-10, with tests passing offline. Stop and show the owner.
4. Give the owner STE steps for the Google Cloud setup, then run the live M1 checks together.
5. Continue with M2 … M6, stopping after each one.
6. Update the **Status** section above after each milestone.
