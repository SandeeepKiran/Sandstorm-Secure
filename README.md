# Sandstorm Secure

A local Android phone-management (MDM) CLI and dashboard built on Google's
[Android Management API](https://developers.google.com/android/management).
It applies a locked-down policy to an Android device and lets you change that policy
from a command-line interface or a local web dashboard.

[![Sandstorm Secure launch video: pick the rules, scan one QR code, see which phones comply](docs/media/sandstorm-secure-launch.gif)](docs/media/sandstorm-secure-launch.mp4)

*The 22-second launch video, made from the real demo pages with sample data. [Watch it in full quality, with sound (MP4)](docs/media/sandstorm-secure-launch.mp4).*

**Status:** `v5.0.0`. Milestones M1 (Core + CLI), M2 (local web dashboard), M5 (mock landing page) and M6 (sample-data demo) are complete and tested offline. Next: the live end-to-end proof on the Android emulator (M3) and work-profile mode (M4).

## What it does

- Creates and uploads device policies (`policies/baseline.json` and `policies/relaxed.json`) for VPN lockdown, USB data block, app allow-list, screen capture block, factory reset block, and screen-lock strength.
- Generates enrollment tokens and saves setup-wizard QR codes (`output/*.png`) for `fully-managed` and `work-profile` modes.
- Lists enrolled devices with real API values (ID, model, Android version, active policy, last-seen timestamp, and compliance state).
- Switches an enrolled device between policies, or wipes an allow-listed test device after typed confirmation.

## What it can see

An MDM provider can see device hardware details (model, Android version), the applied policy state, compliance reports, and the list of installed apps.
This project displays only what the Google Android Management API returns — no hard-coded statuses or fake metrics.

## How to run the offline tests (STE)

1. Open a PowerShell terminal in the project folder.
2. Run the offline test suite:
   ```powershell
   python -m pytest -v
   ```
3. Verify the CLI version:
   ```powershell
   python -m sandstorm --version
   ```

## CLI commands (STE)

> **WARNING:** Never enroll, lock, or wipe a personal phone. Only use the `Pixel_6` Android emulator.

1. Before you run any live command, set the `SANDSTORM_SA_KEY` environment variable to your service-account JSON file path (stored outside this repository):
   ```powershell
   $env:SANDSTORM_SA_KEY = "path\to\your-service-account-key.json"
   ```
2. To register your enterprise and save its name to `sandstorm.local.json`, run:
   ```powershell
   python -m sandstorm create-enterprise
   ```
3. To upload the baseline and relaxed policies, run:
   ```powershell
   python -m sandstorm apply-policy policies\baseline.json
   python -m sandstorm apply-policy policies\relaxed.json
   ```
4. To list all uploaded policies in your enterprise, run:
   ```powershell
   python -m sandstorm list-policies
   ```
5. To create a `fully-managed` enrollment QR code PNG in `output\`, run:
   ```powershell
   python -m sandstorm enroll-qr --mode fully-managed --policy baseline
   ```
6. To list all enrolled devices and their compliance state, run:
   ```powershell
   python -m sandstorm list-devices
   ```
7. To move a device to another policy, run:
   ```powershell
   python -m sandstorm switch-policy <DEVICE_ID> relaxed
   ```
8. To wipe a test device (the device ID must exist in `allowed_test_devices` inside `sandstorm.local.json`), run:
   ```powershell
   python -m sandstorm wipe <DEVICE_ID>
   ```
9. To start the local web dashboard on `http://127.0.0.1:8000`, run:
   ```powershell
   python -m sandstorm web
   ```
