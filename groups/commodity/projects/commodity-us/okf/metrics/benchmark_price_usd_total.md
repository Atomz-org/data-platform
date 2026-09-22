---
type: Metric
title: Benchmark Price Total (component)
description: Building block for avg_benchmark_price_usd. A sum of prices means nothing
  on its own.
okf_x_kind: simple
okf_x_model: fct_commodity_prices_daily
okf_x_time_column: price_date
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(close_price)`
* **Built on:** [fct_commodity_prices_daily](/tables/fct_commodity_prices_daily.md)
* **Dimensions:** `commodity_id`, `price_basis`
