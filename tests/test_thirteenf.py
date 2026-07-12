"""P7 section B — 13F holders (stale by design, and it says so).

Pinned: the information-table parser extracts top holdings by value from
fixture XML (namespaced or not) and drops malformed rows; the staleness label
carries the filing lag and today's age; issuer->ticker matching is best-effort
and NEVER guesses on ambiguity; a blocked network is a stated skip per
manager; matched tickers land in the store dated by the FILING date, never
today; nothing here touches the verdict engine (the scoring contract's
weights are byte-identical with and without this module imported).
"""

from __future__ import annotations

from datetime import date

from forecasting_lab.sources.thirteenf import (
    MANAGERS,
    fetch_13f_digest,
    match_ticker,
    parse_13f_table,
    staleness,
)

XML = """<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
<infoTable><nameOfIssuer>APPLE INC</nameOfIssuer><cusip>037833100</cusip>
  <value>1,234,567</value><shrsOrPrnAmt><sshPrnamt>5,000,000</sshPrnamt></shrsOrPrnAmt></infoTable>
<infoTable><nameOfIssuer>NVIDIA CORP</nameOfIssuer><cusip>67066G104</cusip>
  <value>999</value><shrsOrPrnAmt><sshPrnamt>10</sshPrnamt></shrsOrPrnAmt></infoTable>
<infoTable><nameOfIssuer>BROKEN ROW</nameOfIssuer><cusip>x</cusip>
  <value>not-a-number</value><shrsOrPrnAmt><sshPrnamt>1</sshPrnamt></shrsOrPrnAmt></infoTable>
</informationTable>"""

XML_NS = XML.replace("<infoTable>", "<ns1:infoTable>").replace("</infoTable>", "</ns1:infoTable>") \
            .replace("<nameOfIssuer>", "<ns1:nameOfIssuer>").replace("</nameOfIssuer>", "</ns1:nameOfIssuer>") \
            .replace("<value>", "<ns1:value>").replace("</value>", "</ns1:value>") \
            .replace("<sshPrnamt>", "<ns1:sshPrnamt>").replace("</sshPrnamt>", "</ns1:sshPrnamt>")


def test_parser_ranks_by_value_and_drops_malformed_rows():
    rows = parse_13f_table(XML)
    assert [r["issuer"] for r in rows] == ["APPLE INC", "NVIDIA CORP"]  # broken row gone
    assert rows[0]["value_kusd"] == 1234567.0 and rows[0]["shares"] == 5e6
    assert parse_13f_table(XML, top=1) == rows[:1]
    assert parse_13f_table("") == [] and parse_13f_table(None) == []
    # namespaced filings parse identically
    assert [r["issuer"] for r in parse_13f_table(XML_NS)] == ["APPLE INC", "NVIDIA CORP"]


def test_staleness_states_the_lag_and_the_age():
    s = staleness("2026-03-31", "2026-05-15", date(2026, 7, 11))
    assert s["filing_lag_days"] == 45 and s["age_days"] == 102
    assert "positions as of 2026-03-31" in s["label"]
    assert "filed 45d later" in s["label"] and "102d old today" in s["label"]
    assert "context, not signal" in s["label"]


def test_ticker_match_is_best_effort_never_a_guess():
    class _Reg:
        def __init__(self, hits):
            self.hits = hits

        def search(self, q, limit=4):
            return self.hits

    class _I:
        def __init__(self, symbol, name, kind="stock"):
            self.symbol, self.name, self.kind = symbol, name, kind

    one = _Reg([_I("AAPL", "Apple Inc. Common Stock")])
    assert match_ticker("APPLE INC", one) == "AAPL"
    # legal-suffix and stopword noise normalizes away (the Berkshire book):
    boa = _Reg([_I("BAC", "Bank of America Corporation Common Stock")])
    assert match_ticker("BANK AMERICA CORP", boa) == "BAC"
    coke = _Reg([_I("KO", "Coca-Cola Company (The) Common Stock")])
    assert match_ticker("COCA COLA CO", coke) == "KO"
    # a similar-but-distinct name is NOT ambiguous under token equality...
    distinct = _Reg([_I("AAPL", "Apple Inc. Common Stock"),
                     _I("APLE", "Apple Hospitality REIT Inc.")])
    assert match_ticker("APPLE INC", distinct) == "AAPL"
    # ...but identical normalized names (share classes) stay None — no guess
    classes = _Reg([_I("GOOGL", "Alphabet Inc. Class A Common Stock"),
                    _I("GOOG", "Alphabet Inc. Class C Capital Stock")])
    assert match_ticker("ALPHABET INC", classes) is None
    assert match_ticker("ZZ", one) is None               # too short to trust
    assert match_ticker("UNKNOWN HOLDINGS LLC", _Reg([])) is None


def test_blocked_network_is_a_stated_skip_per_manager():
    class _Boom:
        def get_json(self, url, **kw):
            raise ConnectionError("blocked here")

        def get_text(self, url, **kw):
            raise ConnectionError("blocked here")

    digest = fetch_13f_digest(http=_Boom(), on=date(2026, 7, 11),
                              registry=type("R", (), {"search": lambda s, q, limit=4: []})())
    assert digest["managers"] == []
    assert len(digest["skips"]) == len(MANAGERS)
    assert all("blocked here" in s["reason"] for s in digest["skips"])
    assert digest["as_of"] == "2026-07-11"


def test_store_facts_are_dated_by_the_filing_never_today():
    class _Http:
        def get_json(self, url, **kw):
            if "submissions" in url:
                return {"filings": {"recent": {
                    "form": ["10-K", "13F-HR"],
                    "accessionNumber": ["0000-1", "0001-23-000045"],
                    "filingDate": ["2026-01-02", "2026-05-15"],
                    "reportDate": ["2025-12-31", "2026-03-31"]}}}
            return {"directory": {"item": [{"name": "primary_doc.xml"},
                                           {"name": "infotable.xml"}]}}

        def get_text(self, url, **kw):
            assert url.endswith("infotable.xml")
            return XML

    class _Store:
        def __init__(self):
            self.calls = []

        def record(self, on, metric, values):
            self.calls.append((on, metric, values))

    class _Reg:
        def search(self, q, limit=4):
            class _I:
                symbol, name, kind = "AAPL", "Apple Inc. Common Stock", "stock"
            return [_I()] if "apple" in q else []

    store = _Store()
    digest = fetch_13f_digest({"Berkshire Hathaway": "1067983"}, http=_Http(),
                              on=date(2026, 7, 11), registry=_Reg(), store=store)
    block = digest["managers"][0]
    assert block["staleness"]["period"] == "2026-03-31"
    assert block["holdings"][0]["ticker"] == "AAPL"      # matched
    assert block["holdings"][1]["ticker"] is None        # NVIDIA unmatched here: honest
    assert store.calls == [("2026-05-15", "13f_value_1067983", {"AAPL": 1234567.0})]


def test_nothing_here_touches_the_verdict_engine():
    from forecasting_lab.signals.verdict import scoring_contract
    before = scoring_contract()["base_weights"]
    import forecasting_lab.sources.thirteenf  # noqa: F401 - the import itself must be inert

    assert scoring_contract()["base_weights"] == before
    import inspect

    src = inspect.getsource(forecasting_lab.sources.thirteenf)
    assert "compute_verdict" not in src                  # no code path into scoring
