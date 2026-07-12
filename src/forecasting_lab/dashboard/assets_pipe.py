"""Static assets for the built site (P9): the vendored motion/3D libraries
and the shared motion layer, copied verbatim into the output directory so the
site keeps making ZERO external fetches.

Vendored, unmodified, licenses alongside: GSAP 3.12.5 (+ScrollTrigger) under
the GSAP Standard License (free incl. commercial since the Webflow
acquisition) and three.js r160 (MIT). See `assets/vendor/LICENSE-*.txt`.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

VENDOR_FILES = ("gsap.min.js", "ScrollTrigger.min.js", "three.module.min.js",
                "LICENSE-gsap.txt", "LICENSE-three.txt")
BUDGET_GZ_LANDING_JS = 250_000  # the landing's total JS, gzipped (pinned)


def copy_assets(out_dir: Path | str) -> list[Path]:
    """Copy motion.js + the vendor bundle into ``site/``. Returns the paths."""
    out = Path(out_dir)
    written: list[Path] = []
    pkg = resources.files("forecasting_lab.dashboard") / "assets"
    (out / "vendor").mkdir(parents=True, exist_ok=True)
    for name in VENDOR_FILES:
        data = (pkg / "vendor" / name).read_bytes()
        dest = out / "vendor" / name
        dest.write_bytes(data)
        written.append(dest)
    motion = out / "motion.js"
    motion.write_bytes((pkg / "motion.js").read_bytes())
    written.append(motion)
    return written
