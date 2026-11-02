/* Sandstorm Secure shared UI script.
 * One file for the dashboard, the demo and the landing page. Keep the copies in
 * demo/ and landing/ identical (run scripts/sync_shared_assets.py).
 * Icons: Lucide (ISC licence, see vendor/LICENSE-lucide.txt). No network requests.
 */
(function () {
  "use strict";

  var THEME_KEY = "sandstorm-theme";
  var root = document.documentElement;

  // Apply a saved theme before the body paints, so the page does not flash.
  try {
    var savedTheme = window.localStorage.getItem(THEME_KEY);
    if (savedTheme === "light" || savedTheme === "dark") {
      root.setAttribute("data-theme", savedTheme);
    }
  } catch (err) {
    // Private mode or blocked storage: follow the system theme.
  }

  var ICONS = {
    "smartphone": "<rect width=\"14\" height=\"20\" x=\"5\" y=\"2\" rx=\"2\" ry=\"2\"/> <path d=\"M12 18h.01\"/>",
    "shield-check": "<path d=\"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z\"/> <path d=\"m9 12 2 2 4-4\"/>",
    "qr-code": "<rect width=\"5\" height=\"5\" x=\"3\" y=\"3\" rx=\"1\"/> <rect width=\"5\" height=\"5\" x=\"16\" y=\"3\" rx=\"1\"/> <rect width=\"5\" height=\"5\" x=\"3\" y=\"16\" rx=\"1\"/> <path d=\"M21 16h-3a2 2 0 0 0-2 2v3\"/> <path d=\"M21 21v.01\"/> <path d=\"M12 7v3a2 2 0 0 1-2 2H7\"/> <path d=\"M3 12h.01\"/> <path d=\"M12 3h.01\"/> <path d=\"M12 16v.01\"/> <path d=\"M16 12h1\"/> <path d=\"M21 12v.01\"/> <path d=\"M12 21v-1\"/>",
    "settings": "<path d=\"M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915\"/> <circle cx=\"12\" cy=\"12\" r=\"3\"/>",
    "sun": "<circle cx=\"12\" cy=\"12\" r=\"4\"/> <path d=\"M12 2v2\"/> <path d=\"M12 20v2\"/> <path d=\"m4.93 4.93 1.41 1.41\"/> <path d=\"m17.66 17.66 1.41 1.41\"/> <path d=\"M2 12h2\"/> <path d=\"M20 12h2\"/> <path d=\"m6.34 17.66-1.41 1.41\"/> <path d=\"m19.07 4.93-1.41 1.41\"/>",
    "moon": "<path d=\"M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401\"/>",
    "refresh-cw": "<path d=\"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8\"/> <path d=\"M21 3v5h-5\"/> <path d=\"M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16\"/> <path d=\"M8 16H3v5\"/>",
    "ellipsis": "<circle cx=\"12\" cy=\"12\" r=\"1\"/> <circle cx=\"19\" cy=\"12\" r=\"1\"/> <circle cx=\"5\" cy=\"12\" r=\"1\"/>",
    "triangle-alert": "<path d=\"m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3\"/> <path d=\"M12 9v4\"/> <path d=\"M12 17h.01\"/>",
    "circle-check": "<circle cx=\"12\" cy=\"12\" r=\"10\"/> <path d=\"m16 9-5.5 5.5L8 12\"/>",
    "circle-x": "<circle cx=\"12\" cy=\"12\" r=\"10\"/> <path d=\"m15 9-6 6\"/> <path d=\"m9 9 6 6\"/>",
    "info": "<circle cx=\"12\" cy=\"12\" r=\"10\"/> <path d=\"M12 16v-4\"/> <path d=\"M12 8h.01\"/>",
    "x": "<path d=\"M18 6 6 18\"/> <path d=\"m6 6 12 12\"/>",
    "menu": "<path d=\"M4 5h16\"/> <path d=\"M4 12h16\"/> <path d=\"M4 19h16\"/>",
    "download": "<path d=\"M12 15V3\"/> <path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\"/> <path d=\"m7 10 5 5 5-5\"/>",
    "plug": "<path d=\"M12 22v-5\"/> <path d=\"M15 8V2\"/> <path d=\"M17 8a1 1 0 0 1 1 1v4a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1z\"/> <path d=\"M9 8V2\"/>",
    "key-round": "<path d=\"M2.586 17.414A2 2 0 0 0 2 18.828V21a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h1a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h.172a2 2 0 0 0 1.414-.586l.814-.814a6.5 6.5 0 1 0-4-4z\"/> <circle cx=\"16.5\" cy=\"7.5\" r=\".5\" fill=\"currentColor\"/>",
    "upload": "<path d=\"M12 3v12\"/> <path d=\"m17 8-5-5-5 5\"/> <path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\"/>",
    "check": "<path d=\"M20 6 9 17l-5-5\"/>",
    "lock": "<rect width=\"18\" height=\"11\" x=\"3\" y=\"11\" rx=\"2\" ry=\"2\"/> <path d=\"M7 11V7a5 5 0 0 1 10 0v4\"/>",
    "eye": "<path d=\"M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0\"/> <circle cx=\"12\" cy=\"12\" r=\"3\"/>",
    "eye-off": "<path d=\"M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49\"/> <path d=\"M14.084 14.158a3 3 0 0 1-4.242-4.242\"/> <path d=\"M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143\"/> <path d=\"m2 2 20 20\"/>",
    "clock": "<circle cx=\"12\" cy=\"12\" r=\"10\"/> <path d=\"M12 6v6l4 2\"/>",
    "arrow-right": "<path d=\"M5 12h14\"/> <path d=\"m12 5 7 7-7 7\"/>",
    "layers": "<path d=\"M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z\"/> <path d=\"M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12\"/> <path d=\"M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17\"/>",
    "server": "<rect width=\"20\" height=\"8\" x=\"2\" y=\"2\" rx=\"2\" ry=\"2\"/> <rect width=\"20\" height=\"8\" x=\"2\" y=\"14\" rx=\"2\" ry=\"2\"/> <line x1=\"6\" x2=\"6.01\" y1=\"6\" y2=\"6\"/> <line x1=\"6\" x2=\"6.01\" y1=\"18\" y2=\"18\"/>",
    "usb": "<circle cx=\"10\" cy=\"7\" r=\"1\"/> <circle cx=\"4\" cy=\"20\" r=\"1\"/> <path d=\"M4.7 19.3 19 5\"/> <path d=\"m21 3-3 1 2 2Z\"/> <path d=\"M9.26 7.68 5 12l2 5\"/> <path d=\"m10 14 5 2 3.5-3.5\"/> <path d=\"m18 12 1-1 1 1-1 1Z\"/>",
    "camera-off": "<path d=\"M14.564 14.558a3 3 0 1 1-4.122-4.121\"/> <path d=\"m2 2 20 20\"/> <path d=\"M20 20H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1.997a2 2 0 0 0 .819-.175\"/> <path d=\"M9.695 4.024A2 2 0 0 1 10.004 4h3.993a2 2 0 0 1 1.76 1.05l.486.9A2 2 0 0 0 18.003 7H20a2 2 0 0 1 2 2v7.344\"/>",
    "rotate-ccw": "<path d=\"M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8\"/> <path d=\"M3 3v5h5\"/>",
    "package": "<path d=\"M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z\"/> <path d=\"M12 22V12\"/> <polyline points=\"3.29 7 12 12 20.71 7\"/> <path d=\"m7.5 4.27 9 5.15\"/>",
    "lock-keyhole": "<circle cx=\"12\" cy=\"16\" r=\"1\"/> <rect x=\"3\" y=\"10\" width=\"18\" height=\"12\" rx=\"2\"/> <path d=\"M7 10V7a5 5 0 0 1 10 0v3\"/>",
    "trash-2": "<path d=\"M10 11v6\"/> <path d=\"M14 11v6\"/> <path d=\"M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6\"/> <path d=\"M3 6h18\"/> <path d=\"M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2\"/>",
    "briefcase": "<path d=\"M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16\"/> <rect width=\"20\" height=\"14\" x=\"2\" y=\"6\" rx=\"2\"/>",
    "scan-line": "<path d=\"M3 7V5a2 2 0 0 1 2-2h2\"/> <path d=\"M17 3h2a2 2 0 0 1 2 2v2\"/> <path d=\"M21 17v2a2 2 0 0 1-2 2h-2\"/> <path d=\"M7 21H5a2 2 0 0 1-2-2v-2\"/> <path d=\"M7 12h10\"/>",
    "list-checks": "<path d=\"M13 5h8\"/> <path d=\"M13 12h8\"/> <path d=\"M13 19h8\"/> <path d=\"m3 17 2 2 4-4\"/> <path d=\"m3 7 2 2 4-4\"/>",
    "save": "<path d=\"M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z\"/> <path d=\"M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7\"/> <path d=\"M7 3v4a1 1 0 0 0 1 1h7\"/>",
    "chevron-right": "<path d=\"m9 18 6-6-6-6\"/>",
    "chevron-down": "<path d=\"m6 9 6 6 6-6\"/>",
    "external-link": "<path d=\"M15 3h6v6\"/> <path d=\"M10 14 21 3\"/> <path d=\"M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6\"/>",
    "mail": "<path d=\"m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7\"/> <rect x=\"2\" y=\"4\" width=\"20\" height=\"16\" rx=\"2\"/>",
    "globe-lock": "<path d=\"M15.686 15A14.5 14.5 0 0 1 12 22a14.5 14.5 0 0 1 0-20 10 10 0 1 0 9.542 13\"/> <path d=\"M2 12h8.5\"/> <path d=\"M20 6V4a2 2 0 1 0-4 0v2\"/> <rect width=\"8\" height=\"5\" x=\"14\" y=\"6\" rx=\"1\"/>",
    "shield": "<path d=\"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z\"/>",
    "monitor": "<rect width=\"20\" height=\"14\" x=\"2\" y=\"3\" rx=\"2\"/> <line x1=\"8\" x2=\"16\" y1=\"21\" y2=\"21\"/> <line x1=\"12\" x2=\"12\" y1=\"17\" y2=\"21\"/>",
    "circle-dashed": "<path d=\"M10.1 2.182a10 10 0 0 1 3.8 0\"/> <path d=\"M13.9 21.818a10 10 0 0 1-3.8 0\"/> <path d=\"M17.609 3.721a10 10 0 0 1 2.69 2.7\"/> <path d=\"M2.182 13.9a10 10 0 0 1 0-3.8\"/> <path d=\"M20.279 17.609a10 10 0 0 1-2.7 2.69\"/> <path d=\"M21.818 10.1a10 10 0 0 1 0 3.8\"/> <path d=\"M3.721 6.391a10 10 0 0 1 2.7-2.69\"/> <path d=\"M6.391 20.279a10 10 0 0 1-2.69-2.7\"/>",
    "file-json": "<path d=\"M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z\"/> <path d=\"M14 2v5a1 1 0 0 0 1 1h5\"/> <path d=\"M10 12a1 1 0 0 0-1 1v1a1 1 0 0 1-1 1 1 1 0 0 1 1 1v1a1 1 0 0 0 1 1\"/> <path d=\"M14 18a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1 1 1 0 0 1-1-1v-1a1 1 0 0 0-1-1\"/>",
    "ban": "<circle cx=\"12\" cy=\"12\" r=\"10\"/> <path d=\"M4.929 4.929 19.07 19.071\"/>",
    "user-round": "<circle cx=\"12\" cy=\"8\" r=\"5\"/> <path d=\"M20 21a8 8 0 0 0-16 0\"/>",
    "circle-help": "<circle cx=\"12\" cy=\"12\" r=\"10\"/> <path d=\"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3\"/> <path d=\"M12 17h.01\"/>"
  };

  function renderIcons(scope) {
    var nodes = (scope || document).querySelectorAll("[data-icon]:not([data-icon-done])");
    Array.prototype.forEach.call(nodes, function (node) {
      var body = ICONS[node.getAttribute("data-icon")];
      if (!body) {
        return;
      }
      node.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
        body +
        "</svg>";
      node.setAttribute("aria-hidden", "true");
      node.setAttribute("data-icon-done", "");
    });
  }

  function effectiveTheme() {
    var explicit = root.getAttribute("data-theme");
    if (explicit) {
      return explicit;
    }
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function syncThemeButtons() {
    var next = effectiveTheme() === "dark" ? "light" : "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.setAttribute("aria-label", "Switch to " + next + " theme");
      btn.setAttribute("title", "Switch to " + next + " theme");
    });
  }

  function initTheme() {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var next = effectiveTheme() === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", next);
        try {
          window.localStorage.setItem(THEME_KEY, next);
        } catch (err) {
          // Storage is blocked: the choice lasts until the page reloads.
        }
        syncThemeButtons();
      });
    });
    syncThemeButtons();
  }

  function initNavToggle() {
    document.querySelectorAll("[data-nav-toggle]").forEach(function (btn) {
      var target = document.getElementById(btn.getAttribute("aria-controls"));
      if (!target) {
        return;
      }
      btn.addEventListener("click", function () {
        var open = btn.getAttribute("aria-expanded") !== "true";
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        target.classList.toggle("is-open", open);
      });
    });
  }

  function dismissToast(toast) {
    toast.classList.add("is-leaving");
    window.setTimeout(function () {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 200);
  }

  function wireToast(toast) {
    var closeBtn = toast.querySelector("[data-toast-close]");
    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        dismissToast(toast);
      });
    }
    // Errors stay until the user closes them, so nobody misses a refusal.
    if (toast.classList.contains("toast-success")) {
      window.setTimeout(function () {
        dismissToast(toast);
      }, 8000);
    }
  }

  function toast(message, tone) {
    var region = document.getElementById("toast-region");
    if (!region) {
      return null;
    }
    var safeTone = tone === "error" ? "error" : "success";
    var el = document.createElement("div");
    el.className = "toast toast-" + safeTone;
    el.setAttribute("role", safeTone === "error" ? "alert" : "status");
    el.innerHTML =
      '<span class="icon toast-icon" data-icon="' +
      (safeTone === "error" ? "circle-x" : "circle-check") +
      '"></span><p class="toast-message"></p>' +
      '<button type="button" class="btn btn-ghost btn-icon btn-sm" data-toast-close aria-label="Close message">' +
      '<span class="icon" data-icon="x"></span></button>';
    el.querySelector(".toast-message").textContent = message;
    region.appendChild(el);
    renderIcons(el);
    wireToast(el);
    return el;
  }

  function initMenus() {
    var menus = document.querySelectorAll("details.menu");
    Array.prototype.forEach.call(menus, function (menu) {
      menu.addEventListener("toggle", function () {
        if (!menu.open) {
          return;
        }
        Array.prototype.forEach.call(menus, function (other) {
          if (other !== menu) {
            other.open = false;
          }
        });
      });
    });
    document.addEventListener("click", function (event) {
      Array.prototype.forEach.call(menus, function (menu) {
        if (menu.open && !menu.contains(event.target)) {
          menu.open = false;
        }
      });
    });
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") {
        return;
      }
      Array.prototype.forEach.call(menus, function (menu) {
        if (menu.open) {
          menu.open = false;
          var summary = menu.querySelector("summary");
          if (summary) {
            summary.focus();
          }
        }
      });
    });
  }

  var FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
  var openModalState = null;

  function closeModal() {
    if (!openModalState) {
      return;
    }
    var state = openModalState;
    openModalState = null;
    state.backdrop.hidden = true;
    document.removeEventListener("keydown", state.onKey, true);
    if (state.opener && typeof state.opener.focus === "function") {
      state.opener.focus();
    }
  }

  function openModal(backdrop, opener) {
    closeModal();
    backdrop.hidden = false;
    var dialog = backdrop.querySelector('[role="dialog"]') || backdrop;
    var onKey = function (event) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeModal();
        return;
      }
      if (event.key !== "Tab") {
        return;
      }
      var items = dialog.querySelectorAll(FOCUSABLE);
      if (!items.length) {
        return;
      }
      var first = items[0];
      var last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    openModalState = { backdrop: backdrop, opener: opener, onKey: onKey };
    document.addEventListener("keydown", onKey, true);
    var autofocus = dialog.querySelector("[data-autofocus]") || dialog.querySelector(FOCUSABLE);
    if (autofocus) {
      autofocus.focus();
    }
  }

  function initModals() {
    document.querySelectorAll(".modal-backdrop").forEach(function (backdrop) {
      backdrop.addEventListener("click", function (event) {
        if (event.target === backdrop) {
          closeModal();
        }
      });
      backdrop.querySelectorAll("[data-modal-close]").forEach(function (btn) {
        btn.addEventListener("click", closeModal);
      });
    });
  }

  function snapshotForm(form) {
    var pairs = [];
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.type === "submit" || el.type === "button") {
        return;
      }
      if (el.type === "checkbox" || el.type === "radio") {
        pairs.push(el.name + "=" + (el.checked ? el.value : ""));
      } else {
        pairs.push(el.name + "=" + el.value);
      }
    });
    return pairs.join("&");
  }

  function initDirtyForms() {
    document.querySelectorAll("form[data-dirty-bar]").forEach(function (form) {
      var bar = document.getElementById(form.getAttribute("data-dirty-bar"));
      if (!bar) {
        return;
      }
      var initial = snapshotForm(form);
      var update = function () {
        bar.hidden = snapshotForm(form) === initial;
      };
      form.addEventListener("input", update);
      form.addEventListener("change", update);
      form.addEventListener("reset", function () {
        window.setTimeout(function () {
          form.dispatchEvent(new Event("change", { bubbles: true }));
          update();
        }, 0);
      });
      form.sandstormMarkClean = function () {
        initial = snapshotForm(form);
        update();
      };
      update();
    });
  }

  window.SandstormUI = {
    renderIcons: renderIcons,
    toast: toast,
    openModal: openModal,
    closeModal: closeModal,
    markClean: function (form) {
      if (form && typeof form.sandstormMarkClean === "function") {
        form.sandstormMarkClean();
      }
    }
  };

  function init() {
    renderIcons(document);
    initTheme();
    initNavToggle();
    initMenus();
    initModals();
    initDirtyForms();
    document.querySelectorAll(".toast").forEach(wireToast);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
