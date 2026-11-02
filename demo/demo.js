/* Sandstorm Secure static demo (Milestone M6: DM-01 through DM-04).
 * Reads sample records from sample-data.js (works from file:// and any static host).
 * Nothing leaves the browser: no Google API calls and no network requests.
 * Runs before ui.js initialises (end of body), so the rows it builds get menus and icons.
 */
(function () {
  "use strict";

  var data = window.SANDSTORM_DEMO_DATA;
  if (!data) {
    return;
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "text") {
        node.textContent = attrs[key];
      } else {
        node.setAttribute(key, attrs[key]);
      }
    });
    (children || []).forEach(function (child) {
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }

  function icon(name) {
    return el("span", { "class": "icon", "data-icon": name });
  }

  function toast(message) {
    if (window.SandstormUI) {
      window.SandstormUI.toast(message, "success");
    }
  }

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function formatTimestamp(raw) {
    var match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(raw || "");
    if (!match) {
      return raw;
    }
    return match[3] + " " + MONTHS[parseInt(match[2], 10) - 1] + " " + match[1] + ", " + match[4] + ":" + match[5] + " UTC";
  }

  function complianceView(state) {
    var detailMatch = /\(([^)]*)\)$/.exec(state);
    var detail = detailMatch ? detailMatch[1] : "";
    if (state.indexOf("NON_COMPLIANT") === 0) {
      return { tone: "danger", label: "Not compliant", detail: detail };
    }
    if (state.indexOf("COMPLIANT") === 0) {
      return { tone: "success", label: "Compliant", detail: detail };
    }
    return { tone: "", label: "Not reported", detail: detail };
  }

  function setText(id, value) {
    var node = document.getElementById(id);
    if (node) {
      node.textContent = value;
    }
  }

  document.querySelectorAll("[data-demo-version]").forEach(function (node) {
    node.textContent = "Sandstorm Secure v" + data.version;
  });

  // ---------------------------------------------------------------- Devices

  function buildDeviceRow(dev, policyNames) {
    var compliance = complianceView(dev.compliance_state);
    var pill = el("span", { "class": "pill compliance-pill" + (compliance.tone ? " pill-" + compliance.tone : ""), text: compliance.label });
    var complianceCell = el("div", {}, [pill]);
    if (compliance.detail) {
      complianceCell.appendChild(el("span", { "class": "cell-detail", text: compliance.detail }));
    }

    var select = el("select", { "class": "select", name: "policy_name", "aria-label": "Policy for " + dev.id });
    policyNames.forEach(function (name) {
      var option = el("option", { value: name, text: name });
      if (name === dev.policy) {
        option.selected = true;
      }
      select.appendChild(option);
    });
    var switchForm = el("form", { "class": "inline-form inline-switch-form", "data-device-id": dev.id }, [
      select,
      el("button", { type: "submit", "class": "btn btn-secondary btn-sm", text: "Apply" })
    ]);

    // DM-04: wipe is always disabled in the demo, even for allow-listed sample devices.
    var wipeNote = dev.is_wipe_allowed
      ? "Disabled in demo mode. In the real dashboard you type the device ID to confirm."
      : "Not in wipe allow-list. Also disabled in demo mode.";
    var wipeButton = el("button", {
      type: "button",
      "class": "btn btn-danger-outline btn-sm wipe-demo-btn",
      disabled: "",
      "aria-disabled": "true",
      title: "Wipe is disabled in the demo"
    }, [icon("trash-2"), "Wipe device…"]);

    var menu = el("details", { "class": "menu row-menu" }, [
      el("summary", { "class": "btn btn-ghost btn-icon btn-sm", "aria-label": "Actions for " + dev.id }, [icon("ellipsis")]),
      el("div", { "class": "menu-panel" }, [
        el("div", { "class": "menu-section" }, [
          el("p", { "class": "menu-heading", text: "Change policy" }),
          switchForm
        ]),
        el("div", { "class": "menu-section danger-zone" }, [
          el("p", { "class": "menu-heading", text: "Danger zone" }),
          el("p", { "class": "danger-note", text: wipeNote }),
          el("div", {}, [wipeButton])
        ])
      ])
    ]);

    switchForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var row = switchForm.closest("tr");
      row.querySelector(".active-policy-tag").textContent = select.value;
      menu.open = false;
      toast("Demo: moved " + dev.id + " to policy '" + select.value + "'. Nothing was sent to Google.");
    });

    return el("tr", { "data-device-id": dev.id }, [
      el("td", { "class": "cell-primary", "data-label": "Device" }, [
        el("div", { "class": "device-cell" }, [
          el("span", { "class": "device-avatar" }, [icon("smartphone")]),
          el("div", {}, [
            el("span", { "class": "device-name", text: dev.model }),
            el("span", { "class": "device-id", text: dev.id })
          ])
        ])
      ]),
      el("td", { "data-label": "Android", "class": "num", text: dev.android_version }),
      el("td", { "data-label": "Policy" }, [el("span", { "class": "tag active-policy-tag", text: dev.policy })]),
      el("td", { "data-label": "Compliance" }, [complianceCell]),
      el("td", { "data-label": "Last seen", "class": "num" }, [
        el("time", { datetime: dev.last_seen, title: dev.last_seen, text: formatTimestamp(dev.last_seen) })
      ]),
      el("td", { "class": "col-actions" }, [menu])
    ]);
  }

  function initDevicesPage() {
    var tbody = document.getElementById("devices-tbody");
    if (!tbody) {
      return;
    }
    var policyNames = Object.keys(data.policies).sort();
    data.devices.forEach(function (dev) {
      tbody.appendChild(buildDeviceRow(dev, policyNames));
    });

    var tones = data.devices.map(function (dev) {
      return complianceView(dev.compliance_state).tone;
    });
    setText("stat-total", String(data.devices.length));
    setText("stat-compliant", String(tones.filter(function (t) { return t === "success"; }).length));
    setText("stat-non-compliant", String(tones.filter(function (t) { return t === "danger"; }).length));
    setText("stat-last-refresh", data.last_refresh);

    var refreshBtn = document.getElementById("refresh-devices-btn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        toast("Demo: reloaded " + data.devices.length + " sample devices. Nothing was sent to Google.");
      });
    }
  }

  // --------------------------------------------------------------- Policies

  function initPoliciesPage() {
    var form = document.getElementById("policy-edit-form");
    if (!form) {
      return;
    }

    var policies = JSON.parse(JSON.stringify(data.policies));
    var params = new URLSearchParams(window.location.search);
    var currentPolicyId = policies[params.get("policy")] ? params.get("policy") : "baseline";

    function byId(id) {
      return document.getElementById(id);
    }

    var fields = {
      policyId: byId("policy_id"),
      usb: byId("usb_file_transfer_disabled"),
      screen: byId("screen_capture_disabled"),
      reset: byId("factory_reset_disabled"),
      allowList: byId("play_store_whitelist_only"),
      vpn: byId("vpn_enabled"),
      vpnPackage: byId("vpn_package"),
      vpnLock: byId("vpn_lockdown"),
      pwLength: byId("password_min_length"),
      pwQuality: byId("password_quality"),
      apps: byId("allowed_packages"),
      preview: byId("policy-json-preview")
    };

    function fillForm(policyId) {
      currentPolicyId = policyId;
      var pol = policies[policyId] || policies.baseline;
      var vpnObj = pol.alwaysOnVpnPackage || null;
      var vpnOn = Boolean(vpnObj && vpnObj.packageName);
      var pw = pol.passwordRequirements || {};

      fields.policyId.value = policyId;
      fields.usb.checked = Boolean(pol.usbFileTransferDisabled);
      fields.screen.checked = Boolean(pol.screenCaptureDisabled);
      fields.reset.checked = Boolean(pol.factoryResetDisabled);
      fields.allowList.checked = pol.playStoreMode === "WHITELIST";
      fields.vpn.checked = vpnOn;
      fields.vpnPackage.value = vpnOn ? vpnObj.packageName : "com.wireguard.android";
      fields.vpnLock.checked = Boolean(vpnOn && vpnObj.lockdownEnabled);
      fields.pwLength.value = String(pw.passwordMinimumLength || 0);
      fields.pwQuality.value = pw.passwordQuality || "NUMERIC";
      fields.apps.value = (pol.applications || []).map(function (app) {
        return app.packageName;
      }).join("\n");

      document.querySelectorAll(".policy-item-link").forEach(function (link) {
        var active = link.getAttribute("data-policy-id") === policyId;
        link.classList.toggle("active", active);
        if (active) {
          link.setAttribute("aria-current", "page");
        } else {
          link.removeAttribute("aria-current");
        }
      });
      setText("disk-policy-code", "policies/" + policyId + ".json");
      syncPreview();
    }

    // Same rules as amapi.save_policy_from_toggles, so the preview matches the real app.
    function policyFromForm() {
      var base = JSON.parse(JSON.stringify(policies[currentPolicyId] || policies.baseline));
      var vpnOn = fields.vpn.checked;
      var vpnPkg = fields.vpnPackage.value.trim();

      if (vpnOn && vpnPkg) {
        base.alwaysOnVpnPackage = { packageName: vpnPkg, lockdownEnabled: fields.vpnLock.checked };
      } else {
        delete base.alwaysOnVpnPackage;
      }
      base.usbFileTransferDisabled = fields.usb.checked;
      base.playStoreMode = fields.allowList.checked ? "WHITELIST" : "BLACKLIST";
      base.screenCaptureDisabled = fields.screen.checked;
      base.factoryResetDisabled = fields.reset.checked;
      base.passwordRequirements = {
        passwordMinimumLength: parseInt(fields.pwLength.value, 10) || 0,
        passwordQuality: fields.pwQuality.value,
        passwordScope: "SCOPE_DEVICE"
      };

      var packages = fields.apps.value.split(/\r?\n/).map(function (s) {
        return s.trim();
      }).filter(Boolean);
      if (vpnOn && vpnPkg && packages.indexOf(vpnPkg) === -1) {
        packages.unshift(vpnPkg);
      }
      base.applications = packages.map(function (pkg) {
        var entry = { packageName: pkg, installType: "AVAILABLE" };
        if (vpnOn && pkg === vpnPkg) {
          entry.defaultPermissionPolicy = "GRANT";
        }
        return entry;
      });
      return base;
    }

    function syncPreview() {
      fields.preview.textContent = JSON.stringify(policyFromForm(), null, 2);
    }

    document.querySelectorAll(".policy-item-link").forEach(function (link) {
      link.addEventListener("click", function (event) {
        event.preventDefault();
        fillForm(link.getAttribute("data-policy-id") || "baseline");
        window.SandstormUI.markClean(form);
      });
    });

    form.addEventListener("input", syncPreview);
    form.addEventListener("change", syncPreview);
    // A native reset restores the HTML defaults (baseline), so refill the open policy.
    form.addEventListener("reset", function () {
      window.setTimeout(function () {
        fillForm(currentPolicyId);
        window.SandstormUI.markClean(form);
      }, 0);
    });
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var saveId = fields.policyId.value.trim() || currentPolicyId;
      policies[saveId] = policyFromForm();
      currentPolicyId = saveId;
      syncPreview();
      window.SandstormUI.markClean(form);
      toast("Demo: saved '" + saveId + ".json' in this browser tab only. Nothing was written or uploaded.");
    });

    fillForm(currentPolicyId);
  }

  // ----------------------------------------------------------------- Enroll

  function sampleQrDataUri() {
    // A fixed decorative pattern, not a real QR code: the demo has no enrollment token.
    var cells = [
      [88, 20, 12, 12], [112, 20, 12, 24], [88, 44, 24, 12], [88, 68, 12, 24], [112, 80, 24, 12],
      [20, 88, 24, 12], [56, 88, 20, 20], [88, 100, 24, 24], [124, 104, 12, 24], [148, 88, 24, 12],
      [184, 88, 20, 24], [20, 116, 12, 20], [44, 120, 24, 12], [88, 136, 12, 24], [112, 140, 24, 12],
      [148, 124, 20, 20], [180, 128, 24, 12], [88, 172, 24, 12], [124, 164, 12, 28], [148, 156, 24, 24],
      [184, 168, 20, 28]
    ];
    var ink = "#0f172a";
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220" viewBox="0 0 220 220">' +
      '<rect width="220" height="220" fill="#ffffff"/>';
    [[16, 16], [148, 16], [16, 148]].forEach(function (corner) {
      svg += '<rect x="' + corner[0] + '" y="' + corner[1] + '" width="56" height="56" rx="6" fill="none" stroke="' + ink + '" stroke-width="8"/>' +
        '<rect x="' + (corner[0] + 14) + '" y="' + (corner[1] + 14) + '" width="28" height="28" rx="3" fill="' + ink + '"/>';
    });
    cells.forEach(function (c) {
      svg += '<rect x="' + c[0] + '" y="' + c[1] + '" width="' + c[2] + '" height="' + c[3] + '" fill="' + ink + '"/>';
    });
    svg += "</svg>";
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }

  function initEnrollPage() {
    var form = document.getElementById("enroll-form");
    if (!form) {
      return;
    }
    var result = document.getElementById("enrollment-result");
    var howTo = document.getElementById("enroll-how-to");

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var checked = form.querySelector('input[name="mode"]:checked');
      var mode = checked ? checked.value : "fully-managed";
      var policy = document.getElementById("policy_name").value;
      var fileName = "enroll-" + mode + "-" + policy + ".png";

      document.getElementById("enrollment-qr-img").src = sampleQrDataUri();
      setText("demo-enroll-mode", mode);
      setText("demo-enroll-policy", policy);
      setText("demo-enroll-file", fileName);
      setText("enrollment-expiry", formatTimestamp(data.enrollment.sample_expiration) + " (sample)");
      result.hidden = false;
      if (howTo) {
        howTo.hidden = true;
      }

      var steps = document.querySelectorAll("#enroll-stepper .step");
      steps.forEach(function (step, index) {
        var isLast = index === steps.length - 1;
        step.classList.toggle("is-done", !isLast);
        step.classList.toggle("is-current", isLast);
        if (isLast) {
          step.setAttribute("aria-current", "step");
        } else {
          step.removeAttribute("aria-current");
          var indexEl = step.querySelector(".step-index");
          indexEl.innerHTML = "";
          indexEl.appendChild(icon("check"));
          window.SandstormUI.renderIcons(indexEl);
        }
      });
      toast("Demo: made a sample QR preview for " + mode + " / " + policy + ". It cannot be scanned.");
    });
  }

  // --------------------------------------------------------------- Settings

  function initSettingsPage() {
    var keyInput = document.getElementById("sa_key_path");
    if (!keyInput) {
      return;
    }
    keyInput.value = data.settings.sa_key_path;
    setText("key-project-id", data.settings.project_id);
    setText("key-client-email", data.settings.client_email);
    setText("check-key-email", data.settings.client_email);
    setText("check-enterprise-name", data.settings.enterprise_name);

    document.getElementById("test-connection-btn").addEventListener("click", function () {
      toast("Demo: no Google call was made. In the real dashboard this makes one read-only call.");
    });
    document.getElementById("key-form").addEventListener("submit", function (event) {
      event.preventDefault();
      toast("Demo: the path was not saved. The real dashboard checks the file and saves the path.");
    });
  }

  initDevicesPage();
  initPoliciesPage();
  initEnrollPage();
  initSettingsPage();
})();
