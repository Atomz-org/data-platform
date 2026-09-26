"""MCX bhavcopy for commodity-india: the exchange's own daily settlement, per commodity.

Everything else in this project prices India from international benchmarks
landed through FX and duty. This is the other half a desk trades against: what
MCX itself settled — every futures contract and option strike, with volume,
open interest and turnover. The connector is `commodity_india.mcx_feed`.

**One commodity is one pipeline.** `mcx_source("gold")` loads only the MCX
codes the `mcx_products` seed files under gold, through a dlt pipeline named
for gold (`commodity-india_mcx_gold`), so each commodity keeps its own cursors
in its own dlt state. Pausing silver never holds up gold, a failed crude load
retries only crude, and a commodity added to the seed backfills alone. All of
them land in the same three tables of the `mcx` dataset, merged on their keys,
which is what the one set of staging models reads.

**Resumable by construction.** `load_commodity` runs the pipeline in batches of
`max_contracts`; each batch commits its rows and its cursors before the next
starts. Stopping a backfill (a terminated Dagster run, a laptop lid) loses at
most one batch, and the next run starts where that one stopped.

    uv run python -m commodity_india.sources.mcx gold silver     # ad hoc, no Dagster
    SOURCES__MCX__HISTORY_START=2016-01-01 uv run python -m commodity_india.sources.mcx gold

Excluded from the factory's auto-discovery (definitions.py passes
`source_modules`): the factory would make one all-commodity asset of these
resources, and the per-commodity jobs in `defs/mcx.py` replace it.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dlt
from pf.ontology import annotate

from commodity_india import mcx_feed

DATASET = "mcx"
IST = ZoneInfo("Asia/Kolkata")
PROJECT_DIR = Path(__file__).resolve().parents[3]

# dlt reads `.dlt/config.toml` from the working directory. A Dagster code
# location runs in `<project>/src` and `pf seed` from wherever it was typed, so
# without this every `[sources.mcx]` setting silently falls back to the
# defaults in `_cfg` — an edited history_start that does nothing.
os.environ.setdefault("DLT_PROJECT_DIR", str(PROJECT_DIR))


def _cfg(key: str, default: Any) -> Any:
    value = dlt.config.get(f"sources.mcx.{key}")
    return default if value is None else value


def history_start() -> date:
    return date.fromisoformat(str(_cfg("history_start", "2021-01-01")))


def today_ist() -> date:
    from datetime import datetime
    return datetime.now(IST).date()


@dataclass
class Run:
    """What one pipeline run of one commodity works from, shared by its resources."""

    commodity: str
    codes: tuple[str, ...]
    client: mcx_feed.MCXClient
    today: date
    max_contracts: int | None
    #: Filled by the resources, read by `load_commodity` after each batch.
    progress: dict[str, int] = field(default_factory=dict)
    #: Contracts an earlier batch of this same load already fetched. Without it
    #: an active contract — never `completed` until it expires — is planned
    #: again by every batch and the load never finishes.
    fetched: set[str] = field(default_factory=set)
    _contracts: list[mcx_feed.Contract] | None = None

    def contracts(self, instrument: str) -> list[mcx_feed.Contract]:
        if self._contracts is None:
            self._contracts = [c for c in self.client.contracts() if c.code in self.codes]
        return [c for c in self._contracts if c.instrument == instrument]


PRICE_COLUMNS = {
    "trade_date": {"data_type": "date"},
    "expiry_date": {"data_type": "date"},
    "open": {"data_type": "double"},
    "high": {"data_type": "double"},
    "low": {"data_type": "double"},
    "close": {"data_type": "double"},
    "previous_close": {"data_type": "double"},
    "volume_lots": {"data_type": "bigint"},
    "open_interest_lots": {"data_type": "bigint"},
    "traded_quantity": {"data_type": "double"},
    "turnover_lakhs": {"data_type": "double"},
}

SESSION_ROLES = {
    "bhavcopy_id": "natural_key",
    "mcx_commodity": "status_enum",
    "contract_code": "free_text",
    "instrument_type": "status_enum",
    "trade_date": "event_time",
    "expiry_date": "reference_date",
    "open": "unit_price",
    "high": "unit_price",
    "low": "unit_price",
    "close": "unit_price",
    "previous_close": "unit_price",
    "volume_lots": "quantity",
    "traded_quantity": "quantity",
    "quantity_unit": "unit_of_measure",
    "open_interest_lots": "quantity",
    "turnover_lakhs": "money_amount",
    "extracted_via": "status_enum",
}
SESSION_RENAME = {
    "bhavcopy_id": "session_id", "trade_date": "traded_at",
    "open": "open_price", "high": "high_price", "low": "low_price",
    "close": "close_price", "previous_close": "previous_close_price",
}


def _batch(run: Run, key: str, windows: list[mcx_feed.Window]) -> list[mcx_feed.Window]:
    windows = [w for w in windows if w.contract.contract_id not in run.fetched]
    todo = windows[:run.max_contracts] if run.max_contracts else windows
    run.progress[key] = len(windows) - len(todo)
    run.fetched.update(w.contract.contract_id for w in todo)
    return todo


@dlt.resource(name="futures_bhavcopy", write_disposition="merge", primary_key="bhavcopy_id",
              columns=PRICE_COLUMNS)
@annotate(
    source="mcx",
    concept="ContractSession",
    grain="one MCX futures contract per trading day",
    description="MCX futures bhavcopy: each contract's daily OHLC, settlement, volume in "
                "lots, traded quantity, turnover (₹ lakh) and open interest, as MCX states "
                "it — ₹ per the contract's quote basis (unconverted)",
    roles=SESSION_ROLES,
    rename=SESSION_RENAME,
    currency="INR",
    links={"contract_id": "ExchangeContract"},
)
def futures_bhavcopy(run: Run) -> Iterator[dict[str, Any]]:
    state = dlt.current.resource_state()
    if str(_cfg("strategy", "contract")) == "datewise":
        yield from _datewise_futures(run, state)
        return
    windows = mcx_feed.plan(run.contracts(mcx_feed.FUTURES), state.get("cursors", {}),
                            state.get("completed", []), history_start(), run.today,
                            int(_cfg("refetch_days", 5)))
    yield from mcx_feed.fetch_windows(run.client, _batch(run, "futures", windows),
                                      run.commodity, state, run.today)


def _datewise_futures(run: Run, state: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """The libraries' own path: one bhavcopy per weekday, filtered to this commodity.

    Cursor is the last day stored for the commodity as a whole. Exchange
    holidays come back empty and are simply skipped past.
    """
    feed = mcx_feed.DatewiseFeed(run.client, _cfg("datewise_backends", ["mcxlib", "mcxpy", "direct"]))
    last = state.get("last_day")
    day = (date.fromisoformat(last) - timedelta(days=int(_cfg("refetch_days", 5)))) if last \
        else max(history_start(), run.today - timedelta(days=int(_cfg("datewise_max_days", 30))))
    run.progress["futures"] = 0
    while day <= run.today:
        if day.weekday() < 5:
            via, records = feed.bhavcopy(day, mcx_feed.FUTURES)
            for rec in records:
                if str(rec.get("Symbol", "")).strip() in run.codes:
                    yield mcx_feed.bhavcopy_row(rec, run.commodity, extracted_via=f"{via}:datewise")
            state["last_day"] = day.isoformat()
        day += timedelta(days=1)


@dlt.resource(name="options_bhavcopy", write_disposition="merge", primary_key="bhavcopy_id",
              columns={**PRICE_COLUMNS, "strike_price": {"data_type": "double"}})
@annotate(
    source="mcx",
    concept="ContractSession",
    grain="one MCX option strike and type per contract expiry per trading day",
    description="MCX options-on-futures bhavcopy: each strike's daily premium OHLC, volume, "
                "turnover (₹ lakh) and open interest; `contract_id` names the expiry's chain",
    roles={**SESSION_ROLES, "strike_price": "unit_price", "option_type": "status_enum"},
    rename=SESSION_RENAME,
    currency="INR",
    links={"contract_id": "ExchangeContract"},
)
def options_bhavcopy(run: Run) -> Iterator[dict[str, Any]]:
    """Options history is short on purpose: a chain is hundreds of strikes a day,
    and what a desk reads from it — put/call ratio, max pain, the OI walls — is
    about the expiries still trading. `options_history_days` sets the depth."""
    state = dlt.current.resource_state()
    days = int(_cfg("options_history_days", 45))
    if days <= 0:
        run.progress["options"] = 0
        return
    windows = mcx_feed.plan(run.contracts(mcx_feed.OPTIONS), state.get("cursors", {}),
                            state.get("completed", []), run.today - timedelta(days=days),
                            run.today, int(_cfg("refetch_days", 5)))
    yield from mcx_feed.fetch_windows(run.client, _batch(run, "options", windows),
                                      run.commodity, state, run.today)


@dlt.resource(name="contract_master", write_disposition="merge", primary_key="contract_id",
              columns={"expiry_date": {"data_type": "date"}, "is_traded_today": {"data_type": "bool"}})
@annotate(
    source="mcx",
    concept="ExchangeContract",
    grain="one MCX futures contract or option expiry chain",
    description="Every contract MCX lists or has listed for the commodity — code, instrument, "
                "expiry — with whether it traded in the latest session",
    roles={
        "contract_id": "natural_key",
        "mcx_commodity": "status_enum",
        "contract_code": "free_text",
        "instrument_type": "status_enum",
        "expiry_date": "reference_date",
        "is_traded_today": "flag",
    },
)
def contract_master(run: Run) -> Iterator[dict[str, Any]]:
    floor = history_start()
    for instrument in (mcx_feed.FUTURES, mcx_feed.OPTIONS):
        for c in run.contracts(instrument):
            if c.expiry >= floor:
                yield mcx_feed.contract_row(c, run.commodity)


@dlt.source(name="mcx")
def mcx_source(commodity: str, max_contracts: int | None = None, run: Run | None = None):
    """One commodity's three resources. Pass `run` to read its `progress` afterwards."""
    run = run or new_run(commodity, max_contracts)
    return [contract_master(run), futures_bhavcopy(run), options_bhavcopy(run)]


def new_run(commodity: str, max_contracts: int | None = None,
            fetched: set[str] | None = None) -> Run:
    return Run(commodity=commodity, codes=mcx_feed.codes_for(commodity),
               client=mcx_feed.MCXClient(pause_s=float(_cfg("pause_seconds", 0.25))),
               today=today_ist(), max_contracts=max_contracts,
               # `is None`, not `or`: the caller's set starts empty, and `or`
               # would swap it for a fresh one the next batch never sees.
               fetched=set() if fetched is None else fetched)


def pipeline_name(commodity: str) -> str:
    """The `source_name` handed to `run_source`; the pipeline is `<project>_<this>`."""
    return f"mcx_{commodity}"


def load_commodity(wh: Any, commodity: str, max_contracts: int | None = None,
                   on_batch: Any = None) -> dict[str, Any]:
    """Load one commodity to completion, one committed batch at a time.

    Returns a summary: batches, rows landed per table (read back through dlt,
    not trusted from the load report), load ids.
    """
    from pf.runtime.dlt_runtime import run_source

    batch_size = max_contracts or int(_cfg("max_contracts_per_batch", 40))
    batches, load_ids, info, fetched = 0, [], {}, set()
    last_pending = 0
    while True:
        run = new_run(commodity, batch_size, fetched)
        info = run_source(wh, mcx_source(commodity, run=run), source_name=pipeline_name(commodity),
                          dataset=DATASET)
        batches += 1
        load_ids += info["load_ids"]
        pending = sum(run.progress.values())
        if on_batch:
            on_batch(batches, pending, info)
        if pending == 0:
            break
        if batches > 1 and pending >= last_pending:
            # Every batch must shrink the work left. One that does not is
            # re-planning what it already fetched, and would loop forever.
            raise RuntimeError(f"mcx {commodity}: batch {batches} made no progress "
                               f"({pending} contract(s) still pending)")
        last_pending = pending
    return {"commodity": commodity, "batches": batches, "load_ids": load_ids,
            "rows": info.get("rows", {}), "pipeline": info.get("pipeline")}


ALL = [contract_master, futures_bhavcopy, options_bhavcopy]


def main(argv: list[str]) -> int:
    from pf.runtime.warehouse import Warehouse

    wh = Warehouse.for_project(PROJECT_DIR, "commodity", "commodity-india")
    wanted = argv or list(mcx_feed.commodities())
    for commodity in wanted:
        summary = load_commodity(
            wh, commodity,
            on_batch=lambda n, pending, _i, c=commodity: print(f"  mcx {c}: batch {n}, {pending} contract(s) pending"))
        print(f"  mcx {commodity}: {summary['batches']} batch(es) → {summary['rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
