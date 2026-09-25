---
type: Metric
title: Avg Rupee Share of the Move
description: Share of the 20-day landed move attributable to USD/INR rather than the
  benchmark or duty. High means the commodity call and the currency call have come
  apart, and timing the commodity will not recover the cost.
okf_x_kind: ratio
okf_x_model: fct_landed_price_attribution_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_fx_share_of_move
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `fx_share_total` / `fx_share_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_landed_price_attribution_daily](/tables/fct_landed_price_attribution_daily.md)
* **Dimensions:** `commodity_id`, `currency_code`, `is_duty_rate_confirmed`, `market_code`, `primary_driver`
* **Built from:** [fx_share_days](/metrics/fx_share_days.md), [fx_share_total](/metrics/fx_share_total.md)
