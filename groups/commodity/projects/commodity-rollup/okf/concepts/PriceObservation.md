---
type: Concept
title: PriceObservation
description: One benchmark price for one commodity at one point in time. Never summed.
okf_x_defined_in: group
okf_x_parent: Event
okf_x_identity: quote_id
---

Declared in `groups/commodity/ontology/extension.yaml`, shared by every sister of `commodity`.

# Instantiated by

* [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* [fct_market_spreads_daily](/tables/fct_market_spreads_daily.md)
* [rpt_market_comparison_board](/tables/rpt_market_comparison_board.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `close_price` | decimal | unit_price |
| `commodity_id` | string | foreign_key |
| `currency_code` | string | currency_code |
| `quote_id` | string | natural_key |
| `traded_at` | timestamp | event_time |
| `volume` | integer | quantity |

# Relations

* PriceObservation is landed in Market — A landed price is one market's price; the benchmark it derives from belongs to none.
* PriceObservation prices Commodity — Every benchmark price belongs to exactly one commodity.
