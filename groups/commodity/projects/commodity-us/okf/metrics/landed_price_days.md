---
type: Metric
title: Days With a Landed Price
description: Days a landed price exists — never for commodities this market prohibits
  importing.
okf_x_kind: simple
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:landed_price_days
---

# Definition

* **Kind:** `simple`
* **Expression:** `count(landed_price_local)`
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `currency_code`, `market_unit`, `is_duty_rate_confirmed`, `price_basis`
