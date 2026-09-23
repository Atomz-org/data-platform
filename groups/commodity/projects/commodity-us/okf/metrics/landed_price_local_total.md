---
type: Metric
title: Landed Price Total (component)
description: Building block for avg_landed_price_local. A sum of prices means nothing
  on its own.
okf_x_kind: simple
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:landed_price_local_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(landed_price_local)`
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `currency_code`, `is_duty_rate_confirmed`, `market_code`, `market_unit`, `price_basis`
* **Derived from it:** [avg_landed_price_local](/metrics/avg_landed_price_local.md)
