---
type: Metric
title: Avg MCX RSI(14)
description: Wilder RSI on the roll-free continuous series. Group by contract_code.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:avg_mcx_rsi
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_rsi_total` / `mcx_rsi_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md)
* **Dimensions:** `contract_code`, `curve_state`, `ema_9_21_signal`, `is_backwardation`, `is_contango`, `is_flagship`, `mcx_commodity`, `oi_buildup`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_rsi_days](/metrics/mcx_rsi_days.md), [mcx_rsi_total](/metrics/mcx_rsi_total.md)
