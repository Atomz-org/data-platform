"""gold-api.com spot connector, declared as a dlt `rest_api` source.

Free, keyless spot quotes for the precious metals — the fallback when Yahoo
futures are unavailable. The endpoint returns only the latest quote, so history
accumulates one row per update the pipeline happens to observe.

Declared, not hand-rolled: `dlt.sources.rest_api` (dlt Core) owns the client,
the request per symbol and the response handling. The symbol list is a parent
resource the `price/{symbol}` endpoint resolves against, so adding a metal to
the catalog is the whole change. The feed's extra fields land untouched in the
raw table; staging selects the annotated columns and nothing else.

A backup feed failing is ignored, not raised: a 429 or 5xx for one symbol skips
that symbol, and each sister's seed records a failed gold-api run as a warning.

`spot_prices(commodities)` returns the generated resource without an annotation;
the sister applies its own, because the annotation is the sister's contract with
its staging layer.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

import dlt
from dlt.sources.rest_api import rest_api_resources
from dlt.sources.rest_api.typing import RESTAPIConfig

from commodity_shared.catalog import Commodity

BASE_URL = "https://api.gold-api.com/"
QUOTE_UNIT = "troy_oz"


def spot_symbols(commodities: Iterable[Commodity]):
    symbols = [{"symbol": c.spot_symbol, "commodity_id": c.commodity_id}
               for c in commodities if c.spot_symbol]

    @dlt.resource(name="spot_symbols", selected=False)
    def _symbols() -> Iterator[list[dict[str, str]]]:
        """The catalogued spot symbols, as one page.

        A dependent rest_api resource iterates whatever its parent yields, so
        this yields the list once rather than one symbol at a time — one dict
        per yield would be iterated as its keys. Unselected: not a table.
        """
        yield symbols

    return _symbols


def is_quote(row: dict[str, Any]) -> bool:
    return row.get("price") is not None and bool(row.get("updatedAt"))


def stamp(row: dict[str, Any]) -> dict[str, Any]:
    """Key and unit the quote the way the sisters' annotation describes it."""
    row["commodity_id"] = row.pop("_spot_symbols_commodity_id")
    row["spot_quote_id"] = f"{row['commodity_id']}:{row['updatedAt']}"
    row["quote_unit"] = QUOTE_UNIT
    return row


def rest_config(commodities: Iterable[Commodity]) -> RESTAPIConfig:
    return {
        "client": {"base_url": BASE_URL},
        "resources": [
            spot_symbols(commodities),
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
                "processing_steps": [{"filter": is_quote}, {"map": stamp}],
                "write_disposition": "merge",
                "primary_key": "spot_quote_id",
                # dlt snake-cases the feed's camelCase: `updatedAt` lands as
                # `updated_at`, which is the column the annotation names and
                # the name a hint must use — hinting `updatedAt` makes dlt
                # merge two columns and warn about it on every load.
                "columns": {"price": {"data_type": "double"},
                            "updated_at": {"data_type": "timestamp"}},
            },
        ],
    }


def spot_prices(commodities: Iterable[Commodity]):
    """The `spot_prices` transformer dlt generates from the config, carrying its
    unselected parent with it. Annotate it in the sister."""
    commodities = tuple(commodities)
    return next(r for r in rest_api_resources(rest_config(commodities)) if r.name == "spot_prices")
