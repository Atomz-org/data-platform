---
type: Metric
title: Cheapest Landed Total (component)
description: Building block for avg_spread_to_cheapest_ratio.
okf_x_kind: simple
okf_x_model: fct_market_spreads_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:cheapest_usd_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(cheapest_landed_usd)`
* **Built on:** [fct_market_spreads_daily](/tables/fct_market_spreads_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `cheapest_market_code`, `is_cheapest_market`
* **Derived from it:** [avg_spread_to_cheapest_ratio](/metrics/avg_spread_to_cheapest_ratio.md)
