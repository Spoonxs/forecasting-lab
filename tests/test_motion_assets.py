"""P9-1 — the vendored motion/3D libraries + the shared motion layer.

Pinned: the vendor bundle ships as package data (unmodified official dists,
licenses alongside) and copies verbatim into the site; the total landing JS
weight fits the 250KB-gzipped budget; motion.js has ONE kill-switch honoring
prefers-reduced-motion AND the persisted user toggle, counters land exactly
on the printed truth (never invented numbers), and nothing in it fetches or
gates content.
"""

from __future__ import annotations

import gzip
from importlib import resources

from forecasting_lab.dashboard.assets_pipe import (
    BUDGET_GZ_LANDING_JS,
    VENDOR_FILES,
    copy_assets,
)


def _asset(name: str) -> bytes:
    return (resources.files("forecasting_lab.dashboard") / "assets" / name).read_bytes()


def test_vendor_bundle_ships_with_licenses_and_copies(tmp_path):
    written = copy_assets(tmp_path)
    names = {p.name for p in written}
    assert set(VENDOR_FILES) | {"motion.js"} == names
    for p in written:
        assert p.stat().st_size > 0
    # licenses attribute the real terms
    gsap_lic = (tmp_path / "vendor" / "LICENSE-gsap.txt").read_text(encoding="utf-8")
    assert "gsap.com/standard-license" in gsap_lic and "UNMODIFIED" in gsap_lic
    three_lic = (tmp_path / "vendor" / "LICENSE-three.txt").read_text(encoding="utf-8")
    assert "MIT License" in three_lic
    # the vendored files are the official dists (their own headers say so)
    gsap = (tmp_path / "vendor" / "gsap.min.js").read_text(encoding="utf-8", errors="ignore")
    assert "GSAP 3.12.5" in gsap[:200] and "greensock" in gsap[:400].lower() or "gsap.com" in gsap[:200]


def test_landing_js_budget_holds_gzipped():
    total = sum(len(gzip.compress(_asset(f"vendor/{n}")))
                for n in VENDOR_FILES if n.endswith(".js"))
    total += len(gzip.compress(_asset("motion.js")))
    assert total < BUDGET_GZ_LANDING_JS, f"{total} gz exceeds the landing JS budget"


def test_motion_layer_has_one_kill_switch_and_never_invents_numbers():
    js = _asset("motion.js").decode("utf-8")
    assert "prefers-reduced-motion" in js
    assert "flab_motion" in js                           # the persisted user toggle
    assert js.count("motionOff") >= 2                    # checked before ANY work
    assert "return; // the kill-switch kills EVERYTHING" in js
    assert "el.textContent = raw" in js                  # counters land on the truth
    assert "cubic-bezier(.7,0,.2,1)" in js               # the Sakura curve
    for banned in ("fetch(", "XMLHttpRequest", "http://", "https://",
                   "innerHTML"):
        assert banned not in js                          # no fetches, no injection
    # Codex review: a LIVE switch-off stops in-flight motion and never leaves
    # content hidden — callbacks self-gate and setMotion(false) force-reveals
    assert 'if (motionOff()) { el.textContent = raw; return; }' in js
    assert "self-gate (Codex review)" in js
    set_motion_body = js.split("function setMotion")[1].split("function reveals")[0]
    assert 'el.style.opacity = "1"' in set_motion_body


def test_dashboard_build_copies_the_assets(tmp_path):
    # the copy is wired into the CLI; the pipe itself is idempotent
    first = copy_assets(tmp_path)
    second = copy_assets(tmp_path)
    assert [p.name for p in first] == [p.name for p in second]
    assert (tmp_path / "motion.js").exists() and (tmp_path / "vendor").is_dir()
