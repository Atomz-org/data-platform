"""gold-api.com spot source for commodity-india, declared as a dlt REST source.

Free, keyless spot quotes for the four precious metals — the tracker's fallback
when Yahoo futures are unavailable. The endpoint returns only the latest quote,
so history accumulates one row per update the pipeline happens to observe.

Declared, not hand-rolled: `dlt.sources.rest_api` (dlt Core) owns the client,
the request per symbol and the response handling. The symbol list is a parent
resource the `price/{symbol}` endpoint resolves against, so adding a metal to
the catalog is the whole change. The feed's extra fields land untouched in the
raw table; staging selects the annotated columns and nothing else.

A backup feed failing is ignored, not raised: a 429 or 5xx for one symbol skips
that symbol, and `seed.py` records a failed gold-api run as a warning. The
futures feed is the source of record, and a gold-api outage must not fail it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import dlt
from dlt.sources.rest_api import rest_api_resources
from dlt.sources.rest_api.typing import RESTAPIConfig
from pf.ontology import annotate

from commodity_india.catalog import COMMODITIES

BASE_URL = "https://api.gold-api.com/"


@dlt.resource(name="spot_symbols", selected=False)
def spot_symbols() -> Iterator[list[dict[str, str]]]:
    """The catalogued spot symbols, as one page.

    A dependent rest_api resource iterates whatever its parent yields, so this
    yields the list once rather than one symbol at a time — one dict per yield
    would be iterated as its keys. Unselected: the list is not a table.
    """
    yield [{"symbol": c.spot_symbol, "commodity_id": c.commodity_id}
           for c in COMMODITIES if c.spot_symbol]


def _is_quote(row: dict[str, Any]) -> bool:
    return row.get("price") is not None and bool(row.get("updatedAt"))


def _stamp(row: dict[str, Any]) -> dict[str, Any]:
    """Key and unit the quote the way the annotation describes it."""
    row["commodity_id"] = row.pop("_spot_symbols_commodity_id")
    row["spot_quote_id"] = f"{row['commodity_id']}:{row['updatedAt']}"
    row["quote_unit"] = "troy_oz"
    return row


def rest_config() -> RESTAPIConfig:
    return {
        "client": {"base_url": BASE_URL},
        "resources": [
            spot_symbols,
            {
                "name": "spot_prices",
                "endpoint": {
                    "path": "price/{symbol}",
                    "params": {"symbol": {"type": "resolve", "resource": "spot_symbols",
                                          "field": "symbol"}},
                    # Backup feed: a symbol the API cannot serve right now is
                    # skipped for this run, not fatal for the load.
                    "response_actions": [{"status_code": code, "action": "ignore"}
                                         for code in (404, 429, 500, 502, 503, 504)],
                },
                "include_from_parent": ["commodity_id"],
                "processing_steps": [{"filter": _is_quote}, {"map": _stamp}],
                "write_disposition": "merge",
                "primary_key": "spot_quote_id",
                # dlt snake-cases the feed's camelCase: `updatedAt` lands as
                # `updated_at`, which is the column the annotation names.
                "columns": {"price": {"data_type": "double"},
                            "updatedAt": {"data_type": "timestamp"}},
            },
        ],
    }


annotate_spot_prices = annotate(
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

# Built once at import so the annotation registers, exactly as a decorated
# resource's would; `annotate(...)(resource)` is the decorator applied to a
# resource dlt generated from config rather than from a function.
spot_prices = annotate_spot_prices(
    next(r for r in rest_api_resources(rest_config()) if r.name == "spot_prices"))


@dlt.source(name="gold_api")
def gold_api_source():
    # The transformer carries its (unselected) parent with it.
    return [spot_prices]


ALL = [spot_prices]
