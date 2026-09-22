---
type: Metric
title: Avg Spread to Cheapest Market (ratio)
description: Mean spread as a share of the cheapest landed price, re-divided at query
  grain. Group by commodity and market.
okf_x_kind: ratio
okf_x_model: fct_market_spreads_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_spread_to_cheapest_ratio
---

# Definition

* **Kind:** `ratio`
* **Expression:** `sum(spread_to_cheapest_usd) / nullif(sum(cheapest_landed_usd), 0)`
* **Ratio:** `spread_usd_total` / `cheapest_usd_total` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_market_spreads_daily](/tables/fct_market_spreads_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `cheapest_market_code`, `is_cheapest_market`
* **Built from:** [cheapest_usd_total](/metrics/cheapest_usd_total.md), [spread_usd_total](/metrics/spread_usd_total.md)
