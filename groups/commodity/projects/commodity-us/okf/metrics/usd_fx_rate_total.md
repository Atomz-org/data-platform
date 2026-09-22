---
type: Metric
title: Applied FX Rate Total (component)
description: Building block for avg_usd_fx_rate — the rate each landed price actually
  used.
okf_x_kind: simple
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:usd_fx_rate_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(usd_fx_rate)`
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `currency_code`, `market_unit`, `is_duty_rate_confirmed`, `price_basis`
* **Derived from it:** [avg_usd_fx_rate](/metrics/avg_usd_fx_rate.md)
