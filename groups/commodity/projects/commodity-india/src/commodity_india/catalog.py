"""What commodity-india tracks, and the market it lands them in.

The catalog itself is the group's — `commodity_shared.catalog` reads the
conformed `commodities` and `markets` seeds — so every sister prices the same
`gold` and the roll-up can line them up. What is India's here is the selection
(every benchmark the tracker follows) and the market row: INR, MCX, Kolkata.

Market facts — the unit Indian markets quote in, customs duty, MCX contract
lots, retail purities — are this project's dbt seeds, not this module's.
"""

from __future__ import annotations

from commodity_shared.catalog import Commodity, Market, commodities, market

MARKET: Market = market("IN")

#: Every catalogued benchmark. Narrow with `commodities(tracked=[...])` when a
#: market follows a subset.
COMMODITIES: tuple[Commodity, ...] = commodities()

#: Currencies fixed against USD every day. The market's own currency drives the
#: landed price; the rest are the reference rates the tracker shows beside it.
FX_CURRENCIES: tuple[str, ...] = (MARKET.currency_code, "EUR", "GBP", "JPY", "CNY", "AED", "CAD")
