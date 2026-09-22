---
type: Metric
title: Avg Landed Price (USD per quote unit)
description: Mean landed price on the benchmark's footing. Group by commodity and
  market; this is the number that compares.
okf_x_kind: ratio
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_landed_price_usd
---

# Definition

* **Kind:** `ratio`
* **Expression:** `sum(landed_price_usd_per_quote_unit) / nullif(count(landed_price_usd_per_quote_unit), 0)`
* **Ratio:** `landed_usd_total` / `landed_usd_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `price_basis`, `is_duty_rate_confirmed`
* **Built from:** [landed_usd_days](/metrics/landed_usd_days.md), [landed_usd_total](/metrics/landed_usd_total.md)
