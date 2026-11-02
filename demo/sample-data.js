/* Demo data for the static demo (M6). The ONE source of sample records.
 * The object below is strict JSON, so tests can parse it. Every value is made up.
 */
window.SANDSTORM_DEMO_DATA = {
  "demo_label": "Demo data",
  "version": "5.1.0",
  "last_refresh": "09:15:00 UTC",
  "devices": [
    {
      "id": "sample-pixel6-01",
      "model": "Pixel 6",
      "android_version": "14",
      "management_mode": "FULLY_MANAGED",
      "policy": "baseline",
      "last_seen": "2026-10-15T09:12:00Z",
      "compliance_state": "COMPLIANT",
      "is_wipe_allowed": true
    },
    {
      "id": "sample-galaxya54-02",
      "model": "Galaxy A54",
      "android_version": "14",
      "management_mode": "WORK_PROFILE",
      "policy": "relaxed",
      "last_seen": "2026-10-15T09:10:00Z",
      "compliance_state": "COMPLIANT",
      "is_wipe_allowed": false
    },
    {
      "id": "sample-motog54-03",
      "model": "Moto G54",
      "android_version": "13",
      "management_mode": "FULLY_MANAGED",
      "policy": "baseline",
      "last_seen": "2026-10-15T08:45:00Z",
      "compliance_state": "NON_COMPLIANT (alwaysOnVpnPackage)",
      "is_wipe_allowed": true
    },
    {
      "id": "sample-pixel8-04",
      "model": "Pixel 8",
      "android_version": "15",
      "management_mode": "FULLY_MANAGED",
      "policy": "baseline",
      "last_seen": "2026-10-15T09:14:00Z",
      "compliance_state": "COMPLIANT",
      "is_wipe_allowed": false
    },
    {
      "id": "sample-tab-a9-05",
      "model": "Galaxy Tab A9",
      "android_version": "14",
      "management_mode": "WORK_PROFILE",
      "policy": "relaxed",
      "last_seen": "2026-10-14T17:30:00Z",
      "compliance_state": "UNREPORTED (PROVISIONING)",
      "is_wipe_allowed": false
    }
  ],
  "policies": {
    "baseline": {
      "alwaysOnVpnPackage": {
        "packageName": "com.wireguard.android",
        "lockdownEnabled": true
      },
      "usbFileTransferDisabled": true,
      "playStoreMode": "WHITELIST",
      "applications": [
        {
          "packageName": "com.wireguard.android",
          "installType": "AVAILABLE",
          "defaultPermissionPolicy": "GRANT"
        }
      ],
      "screenCaptureDisabled": true,
      "factoryResetDisabled": true,
      "passwordRequirements": {
        "passwordMinimumLength": 6,
        "passwordQuality": "NUMERIC_COMPLEX",
        "passwordScope": "SCOPE_DEVICE"
      },
      "statusReportingSettings": {
        "applicationReportsEnabled": true,
        "deviceSettingsEnabled": true,
        "displayInfoEnabled": true,
        "hardwareStatusEnabled": true,
        "memoryInfoEnabled": true,
        "networkInfoEnabled": true,
        "powerManagementEventsEnabled": true,
        "softwareInfoEnabled": true
      }
    },
    "relaxed": {
      "usbFileTransferDisabled": false,
      "playStoreMode": "BLACKLIST",
      "applications": [
        {
          "packageName": "com.wireguard.android",
          "installType": "AVAILABLE"
        },
        {
          "packageName": "com.android.chrome",
          "installType": "AVAILABLE"
        },
        {
          "packageName": "com.google.android.calculator",
          "installType": "AVAILABLE"
        }
      ],
      "screenCaptureDisabled": false,
      "factoryResetDisabled": false,
      "passwordRequirements": {
        "passwordMinimumLength": 4,
        "passwordQuality": "NUMERIC",
        "passwordScope": "SCOPE_DEVICE"
      },
      "statusReportingSettings": {
        "applicationReportsEnabled": true,
        "deviceSettingsEnabled": true,
        "displayInfoEnabled": true,
        "hardwareStatusEnabled": true,
        "memoryInfoEnabled": true,
        "networkInfoEnabled": true,
        "powerManagementEventsEnabled": true,
        "softwareInfoEnabled": true
      }
    }
  },
  "enrollment": {
    "sample_expiration": "2026-10-15T10:30:00Z"
  },
  "settings": {
    "sa_key_path": "D:\\keys\\sandstorm-service-account.json",
    "project_id": "demo-project-000000",
    "client_email": "sandstorm-demo@demo-project-000000.iam.gserviceaccount.com",
    "enterprise_name": "enterprises/DEMO_SAMPLE_00"
  }
};
