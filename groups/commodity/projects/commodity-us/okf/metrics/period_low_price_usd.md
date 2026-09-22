---
type: Metric
title: Period Low (USD)
description: Lowest traded price in the period, USD per quote unit. Group by commodity.
okf_x_kind: simple
okf_x_model: fct_commodity_prices_daily
okf_x_time_column: price_date
---

# Definition

* **Kind:** `simple`
* **Expression:** `min(coalesce(low_price, close_price))`
* **Built on:** [fct_commodity_prices_daily](/tables/fct_commodity_prices_daily.md)
* **Dimensions:** `commodity_id`, `price_basis`
