---
type: Metric
title: Avg Import Parity Ratio
description: Landed over benchmark, both in USD per quote unit — 1.15 means landing
  adds 15%. Group by commodity and market.
okf_x_kind: ratio
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_import_parity_ratio
---

# Definition

* **Kind:** `ratio`
* **Expression:** `sum(landed_price_usd_per_quote_unit) / nullif(sum(case when landed_price_usd_per_quote_unit is not null then benchmark_price_usd end), 0)`
* **Ratio:** `landed_usd_total` / `benchmark_usd_total_where_landed` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `price_basis`, `is_duty_rate_confirmed`
