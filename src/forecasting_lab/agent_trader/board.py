"""P6 — the live account board.

Renders the REAL account state (from the run loop's snapshot + the actual broker) as a
self-contained page: equity, return vs the benchmark, drawdown, positions, the live
strategy version, and a blunt banner — paper vs. real, dollars at risk, and "edge proven?
not yet" until the gate says otherwise. In production the numbers stream from the broker
websocket (SIP pinned); here it renders a real snapshot. Real results, including red days —
never just a green screenshot.
"""

from __future__ import annotations

import html as _html


def _pct(v: float, signed: bool = True) -> str:
    s = "+" if signed and v >= 0 else ("−" if v < 0 else "")
    return f"{s}{abs(v) * 100:.2f}%"


def render_account(snapshot: dict, *, start_equity: float, benchmark_return: float,
                   ladder, peak_equity: float | None = None) -> str:
    """A self-contained live-account page from a run snapshot + benchmark + ladder state."""
    equity = float(snapshot.get("equity", start_equity))
    ret = equity / start_equity - 1.0 if start_equity else 0.0
    excess = ret - benchmark_return
    peak = max(peak_equity or start_equity, equity)
    drawdown = equity / peak - 1.0 if peak else 0.0

    at_risk = 0.0 if ladder.is_paper else ladder.capital
    mode = "PAPER" if ladder.is_paper else "LIVE"
    verdict = (f"Live version {ladder.live_version} — gate-cleared"
               if ladder.live_version else "Edge proven? Not yet — stay on paper")
    halted = snapshot.get("halted")

    rows = "".join(
        f"<tr><td>{_html.escape(str(s))}</td><td class='n'>{q:g}</td></tr>"
        for s, q in (snapshot.get("positions") or {}).items()
    ) or "<tr><td colspan='2'>flat</td></tr>"

    up = "#0B6B3A"
    dn = "#B0281A"
    ret_c = up if ret >= 0 else dn
    ex_c = up if excess >= 0 else dn
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Agent account — {mode}</title>
<style>
body{{font:15px/1.5 ui-sans-serif,system-ui,Arial;background:#0f1115;color:#e8e8ea;margin:0;padding:22px}}
.banner{{padding:10px 14px;border-radius:8px;font-weight:700;margin-bottom:16px;
  background:{'#22301f' if ladder.is_paper else '#3a2320'};border:1px solid #333}}
.kpis{{display:flex;gap:22px;flex-wrap:wrap;margin-bottom:16px}}
.kpi b{{display:block;font:700 26px/1.1 ui-sans-serif}} .kpi span{{color:#9a9aa2;font-size:12px;text-transform:uppercase;letter-spacing:.05em}}
table{{border-collapse:collapse;min-width:240px}} td{{padding:6px 12px;border-bottom:1px solid #23262d}} .n{{text-align:right;font-variant-numeric:tabular-nums}}
.halt{{color:{dn};font-weight:700}} .foot{{color:#7a7a82;font-size:12px;margin-top:18px}}
</style></head><body>
<div class="banner">{mode} · ${at_risk:,.0f} at risk · {_html.escape(verdict)}{' · TRADING HALTED (kill switch)' if halted else ''}</div>
<div class="kpis">
  <div class="kpi"><span>Equity</span><b>${equity:,.0f}</b></div>
  <div class="kpi"><span>Return</span><b style="color:{ret_c}">{_pct(ret)}</b></div>
  <div class="kpi"><span>vs benchmark</span><b style="color:{ex_c}">{_pct(excess)}</b></div>
  <div class="kpi"><span>Drawdown</span><b style="color:{dn}">{_pct(drawdown, signed=False)}</b></div>
  <div class="kpi"><span>Live version</span><b>{_html.escape(str(ladder.live_version or 'none — paper'))}</b></div>
</div>
<table><thead><tr><td>position</td><td class="n">qty</td></tr></thead><tbody>{rows}</tbody></table>
<div class="foot">Benchmark return {_pct(benchmark_return)} over the same window · run {_html.escape(str(snapshot.get('run_id','')))} ·
Not financial advice — a research and skill-building system.</div>
</body></html>"""
