---
type: Metric
title: Avg MCX Daily Return
description: Mean roll-free daily return of the most-active contract. Group by contract_code.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:avg_mcx_daily_return
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_return_total` / `mcx_session_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md)
* **Dimensions:** `contract_code`, `curve_state`, `ema_9_21_signal`, `is_backwardation`, `is_contango`, `is_flagship`, `mcx_commodity`, `oi_buildup`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_return_total](/metrics/mcx_return_total.md), [mcx_session_days](/metrics/mcx_session_days.md)
