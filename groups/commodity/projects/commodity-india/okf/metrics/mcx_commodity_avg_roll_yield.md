---
type: Metric
title: Avg Roll Yield (annualised) — per Commodity
description: What a long earned rolling the flagship's near month into the next, annualised.
  Negative in contango.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_avg_roll_yield
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_commodity_roll_yield_total` / `mcx_commodity_roll_yield_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_commodity_roll_yield_days](/metrics/mcx_commodity_roll_yield_days.md), [mcx_commodity_roll_yield_total](/metrics/mcx_commodity_roll_yield_total.md)
