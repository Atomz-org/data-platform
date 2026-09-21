"""The sisters, as a dlt source: the roll-up's raw stage is their conformed marts.

Every sister builds `fct_landed_prices_daily` in the same shape; this source
reads each one READ_ONLY (`commodity_shared.sisters`) and lands the union in
this warehouse's `sisters` dataset, replaced on every run because it is a
snapshot of what the sisters have built, not a stream. dbt stages it like any
other raw table, so lineage runs sister mart → dlt resource → `stg_` → marts.

A sister whose columns differ is refused before a row is read. `price_id` is
unique within a sister but repeats across them (`gold:2026-09-16` in every
market), so the natural key here is market-qualified.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import dlt
import pyarrow as pa
import pyarrow.compute as pc
from commodity_shared import sisters
from pf.ontology import annotate

from commodity_rollup.roster import sister_paths


def _keyed(batch: pa.RecordBatch) -> pa.RecordBatch:
    key = pc.binary_join_element_wise(batch.column("market_code"), batch.column("price_id"), ":")
    return batch.append_column("landed_price_id", key)


@dlt.resource(name="landed_prices", write_disposition="replace", primary_key="landed_price_id")
@annotate(
    source="sisters",
    concept="PriceObservation",
    grain="one commodity per market per price date",
    description="Every sister's conformed daily landed price, in her own currency per "
                "her market unit, with the benchmark, FX rate and duty it was built from",
    roles={
        "landed_price_id": "natural_key",
        "price_date": "event_time",
        "price_basis": "status_enum",
        "quote_unit": "unit_of_measure",
        "market_unit": "unit_of_measure",
        "currency_code": "currency_code",
        "benchmark_price_usd": "unit_price",
        "benchmark_usd_per_market_unit": "unit_price",
        "usd_fx_rate": "exchange_rate",
        "fx_fixed_on": "reference_date",
        "effective_duty_rate": "rate_fraction",
        "is_import_prohibited": "flag",
        "is_duty_rate_confirmed": "flag",
        "assessable_value_local": "unit_price",
        "duty_local": "unit_price",
        "landed_price_local": "unit_price",
        "landed_price_change_local": "unit_price",
        "landed_price_change_pct": "rate_fraction",
    },
    links={"commodity_id": "Commodity", "market_code": "Market"},
)
def landed_prices() -> Iterator[Any]:
    for batch in sisters.read_mart(sister_paths(), "fct_landed_prices_daily"):
        yield _keyed(batch)


@dlt.source(name="sisters")
def sisters_source():
    return [landed_prices()]


ALL = [landed_prices]
