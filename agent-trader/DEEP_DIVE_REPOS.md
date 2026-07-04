# Deep-dive: per-repo teardown

*Line-level analysis of 9 cloned repos (the 10th, Temple-Stuart's `temple-stuart-accounting`,
is now private/gone — reconstructed from its 3 Reddit posts in `DEEP_DIVE_FORUMS.md`).
Rigor grep applied to each: `brier|backtest|walk.forward|sharpe|calibrat|kelly|purge|
embargo|deflated|PBO|as.of|survivor|cost`. 2026-07-04.*

## Summary table

| Repo | What | Licence | Data (free? real-time?) | Rigor present | Verdict |
|---|---|---|---|---|---|
| **ralliesai/openfactor** | Barra-style US factor risk model | **Apache-2.0** ✅ | R2 CSV snapshots free; inputs paid (Massive/sec-api/Finnhub/FMP/TipRanks); **~weekly stale** | `as_of` ✅, winsorize ✅; **no** brier/backtest/CV/tests | ⭐⭐ Genuinely rigorous *estimation*; in-sample semantic gate is the weak spot |
| **ralliesai/rallies-cli** | "ChatGPT for traders" CLI | GPL-3.0 | proprietary closed backend (paid, real-time) | none | ◐ Thin LLM wrapper over a closed API |
| **ralliesai/tenk** | RAG over SEC filings | Personal-use (non-commercial) | EDGAR + yfinance free; local MiniLM; gpt-5.2 | none | ◐ Clean agentic RAG, cited; no methodology |
| **brentrager/get-rich-slow** | Kalshi sports live-lag scalper | **MIT** ✅ | ESPN + Kalshi WS free, real-time | "shadow strategies" = forward what-if, **frictionless** (no fee/slippage) | ◐ Good live infra, methodologically naive |
| **jakenesler/openprophet** | Claude-Code options trader (v2) | **CC BY-NC** (no commercial) | Alpaca paper/live + Gemini + macro; real-time | **none** in code (only in prompts) | ◐ Great harness; **risk caps are prompt-only** |
| **JakeNesler/Claude_Prophet** | v1 (deprecated) shell one-shot | MIT | Alpaca + Gemini | none ("backtesting code removed") | ◐ Superseded by openprophet |
| **Kingler16/Velora** | AI wealth advisor | **MIT** ✅ | yfinance/FRED/ECB/Brave/Finnhub free (delayed) | expectancy ✅, **refuses fake alpha** ✅, survivorship-visible ✅, per-pos Sharpe ✅; no brier/CV | ⭐ **Most honest repo**; adopt its Mandate gate |
| **btopn/OpenInsider-MCP** | 16-tool insider/short-data MCP | **MIT** ✅ | EDGAR/FINRA/RegSHO/OpenInsider/Yahoo — all free, **freshness documented per-tool** | n/a (data server); literature-cited | ⭐ **Best-documented data layer**; complements sources/finra+sec |
| **quixio/klaus-kode** | Claude-Code data-pipeline builder | **none** (all-rights-reserved) | off-domain; needs Quix PAT + Anthropic key | n/a; core `workflow_tools/` missing from clone | ◐ Good phased-approval pattern; unlicensed, half-missing |

## Detail — the four that matter

### openfactor ⭐⭐ (the one genuinely rigorous quant asset)
- **Factor math is correct Barra USE4-style.** `model/factor_returns.py`: daily cross-sectional
  WLS `return = market + sector + industry + style + residual`, **√market-cap weights**
  (`weighted_lstsq`, inline cite "Barra USE4 §3.1"), MAD-winsorized returns
  (`return_limit=5.0`), **exact equality-constrained** zero-sum sector/industry returns via a
  KKT block solve (`constrained_lstsq`), and a **market leg fixable to SPY**. Thin industries
  folded out (`min_group_members=5`).
- **No-look-ahead is structural.** `as_of_price_matrix(matrix, return_row+1)` builds exposures
  from prices *through the decision close*, then models the *next* return; fundamentals
  point-in-time filtered (`as_of_date == date`). Genuinely leakage-free.
- **The weak spot (correcting an earlier read): the semantic-residual gate is IN-SAMPLE.**
  `llm/semantic.py` accepts a discovered factor iff `after_var < before_var` measured **on the
  same 63-day window used to fit it** — no holdout, no significance, no DoF penalty → nearly
  always true. This is exactly the curve-fit trap; **wrap in PurgedWalkForwardCV before trusting.**
- **Validation is honest-but-partial:** in-sample cross-sectional R² ≈ 63.6%, momentum 0.77
  corr w/ Ken French; forward bias-stat calibration is *future work*; **zero tests shipped**;
  `--track` is a real forward ledger (not a backtest). **Data:** as_of 2026-06-25 (9 days stale
  today), 1000 US names, 102 factors, SEC-sourced market caps, SPY benchmark. Grade **B+ research**.
- **Adopt (Apache-2.0):** `constrained_lstsq` zero-sum purification; `as_of_price_matrix`/
  `rolling_exposures` leakage pattern for `ml.features.lag_features`; MAD-winsorize+z-score
  prep (`normalize.py`); the `--track` forward-accumulation ledger. **Don't** copy the semantic
  gate as-is.

### Velora ⭐ (the most honest repo — adopt its gate)
- **`mandate.py` = machine-checked rule engine** run on every recommendation before storing:
  `KNOWN_RULE_TYPES` = forbidden_ticker/instrument, max_position_pct, min_cash_pct,
  max_keyword_pct, max_sector_pct; returns pass|warn|**block**; concentration computed on
  **invested** capital (not total), sells always pass, missing data → skip (never false-block),
  atomic versioned writes + change-log. Plus `compute_strategy_drift` with warn/breach bands.
- **Refuses fake alpha** (`performance.py`): *"a real benchmark-alpha would need the index level
  at entry — that is NOT stored, so NO (fake) alpha is computed here."* **Survivorship visible:**
  expired watch-limits excluded from hit-rate but shown (`⊘ verfallen`). Real expectancy =
  `p(win)·avg_win + p(loss)·avg_loss`; per-position Sharpe. Property-tested. **MIT.**
- **Adopt wholesale:** the Mandate validator (→ `agent_trader/execution.py` guardrail) and the
  "refuse a metric you can't compute point-in-time" discipline (→ `eval`/`predictions.py`).

### openprophet ◐ (great plumbing, dangerous risk theatre)
- **Fail-closed order gate (the one good safety primitive):** `mcp-server.js` — if the agent
  server is unreachable, `ORDER_TOOLS` **throw "Order blocked for safety"** (non-order tools
  fail open). Enforces in code: `allowLiveTrading/Options/Stocks`, `allow0DTE` (parses OCC
  expiry), `requireConfirmation`, `maxOrderValue`.
- **Real bracket/trailing exits in Go** (`position_manager.go`): STOP + LIMIT OTO orders + a
  working trailing stop that cancels/re-places.
- **The red flag:** `maxPositionPct:15`, `maxDeployedPct:80`, `maxDailyLoss:5`,
  `maxOpenPositions:10` and "spread <10% of mid" exist **only as prompt text** —
  `enforcePermissions` never checks them. Advertised risk caps the code does **not** enforce.
  **CC BY-NC** (blocks commercial reuse). **Borrow** the fail-closed `ORDER_TOOLS` pattern +
  the Go bracket manager; **avoid** trusting its risk caps.

### OpenInsider-MCP ⭐ (best-documented data layer — complements the lab)
- 16 tools across **EDGAR** (Form 4, 8-K, NT-10K/Q late filings, 13D activist, S-3/424B5
  dilution; ~9 rps under SEC's limit), **FINRA/SEC short data** (short interest %float/DTC
  bi-monthly ~1-2wk lag; Reg SHO daily short volume ~1-day; FTDs + threshold list),
  **OpenInsider** scrape (cluster buys, officer buys $25k+, screener), **Yahoo** quote (60s TTL).
  All **free**, per-source TTL + rate-pace config, **every delay documented in-tool**, and tool
  descriptions **cite the academic basis** (Brav-Jiang 2008 +7% CAR on 13D; Diether-Lee-Werner
  2009; Stratmann-Welborn 2016) with honest "signal attenuated post-2008" hedges. **MIT.**
- **Adopt:** the endpoint set + the literature-cited, freshness-caveated tool descriptions +
  per-source TTL/rate-pace pattern → `sources/finra`, `sources/sec`, `signals/squeeze`.

*(get-rich-slow: borrow the hot-config-in-SQLite + live cross-source lag detection; never trust
its frictionless P&L. rallies-cli/tenk/klaus-kode: LLM scaffolding, no methodology.)*
