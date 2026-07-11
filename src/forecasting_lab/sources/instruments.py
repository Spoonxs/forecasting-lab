"""The full-universe instrument registry — every listed US stock and ETF (P6a).

The platform must feel like a brokerage: ANY symbol searchable. The registry is
built from the two official, free Nasdaq Trader symbol directories
(``nasdaqlisted.txt`` = every NASDAQ listing, ``otherlisted.txt`` = every
NYSE/AMEX/ARCA/BATS listing), both carrying an authoritative ETF flag. A gzipped
snapshot of both files is bundled with the package so the registry works
offline at full size (~11k symbols); a live refresh replaces it when reachable
and **degrades honestly to the bundle** when not.

Beyond listings, the registry knows two more instrument kinds:
- **core ETFs** get curated metadata (expense ratio, benchmark description) —
  the handful the platform features on the home page;
- **HYSA-cash** is a first-class instrument whose yield comes from FRED
  (3-month T-bill / EFFR context) — the honest benchmark every risk asset must
  beat over the operator's horizon. Offline its yield is None, never a guess.

Unknown ticker -> ``None``. Test issues are excluded. Nothing is ever invented.
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from importlib import resources

from ..utils.http import HttpClient

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

_EXCHANGE_NAMES = {
    "A": "NYSE American",
    "N": "NYSE",
    "P": "NYSE Arca",
    "Z": "Cboe BZX",
    "V": "IEX",
}

#: curated metadata for the featured core ETFs (expense ratios as published).
CORE_ETFS: dict[str, dict] = {
    "VOO": {"expense_ratio": 0.0003, "benchmark": "S&P 500"},
    "SPY": {"expense_ratio": 0.000945, "benchmark": "S&P 500"},
    "QQQ": {"expense_ratio": 0.0020, "benchmark": "Nasdaq-100"},
    "VTI": {"expense_ratio": 0.0003, "benchmark": "US total market"},
    "IWM": {"expense_ratio": 0.0019, "benchmark": "Russell 2000"},
    "DIA": {"expense_ratio": 0.0016, "benchmark": "Dow Jones Industrial Average"},
    "SCHD": {"expense_ratio": 0.0006, "benchmark": "Dow Jones US Dividend 100"},
    "VXUS": {"expense_ratio": 0.0005, "benchmark": "Total international ex-US"},
    "BND": {"expense_ratio": 0.0003, "benchmark": "US total bond market"},
}

#: common index mutual funds -> their ETF twins (same exposure), expense
#: ratios as published. The fee delta is the whole point: "same exposure,
#: Nx the fee" is a real, checkable statement (P6e §3).
MUTUAL_FUND_TWINS: dict[str, dict] = {
    "VTSAX": {"twin": "VTI", "expense_ratio": 0.0004,
              "name": "Vanguard Total Stock Market Index Fund Admiral Shares"},
    "VFIAX": {"twin": "VOO", "expense_ratio": 0.0004,
              "name": "Vanguard 500 Index Fund Admiral Shares"},
    "FXAIX": {"twin": "VOO", "expense_ratio": 0.00015,
              "name": "Fidelity 500 Index Fund"},
    "SWPPX": {"twin": "VOO", "expense_ratio": 0.0002,
              "name": "Schwab S&P 500 Index Fund"},
    "SWTSX": {"twin": "VTI", "expense_ratio": 0.0003,
              "name": "Schwab Total Stock Market Index Fund"},
    "FSKAX": {"twin": "VTI", "expense_ratio": 0.00015,
              "name": "Fidelity Total Market Index Fund"},
    "VTIAX": {"twin": "VXUS", "expense_ratio": 0.0009,
              "name": "Vanguard Total International Stock Index Fund Admiral Shares"},
    "VBTLX": {"twin": "BND", "expense_ratio": 0.0004,
              "name": "Vanguard Total Bond Market Index Fund Admiral Shares"},
}

HYSA_SYMBOL = "CASH.HYSA"


def fund_twin(symbol: str) -> dict | None:
    """The twin card for a mutual fund: fund + twin symbols, both expense
    ratios, and the fee multiple (None when either ratio is unknown — the
    callout is honest or absent, never guessed)."""
    meta = MUTUAL_FUND_TWINS.get((symbol or "").strip().upper())
    if not meta:
        return None
    twin_er = CORE_ETFS.get(meta["twin"], {}).get("expense_ratio")
    fund_er = meta["expense_ratio"]
    multiple = round(fund_er / twin_er, 1) if fund_er and twin_er else None
    return {"fund": (symbol or "").strip().upper(), "twin": meta["twin"],
            "name": meta["name"], "fund_expense_ratio": fund_er,
            "twin_expense_ratio": twin_er, "fee_multiple": multiple}


def funds_for_twin(etf: str) -> list[str]:
    """Every mapped mutual fund whose twin is this ETF (bidirectional lookup)."""
    key = (etf or "").strip().upper()
    return sorted(f for f, m in MUTUAL_FUND_TWINS.items() if m["twin"] == key)


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    kind: str  # "stock" | "etf" | "mutual_fund" | "cash" | "other"
    exchange: str
    expense_ratio: float | None = None
    benchmark: str | None = None
    yield_pct: float | None = None  # cash only; None when the feed is unreachable


# securities that are listed but are NOT common stock (Codex review: preferreds,
# warrants, units, rights, notes must not pose as ordinary stocks in verdicts)
_NON_COMMON = ("preferred", "warrant", " right", "rights", " unit", "units",
               "notes due", "depositary", "debenture", "% notes")


def _classify(name: str, etf_flag: str) -> str:
    if etf_flag == "Y":
        return "etf"
    lowered = f" {name.lower()}"
    if any(marker in lowered for marker in _NON_COMMON):
        return "other"
    return "stock"


def _parse_nasdaq_listed(text: str) -> list[Instrument]:
    out: list[Instrument] = []
    for line in text.splitlines()[1:]:
        parts = line.split("|")
        if len(parts) < 8 or parts[0].startswith("File Creation"):
            continue
        symbol, name, _cat, test_issue, _fin, _lot, etf, _next = parts[:8]
        if test_issue == "Y" or not symbol:
            continue
        out.append(Instrument(symbol.strip(), name.strip(), _classify(name, etf), "NASDAQ"))
    return out


def _parse_other_listed(text: str) -> list[Instrument]:
    out: list[Instrument] = []
    for line in text.splitlines()[1:]:
        parts = line.split("|")
        if len(parts) < 8 or parts[0].startswith("File Creation"):
            continue
        symbol, name, exchange, _cqs, etf, _lot, test_issue, _nq = parts[:8]
        if test_issue == "Y" or not symbol:
            continue
        out.append(Instrument(
            symbol.strip(), name.strip(), _classify(name, etf),
            _EXCHANGE_NAMES.get(exchange, exchange),
        ))
    return out


def _bundled_text(name: str) -> str:
    ref = resources.files("forecasting_lab.sources") / "data" / f"{name}.gz"
    with ref.open("rb") as f:
        return gzip.decompress(f.read()).decode("utf-8", errors="replace")


def _enrich(inst: Instrument) -> Instrument:
    meta = CORE_ETFS.get(inst.symbol)
    if meta and inst.kind == "etf":
        return Instrument(inst.symbol, inst.name, inst.kind, inst.exchange,
                          expense_ratio=meta["expense_ratio"], benchmark=meta["benchmark"])
    return inst


class InstrumentRegistry:
    """The searchable universe. Loads the bundle; ``refresh()`` goes live."""

    def __init__(self) -> None:
        self._by_symbol: dict[str, Instrument] = {}
        self.source = "bundled snapshot"
        self._load(_bundled_text("nasdaqlisted.txt"), _bundled_text("otherlisted.txt"))

    def _load(self, nasdaq_text: str, other_text: str) -> None:
        instruments = _parse_nasdaq_listed(nasdaq_text) + _parse_other_listed(other_text)
        self._by_symbol = {i.symbol.upper(): _enrich(i) for i in instruments}
        self._by_symbol[HYSA_SYMBOL] = Instrument(
            HYSA_SYMBOL, "High-yield savings (cash benchmark)", "cash", "—",
            benchmark="3-month T-bill / EFFR", yield_pct=None,
        )
        # the common index mutual funds, searchable like everything else and
        # scored via their ETF twins (P6e §3)
        for sym, meta in MUTUAL_FUND_TWINS.items():
            self._by_symbol[sym] = Instrument(
                sym, meta["name"], "mutual_fund", "—",
                expense_ratio=meta["expense_ratio"], benchmark=f"ETF twin: {meta['twin']}",
            )

    def refresh(self, http: HttpClient | None = None) -> bool:
        """Replace the bundle with the live directories. False (bundle kept) on
        any failure — honest degradation, never a partial mix."""
        try:
            client = http or HttpClient()
            nasdaq_text = client.get_text(NASDAQ_LISTED_URL)
            other_text = client.get_text(OTHER_LISTED_URL)
            if "Symbol|" not in nasdaq_text or "ACT Symbol|" not in other_text:
                return False
            self._load(nasdaq_text, other_text)
            self.source = "nasdaqtrader.com (live)"
            return True
        except Exception:  # noqa: BLE001 - registry must never crash the build
            if self.source.endswith("(live)"):
                # a previously-live registry that failed to re-refresh is STALE
                # live data, not fresh — the label must say so (Codex review)
                self.source = "nasdaqtrader.com (live, stale — last refresh failed)"
            return False

    def get(self, symbol: str) -> Instrument | None:
        if not symbol or not isinstance(symbol, str):
            return None
        key = symbol.strip().upper()
        hit = self._by_symbol.get(key)
        if hit is None and "-" in key:  # Yahoo-style BRK-B -> directory-style BRK.B
            hit = self._by_symbol.get(key.replace("-", "."))
        if hit is None and "." in key:
            hit = self._by_symbol.get(key.replace(".", "-"))
        return hit

    def hysa(self, tbill_yield_pct: float | None = None) -> Instrument:
        """The cash instrument, optionally carrying a live FRED 3-month T-bill
        yield (percent). None stays None — n/a offline, never a made-up rate."""
        base = self._by_symbol[HYSA_SYMBOL]
        if tbill_yield_pct is None:
            return base
        return Instrument(base.symbol, base.name, base.kind, base.exchange,
                          benchmark=base.benchmark, yield_pct=float(tbill_yield_pct))

    def search(self, query: str, limit: int = 12) -> list[Instrument]:
        """Symbol-prefix first, then name substring — brokerage-style search."""
        q = (query or "").strip().upper()
        if not q:
            return []
        by_prefix = [i for s, i in self._by_symbol.items() if s.startswith(q)]
        by_prefix.sort(key=lambda i: (len(i.symbol), i.symbol))
        if len(by_prefix) < limit:
            ql = q.lower()
            hits = {i.symbol for i in by_prefix}
            by_name = [i for i in self._by_symbol.values()
                       if i.symbol not in hits and ql in i.name.lower()]
            by_name.sort(key=lambda i: i.symbol)
            by_prefix.extend(by_name)
        return by_prefix[:limit]

    def symbols(self, kinds: tuple[str, ...] = ("stock", "etf")) -> list[str]:
        """All listed symbols of the given kinds, sorted (the worker allowlist)."""
        return sorted(s for s, i in self._by_symbol.items() if i.kind in kinds)

    def __len__(self) -> int:
        return len(self._by_symbol)


def hysa_yield_pct(http: HttpClient | None = None) -> float | None:
    """Live 3-month T-bill yield (percent) from FRED's public CSV; None offline."""
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3"
    try:
        text = (http or HttpClient()).get_text(url)
        for line in reversed(text.strip().splitlines()[1:]):
            parts = line.split(",")
            if len(parts) < 2:  # malformed row: skip it, don't fail the fetch
                continue
            try:
                return float(parts[1])
            except ValueError:
                continue
        return None
    except Exception:  # noqa: BLE001 - optional signal, never fatal
        return None
