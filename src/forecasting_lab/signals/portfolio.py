"""Portfolio evaluation — the operator's book, checked honestly (P6c section A).

Given holdings (symbol + weight or dollars) and the latest verdict artifact, this
computes everything the portfolio page shows, deterministically:

- **mandate** — concentration vs the V4 caps (reuses ``agent_trader.mandate``:
  max-position on INVESTED capital, min-cash floor, sector caps);
- **ETF overlap** — QQQ⊂VOO⊂SPY etc. from a bundled top-holdings map, so
  "holding QQQ + VOO doubles the megacaps" is a real, reasoned warning;
- **per-holding verdict** — joined from the artifact (INSUFFICIENT where unknown);
- **crowding** — after de-duplicating overlap, is the whole book one bet?
- **vs SPY / vs HYSA** — the blended verdict lean against the two benchmarks
  every risk book must beat over the operator's horizon;
- **the decision-friction detector (§10)** — a positive verdict that is NOT
  actionable (already over the cap, earnings proximity, wide spread, wash-sale
  window) renders "don't do this now: <reason>";
- **advice lines with the reason stated**.

The thresholds + overlap data are exported as a contract (:func:`portfolio_contract`)
so the browser mirror uses the SAME numbers — never re-hardcoded. Nothing is
fabricated: missing data renders n/a. This is the operator's research tool, not
financial advice, and holdings never leave the browser (the page keeps them local).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..agent_trader.mandate import Rule, check_mandate

# Bundled approximate top-holdings for the core ETFs (public, stable membership;
# weights are indicative — used for OVERLAP detection, which is about shared
# names, not precise weights). Labeled approximate on the page; refreshable.
CORE_ETF_HOLDINGS: dict[str, dict[str, float]] = {
    "SPY": {"AAPL": .07, "MSFT": .07, "NVDA": .06, "AMZN": .035, "META": .025,
            "GOOGL": .02, "GOOG": .02, "AVGO": .02, "TSLA": .015, "BRK.B": .017},
    "VOO": {"AAPL": .07, "MSFT": .07, "NVDA": .06, "AMZN": .035, "META": .025,
            "GOOGL": .02, "GOOG": .02, "AVGO": .02, "TSLA": .015, "BRK.B": .017},
    "VTI": {"AAPL": .06, "MSFT": .06, "NVDA": .05, "AMZN": .03, "META": .022,
            "GOOGL": .018, "GOOG": .017, "AVGO": .017, "TSLA": .013, "BRK.B": .014},
    "QQQ": {"NVDA": .09, "AAPL": .09, "MSFT": .08, "AMZN": .055, "AVGO": .05,
            "META": .045, "TSLA": .03, "GOOGL": .025, "GOOG": .024, "COST": .025},
    "IWM": {"SMCI": .006, "FTAI": .005, "SFM": .004, "INSM": .004, "APP": .004},
    "DIA": {"UNH": .08, "GS": .07, "MSFT": .06, "HD": .055, "CAT": .05,
            "CRM": .045, "V": .04, "AXP": .04, "AMGN": .04, "MCD": .038},
    "SCHD": {"AVGO": .045, "HD": .04, "CVX": .04, "KO": .038, "VZ": .037,
             "PEP": .036, "CSCO": .035, "TXN": .034, "ABBV": .033, "AMGN": .033},
}

#: the operator's default mandate (mirrors the arena discipline; editable later)
DEFAULT_RULES = [
    Rule("max_position_pct", value=0.25),
    Rule("min_cash_pct", value=0.0),
]
CROWDING_OVERLAP_FLAG = 0.35  # effective-overlap above this = a crowded, single-bet book
OVERLAP_REPORT_FLOOR = 0.005  # pairwise doubled-exposure below this isn't worth a line
DIVIDEND_DRAG_YIELD_PCT = 2.5  # in a TAXABLE account, yields above this earn a drag note

#: the tax/account lens (P6e §B): which tax frictions apply where, with the
#: suppression reason stated ON SCREEN when they don't. One table for both the
#: engine and the JS mirror (shipped in the contract).
ACCOUNT_TYPES = ("taxable", "ira", "401k")
ACCOUNT_BEHAVIORS = {
    "taxable": {"wash_sale": True, "dividend_drag": True,
                "note": "taxable account — wash-sale and dividend-drag checks apply"},
    "ira": {"wash_sale": False, "dividend_drag": False,
            "note": "wash-sale rules don't apply in an IRA, and dividends compound "
                    "untaxed — those checks are off here"},
    "401k": {"wash_sale": False, "dividend_drag": False,
             "note": "wash-sale rules don't apply in a 401k, and dividends compound "
                     "untaxed — those checks are off here"},
}


@dataclass(frozen=True)
class Holding:
    symbol: str
    weight: float  # fraction of the invested book (0..1)


def normalize_holdings(raw: list[dict]) -> list[Holding]:
    """Accept ``[{symbol, weight}]`` or ``[{symbol, dollars}]`` -> weights that
    sum to <= 1 (the remainder is cash). Rows for the SAME symbol are consolidated
    (two lots of NVDA = one position — Codex review); bad rows are dropped."""
    agg: dict[str, float] = {}
    for r in raw:
        sym = str(r.get("symbol", "")).strip().upper()
        if not sym:
            continue
        if r.get("dollars") is not None:
            agg[sym] = agg.get(sym, 0.0) + max(0.0, float(r["dollars"]))
        elif r.get("weight") is not None:
            agg[sym] = agg.get(sym, 0.0) + max(0.0, float(r["weight"]))
    total = sum(agg.values())
    if total <= 0:
        return []
    # if inputs already look like weights summing to ~1, keep them; else normalize by total
    scale = total if total > 1.0001 else 1.0
    return [Holding(s, v / scale) for s, v in agg.items()]


def _exposure(sym: str, weight: float) -> dict[str, float]:
    """Look-through exposure of one holding to underlying names: an ETF spreads
    its weight across its constituents (weight x constituent%); a direct stock
    is its own single exposure."""
    holds = CORE_ETF_HOLDINGS.get(sym)
    if holds:
        return {name: weight * pct for name, pct in holds.items()}
    return {sym: weight}


def etf_overlap(holdings: list[Holding]) -> list[dict]:
    """Pairwise DUPLICATE exposure between held instruments, constituent-level:
    for each shared underlying name, the overlap is min(your exposure to it via
    A, via B) — the genuinely doubled dollars, not an inflated product."""
    out = []
    hs = list(holdings)
    for i in range(len(hs)):
        for j in range(i + 1, len(hs)):
            a, b = hs[i], hs[j]
            ea, eb = _exposure(a.symbol, a.weight), _exposure(b.symbol, b.weight)
            book_overlap, names = 0.0, []
            for name in set(ea) & set(eb):
                book_overlap += min(ea[name], eb[name])  # the doubled dollars in this name
                names.append(name)
            if book_overlap > OVERLAP_REPORT_FLOOR:
                out.append({"a": a.symbol, "b": b.symbol,
                            "book_overlap": round(book_overlap, 4),
                            "names": sorted(names, key=lambda n: -min(ea[n], eb[n]))[:6]})
    out.sort(key=lambda x: -x["book_overlap"])
    return out


def _lookthrough(holdings: list[Holding]) -> dict[str, float]:
    """The book's total exposure to each underlying name, de-duplicated across
    ETFs and direct positions (NVDA via SPY + via QQQ + direct = one number)."""
    agg: dict[str, float] = {}
    for h in holdings:
        for name, w in _exposure(h.symbol, h.weight).items():
            agg[name] = agg.get(name, 0.0) + w
    return agg


def _crowding(holdings: list[Holding]) -> dict:
    """Crowding from the DE-DUPLICATED look-through: the single largest underlying
    name, and the effective number of independent bets (1/HHI). Crowded when one
    underlying name dominates the book."""
    lt = _lookthrough(holdings)
    # denominator is TOTAL invested capital, not just the captured top-holdings —
    # the bundled maps cover only each ETF's top names, so dividing by the
    # captured sum would overstate every name's share (Codex review).
    invested = sum(h.weight for h in holdings)
    if invested <= 0 or not lt:
        return {"top_name": None, "top_weight": 0.0, "effective_bets": 0.0,
                "crowded": False, "n_holdings": len(holdings)}
    top_name = max(lt, key=lt.get)
    top_weight = lt[top_name] / invested
    # NOTE: we deliberately do NOT report an "effective bets" count — the bundled
    # top-holdings cover only each ETF's largest names, so a reliable HHI over the
    # FULL look-through isn't computable without complete constituents (Codex
    # review). The single-largest-underlying-name share is honest and computable.
    return {"top_name": top_name, "top_weight": round(top_weight, 4),
            "crowded": top_weight > CROWDING_OVERLAP_FLAG, "n_holdings": len(holdings)}


def decision_friction(sym: str, inv_share: float, label: str, cap: float,
                      *, earnings_days: int | None = None,
                      spread_pct: float | None = None,
                      recent_sale_days: int | None = None,
                      recent_sale_loss: bool | None = None,
                      account_type: str = "taxable") -> list[str]:
    """Reasons a POSITIVE verdict may still not be actionable now (§10).
    ``inv_share`` is the position as a fraction of INVESTED capital (the same
    basis the mandate uses). Only the checks whose data is present fire, and
    the wash-sale check only in account types where the rule exists (P6e)."""
    frictions = []
    if label in ("STRONG BUY", "BUY"):
        if inv_share >= cap - 1e-9:
            frictions.append(f"already {inv_share:.0%} of invested — at/over the {cap:.0%} cap; "
                             "adding breaks the mandate")
        if earnings_days is not None and 0 <= earnings_days <= 3:
            frictions.append(f"earnings in {earnings_days}d — the setup may reprice on the print")
        if spread_pct is not None and spread_pct > 0.10:
            frictions.append(f"spread {spread_pct:.0%} of mid — too wide to enter cleanly")
        # wash-sale only applies to a prior sale AT A LOSS (Codex review), and
        # only in a taxable account (P6e — the lens states the suppression)
        if (ACCOUNT_BEHAVIORS.get(account_type, ACCOUNT_BEHAVIORS["taxable"])["wash_sale"]
                and recent_sale_days is not None and 0 <= recent_sale_days < 30
                and recent_sale_loss):
            frictions.append(f"sold at a loss {recent_sale_days}d ago — wash-sale window, "
                             "a re-buy defers the loss")
    return frictions


def evaluate_portfolio(
    raw_holdings: list[dict],
    verdicts: dict,
    *,
    rules: list[Rule] | None = None,
    hysa_yield_pct: float | None = None,
    friction_data: dict | None = None,
    account_type: str = "taxable",
) -> dict:
    """The full portfolio evaluation. ``verdicts`` maps symbol -> {label, score};
    ``friction_data`` maps symbol -> {earnings_days, spread_pct, recent_sale_days,
    recent_sale_loss, dividend_yield_pct}. ``account_type`` is the tax lens
    (P6e): taxable applies the wash-sale + dividend-drag checks; IRA/401k
    suppress them WITH the reason stated in the advice."""
    if account_type not in ACCOUNT_TYPES:
        raise ValueError(f"unknown account_type {account_type!r} — one of {ACCOUNT_TYPES}")
    behaviors = ACCOUNT_BEHAVIORS[account_type]
    rules = rules or DEFAULT_RULES
    holdings = normalize_holdings(raw_holdings)
    if not holdings:
        return {"empty": True}
    weights = {h.symbol: h.weight for h in holdings}
    invested = sum(weights.values()) or 1.0
    cash = round(max(0.0, 1.0 - sum(weights.values())), 4)

    mandate = check_mandate(weights, rules)
    overlaps = etf_overlap(holdings)
    crowding = _crowding(holdings)
    cap = next((r.value for r in rules if r.type == "max_position_pct"), 0.25) or 0.25
    fd = friction_data or {}

    # blended score over the RATED holdings only, weight-renormalized — an
    # unrated (INSUFFICIENT / unknown) holding is NAMED, never imputed to 0 (Codex)
    rows, rated_wsum, rated_ssum, unrated = [], 0.0, 0.0, []
    for h in holdings:
        v = verdicts.get(h.symbol, {})
        label = v.get("label", "INSUFFICIENT EVIDENCE")
        # any INSUFFICIENT* variant is unrated (Codex review), and a score must exist
        rated = bool(v) and "score" in v and not str(label).upper().startswith("INSUFFICIENT")
        score = float(v.get("score", 0.0)) if rated else None
        inv_share = h.weight / invested
        if rated:
            rated_wsum += h.weight
            rated_ssum += h.weight * score
        else:
            unrated.append(h.symbol)
        rows.append({
            "symbol": h.symbol, "weight": round(h.weight, 4),
            "label": label, "score": round(score, 4) if rated else None,
            "friction": decision_friction(h.symbol, inv_share, label, cap,
                                          account_type=account_type,
                                          **{k: fd.get(h.symbol, {}).get(k)
                                             for k in ("earnings_days", "spread_pct",
                                                       "recent_sale_days", "recent_sale_loss")}),
        })
    rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0.0)))

    # None when too little of the book is rated to speak honestly
    blended = round(rated_ssum / rated_wsum, 4) if rated_wsum > 0 else None
    spy = verdicts.get("SPY", {})
    spy_score = float(spy["score"]) if spy and spy.get("label") != "INSUFFICIENT EVIDENCE" \
        and "score" in spy else None
    vs_spy = round(blended - spy_score, 4) if (blended is not None and spy_score is not None) else None
    vs_hysa = round(blended - hysa_yield_pct / 100.0, 4) \
        if (blended is not None and hysa_yield_pct is not None) else None

    advice = []
    for v in mandate.violations:
        advice.append(("block", v))
    for o in overlaps[:3]:
        advice.append(("overlap", f"{o['a']} + {o['b']} overlap ~{o['book_overlap']:.0%} of the book "
                                  f"({', '.join(o['names'][:3])}) — you're doubling the same names"))
    if crowding["crowded"] and crowding["top_name"]:
        advice.append(("crowding", f"{crowding['top_name']} is ~{crowding['top_weight']:.0%} of the book "
                                   "once you look through the ETFs — closer to one bet than it looks"))
    if unrated:
        advice.append(("unrated", f"no verdict yet for {', '.join(sorted(unrated))} — "
                                 "excluded from the blended score, not guessed"))
    if cash > 0:
        advice.append(("cash", f"{cash:.0%} in cash"))
    for r in rows:
        for fr in r["friction"]:
            advice.append(("friction", f"{r['symbol']}: attractive, but {fr}"))

    # the tax/account lens (P6e): dividend drag fires ONLY in taxable accounts
    # and ONLY on a real yield datum — never fabricated. In IRA/401k the
    # suppressed checks are stated on screen, not silently dropped — but only
    # when a datum they would have used actually exists.
    tax_data_present = False
    for h in holdings:
        yld = fd.get(h.symbol, {}).get("dividend_yield_pct")
        sale = fd.get(h.symbol, {}).get("recent_sale_days")
        if yld is not None or sale is not None:
            tax_data_present = True
        if (behaviors["dividend_drag"] and yld is not None
                and yld >= DIVIDEND_DRAG_YIELD_PCT):
            advice.append(("tax", f"{h.symbol} yields {yld:.1f}% — in a taxable account "
                                  "that's yearly tax drag; an IRA/401k shelters it"))
    if not behaviors["dividend_drag"] and tax_data_present:
        advice.append(("account", behaviors["note"]))

    return {
        "empty": False, "n_holdings": len(holdings), "cash": cash,
        "account_type": account_type,
        "mandate_status": mandate.status,
        "holdings": rows, "overlaps": overlaps, "crowding": crowding,
        "blended_score": blended, "vs_spy": vs_spy, "vs_hysa": vs_hysa,
        "advice": [{"kind": k, "text": t} for k, t in advice],
    }


def portfolio_contract() -> dict:
    """Thresholds + overlap data the browser mirror consumes (same numbers)."""
    return {
        "version": 1,
        "max_position_pct": next((r.value for r in DEFAULT_RULES if r.type == "max_position_pct"), 0.25),
        "min_cash_pct": next((r.value for r in DEFAULT_RULES if r.type == "min_cash_pct"), 0.0),
        "crowding_overlap_flag": CROWDING_OVERLAP_FLAG,
        "overlap_report_floor": OVERLAP_REPORT_FLOOR,
        "account_types": list(ACCOUNT_TYPES),
        "account_behaviors": {k: dict(v) for k, v in ACCOUNT_BEHAVIORS.items()},
        "dividend_drag_yield_pct": DIVIDEND_DRAG_YIELD_PCT,
        "core_etf_holdings": CORE_ETF_HOLDINGS,
    }
