---
type: Metric
title: Days With a Comparable Landed Price
description: Days a market landed a commodity, restated in USD per quote unit.
okf_x_kind: simple
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
---

# Definition

* **Kind:** `simple`
* **Expression:** `count(landed_price_usd_per_quote_unit)`
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `price_basis`, `is_duty_rate_confirmed`
