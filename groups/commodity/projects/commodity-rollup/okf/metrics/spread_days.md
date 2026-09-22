---
type: Metric
title: Days Compared
description: Days at least two markets priced the commodity.
okf_x_kind: simple
okf_x_model: fct_market_spreads_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:spread_days
---

# Definition

* **Kind:** `simple`
* **Expression:** `count(spread_to_cheapest_usd)`
* **Built on:** [fct_market_spreads_daily](/tables/fct_market_spreads_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `cheapest_market_code`, `is_cheapest_market`
* **Derived from it:** [avg_spread_to_cheapest_usd](/metrics/avg_spread_to_cheapest_usd.md)
