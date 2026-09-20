"""What commodity-us tracks, and the market it lands them in.

The catalog itself is the group's — `commodity_shared.catalog` reads the
conformed `commodities` and `markets` seeds — so every sister prices the same
`gold` and the roll-up can line them up. What is the US's here is the selection
(every benchmark: these are the home exchanges of most of them) and the market
row: USD, COMEX, New York.

Market facts — the unit US markets quote in, customs duty, CME/ICE contract
specifications — are this project's dbt seeds, not this module's.
"""

from __future__ import annotations

from commodity_shared.catalog import Commodity, Market, commodities, market

MARKET: Market = market("US")

#: Every catalogued benchmark. Narrow with `commodities(tracked=[...])` when a
#: market follows a subset.
COMMODITIES: tuple[Commodity, ...] = commodities()

#: Currencies fixed against USD every day. This market prices in USD, so its
#: own rate is 1 and none is fetched; these are the reference rates the desk
#: shows beside the board — the currencies its counterparties settle in.
FX_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "JPY", "CNY", "CAD", "MXN", "INR")
