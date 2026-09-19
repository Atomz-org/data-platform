"""gold-api.com spot source for commodity-india.

Free, keyless spot quotes for the four precious metals — the tracker's fallback
when Yahoo futures are unavailable. The endpoint returns only the latest quote,
so history accumulates one row per update the pipeline happens to observe.

A backup feed failing is logged, not raised: the futures feed is the source of
record, and a gold-api outage must not fail the whole load.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import dlt
from dlt.sources.helpers import requests
from pf.ontology import annotate

from commodity_india.catalog import COMMODITIES

log = logging.getLogger(__name__)

SPOT_URL = "https://api.gold-api.com/price/{symbol}"


@dlt.resource(
    name="spot_prices",
    write_disposition="merge",
    primary_key="spot_quote_id",
    columns={"price": {"data_type": "double"}, "updated_at": {"data_type": "timestamp"}},
)
@annotate(
    source="gold_api",
    concept="PriceObservation",
    grain="one precious metal per gold-api update",
    description="Latest precious-metal spot quotes from gold-api.com, USD per troy ounce",
    roles={
        "spot_quote_id": "natural_key",
        "price": "unit_price",
        "currency": "currency_code",
        "quote_unit": "unit_of_measure",
        "updated_at": "event_time",
    },
    rename={"price": "spot_price", "currency": "currency_code", "updated_at": "quoted_at"},
    links={"commodity_id": "Commodity"},
)
def spot_prices() -> Iterator[dict[str, Any]]:
    for c in COMMODITIES:
        if not c.spot_symbol:
            continue
        try:
            resp = requests.get(SPOT_URL.format(symbol=c.spot_symbol), timeout=15)
            resp.raise_for_status()
            body = resp.json()
        except Exception as exc:  # noqa: BLE001 — backup feed, see module docstring
            log.warning("gold_api: %s failed: %s", c.spot_symbol, exc)
            continue
        if body.get("price") is None or not body.get("updatedAt"):
            continue
        yield {
            "spot_quote_id": f"{c.commodity_id}:{body['updatedAt']}",
            "commodity_id": c.commodity_id,
            "symbol": c.spot_symbol,
            "price": body["price"],
            "currency": body.get("currency") or "USD",
            "quote_unit": "troy_oz",
            "updated_at": body["updatedAt"],
        }


@dlt.source(name="gold_api")
def gold_api_source():
    return [spot_prices()]


ALL = [spot_prices]
