---
type: Metric
title: Avg MCX Roll Yield (annualised)
description: What a long earns rolling the near month into the next, annualised —
  negative in contango, positive in backwardation. Group by contract_code.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:avg_mcx_roll_yield
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_roll_yield_total` / `mcx_roll_yield_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md)
* **Dimensions:** `contract_code`, `curve_state`, `ema_9_21_signal`, `is_backwardation`, `is_contango`, `is_flagship`, `mcx_commodity`, `oi_buildup`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_roll_yield_days](/metrics/mcx_roll_yield_days.md), [mcx_roll_yield_total](/metrics/mcx_roll_yield_total.md)
