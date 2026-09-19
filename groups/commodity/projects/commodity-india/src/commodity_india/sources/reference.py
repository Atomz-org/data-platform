"""Reference source for commodity-india: the tracked commodity catalog.

Loaded from `commodity_india.catalog`, the same list the price sources fetch
from, so the catalog in the warehouse is always exactly what is being priced.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import dlt
from pf.ontology import annotate

from commodity_india.catalog import COMMODITIES


@dlt.resource(name="commodities", write_disposition="replace", primary_key="commodity_id")
@annotate(
    source="reference",
    concept="Commodity",
    grain="one tracked commodity",
    description="Every commodity the tracker prices, with its benchmark, exchange "
                "and the unit the benchmark is quoted per",
    roles={
        "commodity_id": "natural_key",
        "commodity_name": "free_text",
        "category": "status_enum",
        "segment": "status_enum",
        "exchange": "status_enum",
        "quote_unit": "unit_of_measure",
        "price_basis": "status_enum",
        "yahoo_symbol": "free_text",
        "spot_symbol": "free_text",
    },
)
def commodities() -> Iterator[dict[str, Any]]:
    for c in COMMODITIES:
        yield {
            "commodity_id": c.commodity_id,
            "commodity_name": c.commodity_name,
            "category": c.category,
            "segment": c.segment,
            "exchange": c.exchange,
            "quote_unit": c.quote_unit,
            "price_basis": c.price_basis,
            "yahoo_symbol": c.yahoo_symbol,
            "spot_symbol": c.spot_symbol,
        }


@dlt.source(name="reference")
def reference_source():
    return [commodities()]


ALL = [commodities]
