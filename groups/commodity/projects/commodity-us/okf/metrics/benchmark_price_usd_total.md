---
type: Metric
title: Benchmark Price Total (component)
description: Building block for avg_benchmark_price_usd. A sum of prices means nothing
  on its own.
okf_x_kind: simple
okf_x_model: fct_commodity_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:benchmark_price_usd_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(close_price)`
* **Built on:** [fct_commodity_prices_daily](/tables/fct_commodity_prices_daily.md)
* **Dimensions:** `commodity_id`, `price_basis`
* **Derived from it:** [avg_benchmark_price_usd](/metrics/avg_benchmark_price_usd.md)
