"""gold-api.com spot quotes for commodity-india: the precious-metal backup feed.

The declarative `rest_api` source is the group's (`commodity_shared.gold_api`);
this module annotates the resource it generates for India's catalog, which is
what puts it in this project's staging layer and knowledge graph.
"""

from __future__ import annotations

import dlt
from commodity_shared import gold_api
from pf.ontology import annotate

from commodity_india.catalog import COMMODITIES

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
spot_prices = annotate_spot_prices(gold_api.spot_prices(COMMODITIES))


@dlt.source(name="gold_api")
def gold_api_source():
    # The transformer carries its (unselected) parent with it.
    return [spot_prices]


ALL = [spot_prices]
