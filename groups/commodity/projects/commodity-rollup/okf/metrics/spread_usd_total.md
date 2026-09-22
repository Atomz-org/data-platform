---
type: Metric
title: Spread Total (component)
description: Building block for avg_spread_to_cheapest_usd.
okf_x_kind: simple
okf_x_model: fct_market_spreads_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:spread_usd_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(spread_to_cheapest_usd)`
* **Built on:** [fct_market_spreads_daily](/tables/fct_market_spreads_daily.md)
* **Dimensions:** `cheapest_market_code`, `commodity_id`, `is_cheapest_market`, `market_code`
* **Derived from it:** [avg_spread_to_cheapest_ratio](/metrics/avg_spread_to_cheapest_ratio.md), [avg_spread_to_cheapest_usd](/metrics/avg_spread_to_cheapest_usd.md)
