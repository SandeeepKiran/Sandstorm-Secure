# Android Management API (AMAPI) Findings

> Every rule in `policies/baseline.json` is tested on a real Android emulator (`Pixel_6`) and recorded here.
> No rule is claimed as "verified" until observed on the device (Milestones M3 and M4).

## Test environment

- **Emulator:** `Pixel_6` (Android Studio AVD)
- **Android version:** _Pending live test in M3_
- **API level:** _Pending live test in M3_

## Baseline policy rule matrix

| Rule (`policies/baseline.json` field) | Expected behaviour | Fully-managed mode (M3) | Work-profile mode (M4) | Notes / observations |
|---|---|---|---|---|
| Always-on VPN with lockdown (`alwaysOnVpnPackage`) | Device blocks network traffic unless VPN app (`com.wireguard.android`) is connected | _Pending M3_ | _Pending M4_ | Requires VPN app in `applications` allow-list |
| USB file transfer disabled (`usbFileTransferDisabled: true`) | USB mode is locked to charging only; MTP file transfer disabled | _Pending M3_ | _Pending M4_ | |
| App install allow-list only (`playStoreMode: "WHITELIST"` + `applications`) | Managed Google Play shows only allow-listed apps | _Pending M3_ | _Pending M4_ | |
| Screen capture disabled (`screenCaptureDisabled: true`) | Screenshots and screen recording blocked on device | _Pending M3_ | _Pending M4_ | |
| Factory reset blocked (`factoryResetDisabled: true`) | Factory reset option in Settings disabled for device user | _Pending M3_ | _Pending M4_ | Documented by Google as fully-managed only |
| Minimum screen-lock strength (`passwordRequirements`) | Enforces 6+ digit complex numeric PIN / password | _Pending M3_ | _Pending M4_ | |
| Remote wipe (`enterprises.devices.delete`) | Resets fully-managed device to setup wizard; removes work profile in work-profile mode | _Pending M3_ | _Pending M4_ | Protected by local allow-list + typed confirmation |
