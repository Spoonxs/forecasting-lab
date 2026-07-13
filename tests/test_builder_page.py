"""P10-3 — the watcher builder (agent-builder shape, contract-bounded).

Pinned: watchers_contract() carries every template with its description,
bounds containing the runner's defaults, and the fixed params; a config
generated at the defaults round-trips through load_config unchanged; the
page embeds the contract + the CURRENT committed config, clamps every control
to the contract bounds in JS, builds all DOM via createElement/textContent
(no innerHTML), states on screen that nothing is written server-side, and
makes zero fetches.
"""

from __future__ import annotations

import json

from forecasting_lab.dashboard.builder_page import build_builder_page, render_builder_page
from forecasting_lab.pipeline.watchers import (
    DEFAULT_CONFIG,
    WATCHER_KINDS,
    load_config,
    watchers_contract,
)


def test_contract_covers_every_template_with_sane_bounds():
    c = watchers_contract()
    assert set(c["kinds"]) == set(WATCHER_KINDS)
    for kind, spec in c["kinds"].items():
        assert len(spec["description"]) > 30              # plain language, real
        assert spec["enabled_default"] is True
        for name, p in spec["params"].items():
            assert p["min"] <= p["default"] <= p["max"]   # defaults inside bounds
            assert p["default"] == DEFAULT_CONFIG[kind][name]
    # the squeeze metric is fixed (not user-tunable) and stated
    assert c["kinds"]["squeeze_trigger"]["fixed"] == {"metric": "short_volume_ratio"}
    assert "COMMITTED file" in c["note"]


def test_default_generated_config_roundtrips_through_load_config(tmp_path):
    c = watchers_contract()
    generated = {}
    for kind, spec in c["kinds"].items():
        generated[kind] = {"enabled": spec["enabled_default"],
                           **{n: p["default"] for n, p in spec["params"].items()},
                           **spec["fixed"]}
    path = tmp_path / "watchers.json"
    path.write_text(json.dumps(generated), encoding="utf-8")
    assert load_config(path) == DEFAULT_CONFIG            # byte-for-byte the runner's view
    # a tweaked value survives the round-trip too
    generated["squeeze_trigger"]["threshold"] = 0.75
    path.write_text(json.dumps(generated), encoding="utf-8")
    assert load_config(path)["squeeze_trigger"]["threshold"] == 0.75


def test_page_is_contract_driven_writes_nothing_and_is_xss_safe():
    html = render_builder_page()
    blob = html.split('id="contract" type="application/json">')[1].split("</script>")[0]
    parsed = json.loads(blob.replace("\\u003c", "<").replace("\\u003e", ">"))
    assert set(parsed["kinds"]) == set(WATCHER_KINDS)
    assert 'id="current"' in html                          # the committed config shown
    js = html.split("<script>")[-1]
    assert "clamp(" in js and "Math.min(p.max,Math.max(p.min,v))" in js
    assert "spec.params[name].default" in js               # defaults from the contract
    assert "innerHTML" not in js and "textContent" in js   # DOM built safely
    for banned in ("fetch(", "XMLHttpRequest", "sendBeacon", "http://", "https://"):
        assert banned not in js
    assert "writes nothing anywhere" in html
    assert "No server is\n  involved" in html or "No server is involved" in html.replace("\n  ", " ")
    assert "not financial advice" in html.lower()


# ------------------------------------------------ Codex code-review fixes pinned
def test_clamp_precision_and_honest_clipboard_are_pinned():
    """Codex findings: float step noise (0.6000000000000001) is normalized to
    the step's precision, and a clipboard failure is reported honestly."""
    js = render_builder_page().split("<script>")[-1]
    assert "Number(v.toFixed(dec))" in js                 # precision-normalized
    assert "(v-p.min)/p.step" in js                       # rounded FROM min
    assert "copy failed — select the text above" in js    # never a false 'copied'
    assert ".then(done,fail)" in js


def test_build_writes_the_page_and_home_links_it(tmp_path):
    page = build_builder_page(tmp_path)
    assert page.name == "builder.html"
    assert page.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    # the home watchers section links the builder (when the feed renders)
    import forecasting_lab.pipeline.digest as digest
    from forecasting_lab.dashboard.render import _watchers_feed_html

    feed = {"events": [], "skips": [{"kind": "x", "reason": "y"}]}
    orig = digest.read_latest_data
    digest.read_latest_data = lambda slug, out_dir=None: feed
    try:
        assert 'href="builder.html"' in _watchers_feed_html()
    finally:
        digest.read_latest_data = orig
