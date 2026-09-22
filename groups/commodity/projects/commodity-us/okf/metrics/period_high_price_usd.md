---
type: Metric
title: Period High (USD)
description: Highest traded price in the period, USD per quote unit. Group by commodity.
okf_x_kind: simple
okf_x_model: fct_commodity_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:period_high_price_usd
---

# Definition

* **Kind:** `simple`
* **Expression:** `max(coalesce(high_price, close_price))`
* **Built on:** [fct_commodity_prices_daily](/tables/fct_commodity_prices_daily.md)
* **Dimensions:** `commodity_id`, `price_basis`
