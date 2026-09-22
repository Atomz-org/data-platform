---
type: Metric
title: Avg Spread to Cheapest Market (USD)
description: Mean USD per quote unit a market pays over the cheapest market that day.
  Group by commodity and market.
okf_x_kind: ratio
okf_x_model: fct_market_spreads_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_spread_to_cheapest_usd
---

# Definition

* **Kind:** `ratio`
* **Expression:** `sum(spread_to_cheapest_usd) / nullif(count(spread_to_cheapest_usd), 0)`
* **Ratio:** `spread_usd_total` / `spread_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_market_spreads_daily](/tables/fct_market_spreads_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `cheapest_market_code`, `is_cheapest_market`
