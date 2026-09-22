---
type: Metric
title: Customs Duty Total (component)
description: Building block for avg_duty_local. A sum of per-unit duties means nothing
  on its own.
okf_x_kind: simple
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(duty_local)`
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `currency_code`, `market_unit`, `is_duty_rate_confirmed`, `price_basis`
