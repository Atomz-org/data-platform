---
type: Metric
title: FX Share (component)
description: ''
okf_x_kind: simple
okf_x_model: fct_landed_price_attribution_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:fx_share_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(fx_share_of_move)`
* **Built on:** [fct_landed_price_attribution_daily](/tables/fct_landed_price_attribution_daily.md)
* **Dimensions:** `commodity_id`, `currency_code`, `is_duty_rate_confirmed`, `market_code`, `primary_driver`
* **Derived from it:** [avg_fx_share_of_move](/metrics/avg_fx_share_of_move.md)
