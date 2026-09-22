---
type: Metric
title: Avg Customs Duty (market currency)
description: Mean customs duty per market unit, in this market's currency. Group by
  commodity.
okf_x_kind: ratio
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
---

# Definition

* **Kind:** `ratio`
* **Expression:** `sum(duty_local) / nullif(count(landed_price_local), 0)`
* **Ratio:** `duty_local_total` / `landed_price_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `currency_code`, `market_unit`, `is_duty_rate_confirmed`, `price_basis`
