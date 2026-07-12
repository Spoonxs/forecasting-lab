/* The motion layer (P9) — one kill-switch, restrained by design.
 *
 * Every animated surface on the platform runs through here. Motion is OFF
 * whenever prefers-reduced-motion asks for it OR the user flips the persisted
 * toggle (localStorage 'flab_motion' = 'off'). Content is never JS-gated:
 * everything this file touches is already server-rendered and readable — we
 * only add the entrance. Data is never invented: counters ease toward the
 * number already printed in the DOM.
 */
(function () {
  "use strict";
  var EASE = "cubic-bezier(.7,0,.2,1)"; // the Sakura curve: fast out, soft land

  function motionOff() {
    try {
      if (localStorage.getItem("flab_motion") === "off") return true;
    } catch (e) { /* storage blocked: fall through to the media query */ }
    return window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function setMotion(on) {
    try { localStorage.setItem("flab_motion", on ? "on" : "off"); } catch (e) {}
    document.documentElement.classList.toggle("motion-off", !on);
    if (!on) {
      // a LIVE switch-off must never leave content hidden or frames running:
      // reveal everything instantly; in-flight callbacks self-gate below
      document.querySelectorAll("[data-reveal]").forEach(function (el) {
        el.style.transition = "none";
        el.style.opacity = "1";
        el.style.transform = "none";
      });
    }
  }

  // ---- reveals: elements marked data-reveal slide+fade in once visible ----
  function reveals() {
    var els = document.querySelectorAll("[data-reveal]");
    if (!els.length || !("IntersectionObserver" in window)) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target;
        // self-gate (Codex review): a live kill-switch flip stops the show
        el.style.transition = motionOff() ? "none"
          : "opacity .3s " + EASE + ", transform .3s " + EASE;
        el.style.opacity = "1";
        el.style.transform = "none";
        io.unobserve(el);
      });
    }, { threshold: 0.15 });
    els.forEach(function (el) {
      el.style.opacity = "0";
      el.style.transform = "translateY(14px)";
      io.observe(el);
    });
  }

  // ---- counters: ease to the value ALREADY in the DOM (never invented) ----
  function counters() {
    document.querySelectorAll("[data-count]").forEach(function (el) {
      var raw = el.textContent;
      var m = raw.match(/-?\d[\d,]*\.?\d*/);
      if (!m) return;
      var target = parseFloat(m[0].replace(/,/g, ""));
      if (!isFinite(target)) return;
      var prefix = raw.slice(0, m.index), suffix = raw.slice(m.index + m[0].length);
      var decimals = (m[0].split(".")[1] || "").length;
      var t0 = null, DUR = 300; // <=300ms: motion never blocks reading
      function frame(ts) {
        if (motionOff()) { el.textContent = raw; return; } // live kill-switch
        if (t0 === null) t0 = ts;
        var p = Math.min(1, (ts - t0) / DUR);
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = prefix + (target * eased).toFixed(decimals) + suffix;
        if (p < 1) requestAnimationFrame(frame);
        else el.textContent = raw; // land EXACTLY on the printed truth
      }
      requestAnimationFrame(frame);
    });
  }

  // ---- gauge sweeps: dials marked data-sweep animate their arc dash ----
  function sweeps() {
    document.querySelectorAll("[data-sweep]").forEach(function (el) {
      var final_ = el.getAttribute("stroke-dasharray");
      if (!final_) return;
      el.style.transition = "none";
      var parts = final_.split(/[ ,]+/);
      el.setAttribute("stroke-dasharray", "0 " + (parseFloat(parts[1]) || 100));
      requestAnimationFrame(function () {
        el.style.transition = "stroke-dasharray .3s " + EASE;
        el.setAttribute("stroke-dasharray", final_);
      });
    });
  }

  // ---- the public surface ----
  window.flabMotion = { off: motionOff, set: setMotion, ease: EASE };

  if (motionOff()) {
    document.documentElement.classList.add("motion-off");
    return; // the kill-switch kills EVERYTHING — no observers, no frames
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      reveals(); counters(); sweeps();
    });
  } else {
    reveals(); counters(); sweeps();
  }
})();
