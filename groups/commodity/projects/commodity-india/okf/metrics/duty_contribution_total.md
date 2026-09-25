---
type: Metric
title: Duty Contribution (component)
description: ''
okf_x_kind: simple
okf_x_model: fct_landed_price_attribution_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:duty_contribution_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(duty_contribution_pct)`
* **Built on:** [fct_landed_price_attribution_daily](/tables/fct_landed_price_attribution_daily.md)
* **Dimensions:** `commodity_id`, `currency_code`, `is_duty_rate_confirmed`, `market_code`, `primary_driver`
