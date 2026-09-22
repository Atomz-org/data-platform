---
type: Metric
title: Days as Cheapest Market
description: Days a market was the cheapest place to land a commodity. Group by commodity
  and market.
okf_x_kind: simple
okf_x_model: fct_market_spreads_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:days_as_cheapest_market
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(case when is_cheapest_market then 1 else 0 end)`
* **Built on:** [fct_market_spreads_daily](/tables/fct_market_spreads_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `cheapest_market_code`, `is_cheapest_market`
