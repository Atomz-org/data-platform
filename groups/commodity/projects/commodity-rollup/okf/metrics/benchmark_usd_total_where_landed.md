---
type: Metric
title: Benchmark USD Total, landed days (component)
description: Building block for avg_import_parity_ratio — the benchmark on exactly
  the days a landed price exists.
okf_x_kind: simple
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:benchmark_usd_total_where_landed
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(case when landed_price_usd_per_quote_unit is not null then benchmark_price_usd end)`
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `price_basis`, `is_duty_rate_confirmed`
* **Derived from it:** [avg_import_parity_ratio](/metrics/avg_import_parity_ratio.md)
