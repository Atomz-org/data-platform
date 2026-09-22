---
type: Metric
title: Customs Duty Total (component)
description: Building block for avg_duty_local. A sum of per-unit duties means nothing
  on its own.
okf_x_kind: simple
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:duty_local_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(duty_local)`
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `currency_code`, `is_duty_rate_confirmed`, `market_code`, `market_unit`, `price_basis`
* **Derived from it:** [avg_duty_local](/metrics/avg_duty_local.md)
