/* Sandstorm static demo mode logic (Milestone M6: DM-01 through DM-04)
 * Loads sample data from ./sample-data.json when served over HTTP, and falls back
 * to the identical embedded sample dataset when opened directly via file://.
 * Makes zero external network requests.
 */

(function () {
  var FALLBACK_SAMPLE_DATA = {
    demo_label: "Demo data",
    demo_notice:
      "Demo data \u2014 All devices, policies, and enrollment tokens shown here are sample records from demo/sample-data.json. No Google Cloud account or Android device is connected.",
    version: "0.4.0",
    devices: [
      {
        id: "sample-pixel6-01",
        model: "Pixel 6 (Emulator Sample)",
        android_version: "14",
        management_mode: "FULLY_MANAGED",
        policy: "baseline",
        last_seen: "2026-10-15T09:12:00Z",
        compliance_state: "COMPLIANT",
        is_wipe_allowed: true
      },
      {
        id: "sample-galaxya54-02",
        model: "Galaxy A54 (Work Profile Sample)",
        android_version: "14",
        management_mode: "WORK_PROFILE",
        policy: "relaxed",
        last_seen: "2026-10-15T09:10:00Z",
        compliance_state: "COMPLIANT",
        is_wipe_allowed: false
      },
      {
        id: "sample-motog54-03",
        model: "Moto G54 (Field Sample)",
        android_version: "13",
        management_mode: "FULLY_MANAGED",
        policy: "baseline",
        last_seen: "2026-10-15T08:45:00Z",
        compliance_state: "NON_COMPLIANT (alwaysOnVpnPackage)",
        is_wipe_allowed: true
      }
    ],
    policies: {
      baseline: {
        alwaysOnVpnPackage: {
          packageName: "com.wireguard.android",
          lockdownEnabled: true
        },
        usbFileTransferDisabled: true,
        playStoreMode: "WHITELIST",
        applications: [
          {
            packageName: "com.wireguard.android",
            installType: "AVAILABLE",
            defaultPermissionPolicy: "GRANT"
          }
        ],
        screenCaptureDisabled: true,
        factoryResetDisabled: true,
        passwordRequirements: {
          passwordMinimumLength: 6,
          passwordQuality: "NUMERIC_COMPLEX",
          passwordScope: "SCOPE_DEVICE"
        },
        statusReportingSettings: {
          applicationReportsEnabled: true,
          deviceSettingsEnabled: true,
          displayInfoEnabled: true,
          hardwareStatusEnabled: true,
          memoryInfoEnabled: true,
          networkInfoEnabled: true,
          powerManagementEventsEnabled: true,
          softwareInfoEnabled: true
        }
      },
      relaxed: {
        usbFileTransferDisabled: false,
        playStoreMode: "BLACKLIST",
        applications: [
          {
            packageName: "com.wireguard.android",
            installType: "AVAILABLE"
          },
          {
            packageName: "com.android.chrome",
            installType: "AVAILABLE"
          },
          {
            packageName: "com.google.android.calculator",
            installType: "AVAILABLE"
          }
        ],
        screenCaptureDisabled: false,
        factoryResetDisabled: false,
        passwordRequirements: {
          passwordMinimumLength: 4,
          passwordQuality: "NUMERIC",
          passwordScope: "SCOPE_DEVICE"
        },
        statusReportingSettings: {
          applicationReportsEnabled: true,
          deviceSettingsEnabled: true,
          displayInfoEnabled: true,
          hardwareStatusEnabled: true,
          memoryInfoEnabled: true,
          networkInfoEnabled: true,
          powerManagementEventsEnabled: true,
          softwareInfoEnabled: true
        }
      }
    },
    enrollment: {
      default_mode: "fully-managed",
      default_policy: "baseline",
      sample_expiration: "2026-10-15T10:30:00Z (1 hour sample token)",
      sample_output_file: "output/enroll-fully-managed-baseline.png (demo preview)"
    }
  };

  function loadSampleData(callback) {
    if (typeof window.fetch === "function" && window.location.protocol !== "file:") {
      fetch("./sample-data.json")
        .then(function (resp) {
          if (!resp.ok) {
            throw new Error("HTTP " + resp.status);
          }
          return resp.json();
        })
        .then(function (data) {
          callback(data);
        })
        .catch(function () {
          callback(FALLBACK_SAMPLE_DATA);
        });
    } else {
      callback(FALLBACK_SAMPLE_DATA);
    }
  }

  function showNotice(message) {
    var banner = document.getElementById("demo-action-notice");
    if (banner) {
      banner.textContent = message;
      banner.hidden = false;
    }
  }

  function buildSampleQrSvgDataUri(label) {
    var accentBlock = label.indexOf("work-profile") !== -1 ? "#0f766e" : "#0c1626";
    var svg =
      '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220" viewBox="0 0 220 220">' +
      '<rect width="220" height="220" fill="#ffffff"/>' +
      '<rect x="16" y="16" width="56" height="56" fill="none" stroke="' + accentBlock + '" stroke-width="8"/>' +
      '<rect x="30" y="30" width="28" height="28" fill="' + accentBlock + '"/>' +
      '<rect x="148" y="16" width="56" height="56" fill="none" stroke="' + accentBlock + '" stroke-width="8"/>' +
      '<rect x="162" y="30" width="28" height="28" fill="' + accentBlock + '"/>' +
      '<rect x="16" y="148" width="56" height="56" fill="none" stroke="' + accentBlock + '" stroke-width="8"/>' +
      '<rect x="30" y="162" width="28" height="28" fill="' + accentBlock + '"/>' +
      '<rect x="88" y="20" width="12" height="12" fill="' + accentBlock + '"/>' +
      '<rect x="112" y="20" width="12" height="24" fill="' + accentBlock + '"/>' +
      '<rect x="88" y="44" width="24" height="12" fill="' + accentBlock + '"/>' +
      '<rect x="88" y="68" width="12" height="24" fill="' + accentBlock + '"/>' +
      '<rect x="112" y="80" width="24" height="12" fill="' + accentBlock + '"/>' +
      '<rect x="20" y="88" width="24" height="12" fill="' + accentBlock + '"/>' +
      '<rect x="56" y="88" width="20" height="20" fill="' + accentBlock + '"/>' +
      '<rect x="88" y="100" width="24" height="24" fill="' + accentBlock + '"/>' +
      '<rect x="124" y="104" width="12" height="24" fill="' + accentBlock + '"/>' +
      '<rect x="148" y="88" width="24" height="12" fill="' + accentBlock + '"/>' +
      '<rect x="184" y="88" width="20" height="24" fill="' + accentBlock + '"/>' +
      '<rect x="20" y="116" width="12" height="20" fill="' + accentBlock + '"/>' +
      '<rect x="44" y="120" width="24" height="12" fill="' + accentBlock + '"/>' +
      '<rect x="88" y="136" width="12" height="24" fill="' + accentBlock + '"/>' +
      '<rect x="112" y="140" width="24" height="12" fill="' + accentBlock + '"/>' +
      '<rect x="148" y="124" width="20" height="20" fill="' + accentBlock + '"/>' +
      '<rect x="180" y="128" width="24" height="12" fill="' + accentBlock + '"/>' +
      '<rect x="88" y="172" width="24" height="12" fill="' + accentBlock + '"/>' +
      '<rect x="124" y="164" width="12" height="28" fill="' + accentBlock + '"/>' +
      '<rect x="148" y="156" width="24" height="24" fill="' + accentBlock + '"/>' +
      '<rect x="184" y="168" width="20" height="28" fill="' + accentBlock + '"/>' +
      '<text x="110" y="213" text-anchor="middle" font-family="Segoe UI, sans-serif" font-size="10" fill="#134e4a">DEMO QR (' +
      label +
      ")</text>" +
      "</svg>";
    return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
  }

  function initDevicesPage(data) {
    var table = document.getElementById("devices-table");
    if (!table) {
      return;
    }

    var refreshBtn = document.getElementById("refresh-devices-btn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        showNotice(
          "Demo data refreshed from demo/sample-data.json (" +
            data.devices.length +
            " sample devices loaded)."
        );
      });
    }

    document.querySelectorAll(".inline-switch-form").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        var deviceId = form.getAttribute("data-device-id") || "";
        var select = form.querySelector('select[name="policy_name"]');
        var chosenPolicy = select ? select.value : "baseline";
        var row = document.querySelector('tr[data-device-id="' + deviceId + '"]');
        if (row) {
          var activeCell = row.querySelector(".active-policy-tag");
          if (activeCell) {
            activeCell.textContent = chosenPolicy;
          }
        }
        showNotice(
          "Demo mode: switched sample device '" +
            deviceId +
            "' to policy '" +
            chosenPolicy +
            "' (in-memory preview only; no Google API call)."
        );
      });
    });
  }

  function initPoliciesPage(data) {
    var form = document.getElementById("policy-edit-form");
    if (!form) {
      return;
    }

    var policies = JSON.parse(JSON.stringify(data.policies));
    var currentPolicyId = "baseline";

    var params = new URLSearchParams(window.location.search);
    var requestedPolicy = params.get("policy");
    if (requestedPolicy && policies[requestedPolicy]) {
      currentPolicyId = requestedPolicy;
    }

    var policyIdInput = document.getElementById("policy_id");
    var headingCode = document.getElementById("editing-policy-code");
    var diskHeaderCode = document.getElementById("disk-policy-code");
    var usbEl = document.getElementById("usb_file_transfer_disabled");
    var screenEl = document.getElementById("screen_capture_disabled");
    var resetEl = document.getElementById("factory_reset_disabled");
    var whitelistEl = document.getElementById("play_store_whitelist_only");
    var vpnEnabledEl = document.getElementById("vpn_enabled");
    var vpnPkgEl = document.getElementById("vpn_package");
    var vpnLockEl = document.getElementById("vpn_lockdown");
    var pwLenEl = document.getElementById("password_min_length");
    var pwQualEl = document.getElementById("password_quality");
    var allowedAppsEl = document.getElementById("allowed_packages");
    var jsonPreviewEl = document.getElementById("policy-json-preview");

    var chipUsb = document.getElementById("chip-usb");
    var chipScreen = document.getElementById("chip-screen");
    var chipPlay = document.getElementById("chip-play");
    var chipVpn = document.getElementById("chip-vpn");

    function populateFormFromPolicy(polId) {
      currentPolicyId = polId;
      var pol = policies[polId] || policies.baseline;
      if (policyIdInput) policyIdInput.value = polId;
      if (headingCode) headingCode.textContent = polId;
      if (diskHeaderCode) diskHeaderCode.textContent = "policies/" + polId + ".json";

      var vpnObj = pol.alwaysOnVpnPackage || null;
      var vpnOn = Boolean(vpnObj && vpnObj.packageName);
      var vpnPkg = vpnOn ? vpnObj.packageName : "com.wireguard.android";
      var vpnLock = Boolean(vpnOn && vpnObj.lockdownEnabled);

      if (usbEl) usbEl.checked = Boolean(pol.usbFileTransferDisabled);
      if (screenEl) screenEl.checked = Boolean(pol.screenCaptureDisabled);
      if (resetEl) resetEl.checked = Boolean(pol.factoryResetDisabled);
      if (whitelistEl) whitelistEl.checked = pol.playStoreMode === "WHITELIST";
      if (vpnEnabledEl) vpnEnabledEl.checked = vpnOn;
      if (vpnPkgEl) vpnPkgEl.value = vpnPkg;
      if (vpnLockEl) vpnLockEl.checked = vpnLock;

      var pw = pol.passwordRequirements || {};
      if (pwLenEl) pwLenEl.value = String(pw.passwordMinimumLength || 6);
      if (pwQualEl) pwQualEl.value = pw.passwordQuality || "NUMERIC";

      var pkgs = (pol.applications || []).map(function (a) {
        return a.packageName;
      });
      if (allowedAppsEl) allowedAppsEl.value = pkgs.join("\n");

      document.querySelectorAll(".policy-item-link").forEach(function (link) {
        var linkPol = link.getAttribute("data-policy-id");
        if (linkPol === polId) {
          link.classList.add("active");
        } else {
          link.classList.remove("active");
        }
      });

      syncPreviewFromInputs();
    }

    function buildPolicyObjectFromInputs() {
      var base = JSON.parse(
        JSON.stringify(policies[currentPolicyId] || policies.baseline)
      );
      var vpnOn = vpnEnabledEl ? vpnEnabledEl.checked : false;
      var vpnPkg = vpnPkgEl ? vpnPkgEl.value.trim() : "com.wireguard.android";
      var vpnLock = vpnLockEl ? vpnLockEl.checked : false;

      if (vpnOn && vpnPkg) {
        base.alwaysOnVpnPackage = {
          packageName: vpnPkg,
          lockdownEnabled: vpnLock
        };
      } else {
        delete base.alwaysOnVpnPackage;
      }

      base.usbFileTransferDisabled = usbEl ? usbEl.checked : false;
      base.screenCaptureDisabled = screenEl ? screenEl.checked : false;
      base.factoryResetDisabled = resetEl ? resetEl.checked : false;
      base.playStoreMode =
        whitelistEl && whitelistEl.checked ? "WHITELIST" : "BLACKLIST";

      base.passwordRequirements = {
        passwordMinimumLength: pwLenEl ? parseInt(pwLenEl.value, 10) || 0 : 6,
        passwordQuality: pwQualEl ? pwQualEl.value : "NUMERIC",
        passwordScope: "SCOPE_DEVICE"
      };

      var rawLines = allowedAppsEl ? allowedAppsEl.value.split(/\r?\n/) : [];
      var pkgs = rawLines
        .map(function (s) {
          return s.trim();
        })
        .filter(Boolean);
      if (vpnOn && vpnPkg && pkgs.indexOf(vpnPkg) === -1) {
        pkgs.unshift(vpnPkg);
      }
      base.applications = pkgs.map(function (p) {
        var entry = { packageName: p, installType: "AVAILABLE" };
        if (vpnOn && p === vpnPkg) {
          entry.defaultPermissionPolicy = "GRANT";
        }
        return entry;
      });

      return base;
    }

    function syncPreviewFromInputs() {
      var updated = buildPolicyObjectFromInputs();
      if (jsonPreviewEl) {
        jsonPreviewEl.textContent = JSON.stringify(updated, null, 2);
      }
      if (chipUsb) chipUsb.textContent = updated.usbFileTransferDisabled ? "Blocked" : "Allowed";
      if (chipScreen) chipScreen.textContent = updated.screenCaptureDisabled ? "Blocked" : "Allowed";
      if (chipPlay) chipPlay.textContent = updated.playStoreMode;
      if (chipVpn) {
        chipVpn.textContent = updated.alwaysOnVpnPackage
          ? updated.alwaysOnVpnPackage.packageName
          : "Off";
      }
    }

    document.querySelectorAll(".policy-item-link").forEach(function (link) {
      link.addEventListener("click", function (event) {
        event.preventDefault();
        var targetId = link.getAttribute("data-policy-id") || "baseline";
        populateFormFromPolicy(targetId);
      });
    });

    form.addEventListener("change", syncPreviewFromInputs);
    form.addEventListener("input", syncPreviewFromInputs);

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var saveId =
        policyIdInput && policyIdInput.value.trim()
          ? policyIdInput.value.trim()
          : currentPolicyId;
      policies[saveId] = buildPolicyObjectFromInputs();
      syncPreviewFromInputs();
      showNotice(
        "Demo mode: updated policy '" +
          saveId +
          ".json' in browser memory (no disk write or Google API upload in static demo mode)."
      );
    });

    populateFormFromPolicy(currentPolicyId);
  }

  function initEnrollPage() {
    var form = document.getElementById("enroll-form");
    var qrImg = document.getElementById("enrollment-qr-img");
    if (!form || !qrImg) {
      return;
    }

    var modeSelect = document.getElementById("mode");
    var policySelect = document.getElementById("policy_name");
    var modeOut = document.getElementById("demo-enroll-mode");
    var policyOut = document.getElementById("demo-enroll-policy");
    var fileOut = document.getElementById("demo-enroll-file");

    function updateEnrollmentPreview(showBanner) {
      var modeVal = modeSelect ? modeSelect.value : "fully-managed";
      var polVal = policySelect ? policySelect.value : "baseline";
      qrImg.src = buildSampleQrSvgDataUri(modeVal + " / " + polVal);
      if (modeOut) modeOut.textContent = modeVal;
      if (policyOut) {
        policyOut.textContent = "enterprises/DEMO_SAMPLE_00/policies/" + polVal;
      }
      if (fileOut) {
        fileOut.textContent =
          "output/enroll-" + modeVal + "-" + polVal + ".png (sample preview)";
      }
      if (showBanner) {
        showNotice(
          "Demo mode: generated sample QR preview for mode '" +
            modeVal +
            "' with policy '" +
            polVal +
            "'."
        );
      }
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      updateEnrollmentPreview(true);
    });

    updateEnrollmentPreview(false);
  }

  loadSampleData(function (data) {
    initDevicesPage(data);
    initPoliciesPage(data);
    initEnrollPage(data);
  });
})();
