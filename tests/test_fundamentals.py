"""P10-2 — SEC XBRL fundamentals (point-in-time honest).

Pinned: extraction dedups by fiscal period keeping the LATEST filing at or
before as_of and NEVER anything filed after it; the first us-gaap tag that
yields data wins (no mixing); annual/quarterly split; the rolling sweep
refreshes only stale symbols up to the per-run cap, skips unmapped tickers
with a stated reason, and opens the circuit on consecutive failures; the
Financials module renders every value WITH its filed date and honest empty
states; nothing here can reach a verdict (contract weights byte-identical).
"""

from __future__ import annotations

import json
from datetime import date

from forecasting_lab.dashboard.verdict_page import _financials_module
from forecasting_lab.sources.fundamentals import (
    extract_metrics,
    fetch_fundamentals,
    load_fundamentals,
)

AS_OF = date(2026, 7, 12)


def _facts() -> dict:
    def e(end, val, fp, fy, filed, form="10-K"):
        return {"end": end, "val": val, "fp": fp, "fy": fy, "filed": filed, "form": form}

    return {"entityName": "ACME CORP", "facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            e("2024-12-31", 100e9, "FY", 2024, "2025-02-10"),
            e("2025-12-31", 120e9, "FY", 2025, "2026-02-10"),
            e("2025-12-31", 121e9, "FY", 2025, "2026-03-01", "10-K/A"),  # amended, later
            e("2026-12-31", 999e9, "FY", 2026, "2027-02-10"),            # FUTURE filing
            e("2026-03-31", 30e9, "Q1", 2026, "2026-05-05", "10-Q"),
        ]}},
        "Revenues": {"units": {"USD": [                                  # ignored: tag 2
            e("2025-12-31", 555e9, "FY", 2025, "2026-02-10"),
        ]}},
        "NetIncomeLoss": {"units": {"USD": [
            e("2025-12-31", 25e9, "FY", 2025, "2026-02-10"),
        ]}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": [
            e("2025-12-31", 6.42, "FY", 2025, "2026-02-10"),
        ]}},
    }}}


def test_extraction_is_point_in_time_and_dedups_by_latest_filing():
    m = extract_metrics(_facts(), AS_OF)
    rev = m["revenue"]["annual"]
    assert [r["end"] for r in rev] == ["2024-12-31", "2025-12-31"]  # future filing OUT
    fy25 = rev[-1]
    assert fy25["val"] == 121e9 and fy25["filed"] == "2026-03-01"   # the amendment wins
    assert m["revenue"]["quarterly"][0]["fp"] == "Q1"
    # the first tag with data wins — the 555e9 from tag 2 never mixes in
    assert all(r["val"] != 555e9 for r in rev)
    assert m["net_income"]["annual"][0]["val"] == 25e9
    assert m["eps"]["annual"][0]["val"] == 6.42
    assert m["entity"] == "ACME CORP"
    # before anything was filed -> honest nothing, but STILL a stamped record
    # (Codex review: fetched-empty must never render as never-fetched)
    early = extract_metrics(_facts(), date(2024, 1, 1))
    assert early["entity"] == "ACME CORP" and early["as_of"] == "2024-01-01"
    assert not any(k in early for k in ("revenue", "net_income", "eps"))


def test_rolling_sweep_caps_skips_and_breaks(tmp_path, monkeypatch):
    monkeypatch.setattr("forecasting_lab.sources.sec.company_tickers",
                        lambda refresh=False: {"AAA": 1, "BBB": 2, "CCC": 3})

    class _Http:
        def __init__(self):
            self.calls = []

        def get_json(self, url):
            self.calls.append(url)
            if "0000000002" in url:
                raise ConnectionError("blocked")
            return _facts()

    http = _Http()
    rec = fetch_fundamentals(["AAA", "BBB", "CCC", "NOCIK"], as_of=AS_OF,
                             http=http, root=tmp_path, max_fetch=10)
    assert rec["fetched"] == 2                            # AAA + CCC
    reasons = {s["symbol"]: s["reason"] for s in rec["skips"]}
    assert "blocked" in reasons["BBB"] and "no CIK" in reasons["NOCIK"]
    assert load_fundamentals("AAA", root=tmp_path)["entity"] == "ACME CORP"
    # a fresh cache skips the network on the next run
    rec2 = fetch_fundamentals(["AAA"], as_of=AS_OF, http=_Http(), root=tmp_path)
    assert rec2["fresh"] == 1 and rec2["fetched"] == 0
    # the per-run cap holds (rolling window)
    many = [f"S{i}" for i in range(9)]
    monkeypatch.setattr("forecasting_lab.sources.sec.company_tickers",
                        lambda refresh=False: {s: i + 10 for i, s in enumerate(many)})
    rec3 = fetch_fundamentals(many, as_of=AS_OF, http=_Http(),
                              root=tmp_path / "b", max_fetch=3)
    assert rec3["fetched"] == 3


def test_financials_module_renders_filed_dates_and_honest_empties():
    m = extract_metrics(_facts(), AS_OF)
    html = _financials_module(m)
    assert "Revenue" in html and "120.0B" not in html and "121.0B" in html
    assert "filed 2026-03-01" in html                     # staleness ON SCREEN
    assert "never a verdict input" in html
    assert "n/a" in html                                  # FY2024 has no NI/EPS -> honest
    assert _financials_module(None).count("Not fetched yet") == 1
    assert "honest n/a" in _financials_module({"entity": "X"})


# ------------------------------------------------ Codex code-review fixes pinned
def test_ytd_facts_never_pose_as_quarters():
    """Codex finding 3: a Jan–Sep YTD duration fact with fp=Q3 must not be
    cached as 'the quarter'; a 3-month fact must not be cached as FY."""
    facts = _facts()
    entries = facts["facts"]["us-gaap"][
        "RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"]
    entries.append({"end": "2026-03-31", "val": 88e9, "fp": "Q1", "fy": 2026,
                    "filed": "2026-05-05", "form": "10-Q",
                    "start": "2025-07-01"})               # a 9-month YTD span
    entries.append({"end": "2025-12-31", "val": 31e9, "fp": "FY", "fy": 2025,
                    "filed": "2026-02-10", "form": "10-K",
                    "start": "2025-10-01"})               # a 3-month span posing as FY
    for e in entries[:5]:                                 # give the real rows spans too
        if e["fp"] == "FY":
            e["start"] = e["end"][:4] + "-01-01"
        elif e["fp"] == "Q1":
            e.setdefault("start", "2026-01-01")
    m = extract_metrics(facts, AS_OF)
    q1 = [r for r in m["revenue"]["quarterly"] if r["end"] == "2026-03-31"]
    assert len(q1) == 1 and q1[0]["val"] == 30e9          # the true quarter, not YTD
    fy25 = [r for r in m["revenue"]["annual"] if r["end"] == "2025-12-31"]
    assert fy25[0]["val"] == 121e9                        # not the 3-month impostor


def test_fresh_meta_over_missing_cache_refetches(tmp_path, monkeypatch):
    """Codex finding 1: a fresh meta stamp can't mask a deleted/corrupt cache."""
    monkeypatch.setattr("forecasting_lab.sources.sec.company_tickers",
                        lambda refresh=False: {"AAA": 1})

    class _Http:
        calls = 0

        def get_json(self, url):
            _Http.calls += 1
            return _facts()

    fetch_fundamentals(["AAA"], as_of=AS_OF, http=_Http(), root=tmp_path)
    (tmp_path / "AAA.json").unlink()                      # the cache vanishes
    rec = fetch_fundamentals(["AAA"], as_of=AS_OF, http=_Http(), root=tmp_path)
    assert rec["fetched"] == 1 and rec["fresh"] == 0      # it refetched
    assert load_fundamentals("AAA", root=tmp_path) is not None


def test_fetched_empty_renders_as_no_series_not_unfetched():
    """Codex finding 2: a registrant with none of our tags says 'no us-gaap
    series', never 'not fetched yet'."""
    empty = extract_metrics({"entityName": "TAGLESS CO", "facts": {"us-gaap": {}}}, AS_OF)
    html = _financials_module(empty)
    assert "No annual us-gaap series" in html and "Not fetched yet" not in html


def test_fundamentals_never_reach_the_verdict_engine():
    import inspect

    import forecasting_lab.sources.fundamentals as mod
    from forecasting_lab.signals.verdict import scoring_contract

    before = json.dumps(scoring_contract()["base_weights"], sort_keys=True)
    extract_metrics(_facts(), AS_OF)
    assert json.dumps(scoring_contract()["base_weights"], sort_keys=True) == before
    assert "compute_verdict" not in inspect.getsource(mod)
