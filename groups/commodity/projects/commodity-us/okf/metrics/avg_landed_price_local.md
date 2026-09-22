---
type: Metric
title: Avg Landed Price (market currency)
description: Mean import landed price in this market's currency per its market unit
  (benchmark × USD/local × (1 + duty)). Group by commodity; filter landed_price__is_duty_rate_confirmed
  to exclude history priced at a back-applied duty rate.
okf_x_kind: ratio
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_landed_price_local
---

# Definition

* **Kind:** `ratio`
* **Expression:** `sum(landed_price_local) / nullif(count(landed_price_local), 0)`
* **Ratio:** `landed_price_local_total` / `landed_price_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `currency_code`, `market_unit`, `is_duty_rate_confirmed`, `price_basis`
