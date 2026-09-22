---
type: Metric
title: Landed USD Total (component)
description: Building block for avg_landed_price_usd. A sum of prices means nothing
  on its own.
okf_x_kind: simple
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(landed_price_usd_per_quote_unit)`
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `price_basis`, `is_duty_rate_confirmed`
