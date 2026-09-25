---
type: Metric
title: Attribution Days
description: ''
okf_x_kind: simple
okf_x_model: fct_landed_price_attribution_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:attribution_days
---

# Definition

* **Kind:** `simple`
* **Expression:** `count(price_id)`
* **Built on:** [fct_landed_price_attribution_daily](/tables/fct_landed_price_attribution_daily.md)
* **Dimensions:** `commodity_id`, `currency_code`, `is_duty_rate_confirmed`, `market_code`, `primary_driver`
