---
type: Metric
title: Landed USD Total (component)
description: Building block for avg_landed_price_usd. A sum of prices means nothing
  on its own.
okf_x_kind: simple
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:landed_usd_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(landed_price_usd_per_quote_unit)`
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `price_basis`, `is_duty_rate_confirmed`
* **Derived from it:** [avg_import_parity_ratio](/metrics/avg_import_parity_ratio.md), [avg_landed_price_usd](/metrics/avg_landed_price_usd.md)
