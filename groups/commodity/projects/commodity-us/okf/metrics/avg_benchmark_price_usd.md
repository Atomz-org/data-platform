---
type: Metric
title: Avg Benchmark Price (USD)
description: Mean daily settlement price, USD per quote unit. Group by commodity.
okf_x_kind: ratio
okf_x_model: fct_commodity_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_benchmark_price_usd
---

# Definition

* **Kind:** `ratio`
* **Expression:** `sum(close_price) / nullif(count(close_price), 0)`
* **Ratio:** `benchmark_price_usd_total` / `benchmark_price_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_commodity_prices_daily](/tables/fct_commodity_prices_daily.md)
* **Dimensions:** `commodity_id`, `price_basis`
