"""The MCX connector, offline: row shape, library normalisation, backend
fallback, incremental planning, the per-commodity job settings, and that the
batched load terminates. No request leaves the machine."""

from datetime import date, datetime
from pathlib import Path

import pytest
from commodity_india import mcx_feed as m

FUT = {"sLTT": None, "Date": "09/24/2026", "Symbol": "GOLD         ", "ExpiryDate": "04DEC2026",
       "Open": 153557.0, "High": 153557.0, "Low": 152353.0, "Close": 152878.0,
       "PreviousClose": 153476.0, "Volume": 2991, "VolumeInThousands": "2991.000 GRMS ",
       "Value": 457368.91, "OpenInterest": 12185, "DateDisplay": "24 Sep 2026",
       "InstrumentName": "FUTCOM", "StrikePrice": 0.0, "OptionType": "-"}
OPT = {**FUT, "InstrumentName": "OPTFUT", "ExpiryDate": "25NOV2026", "StrikePrice": 159000.0,
       "OptionType": "PE"}


def test_futures_row_is_keyed_and_parsed():
    row = m.bhavcopy_row(FUT, "gold", "direct:contract")
    assert row["bhavcopy_id"] == "MCX:FUTCOM:GOLD:2026-12-04:2026-09-24"
    assert row["contract_id"] == "MCX:FUTCOM:GOLD:2026-12-04"
    assert row["contract_code"] == "GOLD"          # MCX pads symbols; the key must not
    assert row["trade_date"] == date(2026, 9, 24)  # MM/DD/YYYY, not DD/MM
    assert (row["traded_quantity"], row["quantity_unit"]) == (2991000.0, "GRMS")
    assert "strike_price" not in row


def test_option_row_keys_strike_and_type_but_links_the_chain():
    row = m.bhavcopy_row(OPT, "gold", "direct:contract")
    assert row["contract_id"] == "MCX:OPTFUT:GOLD:2026-11-25"
    assert row["bhavcopy_id"] == "MCX:OPTFUT:GOLD:2026-11-25:PE:159000:2026-09-24"
    assert row["option_type"] == "PE" and row["strike_price"] == 159000.0


def test_mcxpy_output_normalises_back_to_mcx_names():
    # mcxpy yields naive pandas timestamps, which is what this reproduces.
    day, expiry = datetime(2026, 9, 24), datetime(2026, 12, 4)  # noqa: DTZ001
    rec = {"Date": day, "Instrument Name": "FUTCOM", "Symbol": "GOLD",
           "Expiry Date": expiry, "Option Type": "-", "Strike Price": 0.0,
           "Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Previous Close": 1.0,
           "Volume(Lots)": 5, "VolumeInThousands": "5.000 GRMS", "Value(Lacs)": 2.0,
           "Open Interest(Lots)": 7}
    row = m.bhavcopy_row(m.from_mcxpy(rec), "gold", "mcxpy:datewise")
    assert row == {**row, "volume_lots": 5, "open_interest_lots": 7, "turnover_lakhs": 2.0,
                   "expiry_date": date(2026, 12, 4), "trade_date": date(2026, 9, 24)}


def test_mcxlib_output_is_already_native():
    assert m.bhavcopy_row(m.from_mcxlib(FUT), "gold", "x") == m.bhavcopy_row(FUT, "gold", "x")


def test_datewise_falls_through_dead_backends_once(monkeypatch):
    calls = []

    def dead(name):
        def f(day, instrument, client):
            calls.append(name)
            raise m.MCXUnavailable(f"{name}: backpage.aspx 404")
        return f

    monkeypatch.setitem(m.BACKENDS, "mcxlib", dead("mcxlib"))
    monkeypatch.setitem(m.BACKENDS, "mcxpy", dead("mcxpy"))
    monkeypatch.setitem(m.BACKENDS, "direct", lambda d, i, c: [FUT])
    feed = m.DatewiseFeed(client=None)
    assert feed.bhavcopy(date(2026, 9, 24), "FUTCOM") == ("direct", [FUT])
    assert feed.bhavcopy(date(2026, 9, 23), "FUTCOM")[0] == "direct"
    assert calls == ["mcxlib", "mcxpy"]           # a dead library is not retried per day


def test_every_backend_failing_raises():
    feed = m.DatewiseFeed(client=None, order=["mcxlib"])
    m.BACKENDS_saved = m.BACKENDS["mcxlib"]
    try:
        m.BACKENDS["mcxlib"] = lambda *a: (_ for _ in ()).throw(RuntimeError("down"))
        with pytest.raises(m.MCXUnavailable):
            feed.bhavcopy(date(2026, 9, 24), "FUTCOM")
    finally:
        m.BACKENDS["mcxlib"] = m.BACKENDS_saved


def _c(expiry, code="GOLD"):
    return m.Contract("FUTCOM", code, expiry, traded_today=True)


def test_plan_backfills_refetches_and_skips_completed():
    old, live, done = _c(date(2020, 12, 4)), _c(date(2026, 12, 4)), _c(date(2026, 8, 5))
    cursors = {live.contract_id: "2026-09-24"}
    windows = m.plan([old, live, done], cursors, [done.contract_id],
                     history_start=date(2021, 1, 1), today=date(2026, 9, 25), refetch_days=5)
    assert [w.contract for w in windows] == [live]           # pre-history and completed skipped
    assert windows[0].start == date(2026, 9, 19)             # cursor minus overlap
    first = m.plan([live], {}, [], date(2021, 1, 1), date(2026, 9, 25), 5)[0]
    assert first.start == date(2021, 1, 1) and first.end == date(2026, 9, 25)


def test_fetch_marks_an_expired_contract_complete():
    expired = _c(date(2026, 8, 5))

    class Client:
        def contract_history(self, c, start, end):
            return [{**FUT, "ExpiryDate": "05AUG2026", "Date": "08/05/2026"}]

    state: dict = {}
    rows = list(m.fetch_windows(Client(), [m.Window(expired, date(2026, 7, 1), expired.expiry)],
                                "gold", state, today=date(2026, 9, 25)))
    assert len(rows) == 1
    assert state["cursors"][expired.contract_id] == "2026-08-05"
    assert state["completed"] == [expired.contract_id]


def test_symbol_data_is_read_from_the_page():
    html = ('<div id="symbol-data" style="display:none;"> [{"Symbol":"GOLD","ExpiryDate":"04DEC2026",'
            '"TodaysTraded":1,"SymbolValue":"GOLD","InstrumentName":"FUTCOM"}]</div>')
    assert m.parse_symbol_data(html) == [_c(date(2026, 12, 4))]
    with pytest.raises(m.MCXUnavailable):
        m.parse_symbol_data("<html>redesigned</html>")


def test_catalogue_is_the_seed():
    assert "gold" in m.commodities()
    assert set(m.codes_for("gold")) >= {"GOLD", "GOLDM", "GOLDPETAL"}
    with pytest.raises(KeyError):
        m.codes_for("unobtainium")


def test_job_settings_validate(tmp_path: Path):
    from commodity_india.defs.mcx import job_settings

    ok = tmp_path / "ok.yaml"
    ok.write_text("defaults: {cron: '0 7 * * 2-6'}\ncommodities: {gold: {schedule: stopped}}\n")
    s = job_settings(ok)
    assert s["gold"] == {"cron": "0 7 * * 2-6", "schedule": "stopped"}
    assert s["silver"]["schedule"] == "running"          # seed commodity, defaults apply
    bad = tmp_path / "bad.yaml"
    bad.write_text("commodities: {golld: {}}\n")
    with pytest.raises(KeyError):
        job_settings(bad)
    typo = tmp_path / "typo.yaml"
    typo.write_text("commodities: {gold: {schedule: paused}}\n")
    with pytest.raises(ValueError):
        job_settings(typo)


def test_batched_load_terminates_with_active_contracts(monkeypatch):
    """The regression that looped forever: active contracts are never
    `completed`, so every batch re-planned them until `fetched` was shared."""
    from commodity_india.sources import mcx

    live = [_c(date(2026, 10 + i % 3, 5), code) for i, code in enumerate(["GOLD", "GOLDM", "GOLDTEN"] * 3)]
    live = list({c.contract_id: c for c in live}.values())

    class Client:
        def contracts(self):
            return live

        def contract_history(self, c, start, end):
            return []

    monkeypatch.setattr(m, "MCXClient", lambda **_: Client())
    runs = []

    def fake_run_source(wh, source, source_name, dataset):
        list(source.resources["futures_bhavcopy"])
        list(source.resources["options_bhavcopy"])
        runs.append(source_name)
        return {"load_ids": [], "rows": {}, "pipeline": source_name}

    monkeypatch.setattr("pf.runtime.dlt_runtime.run_source", fake_run_source)
    out = mcx.load_commodity(wh=None, commodity="gold", max_contracts=2)
    assert out["batches"] == -(-len(live) // 2)
    assert set(runs) == {"mcx_gold"}


def test_schedules_stagger_and_wrap():
    from commodity_india.defs.mcx import staggered

    assert staggered("0 6 * * 2-6", 0) == "0 6 * * 2-6"
    assert staggered("0 6 * * 2-6", 5) == "15 6 * * 2-6"
    assert staggered("50 23 * * *", 5) == "5 0 * * *"      # wraps past midnight
    assert staggered("*/5 6 * * *", 3) == "*/5 6 * * *"    # not a plain time: untouched
