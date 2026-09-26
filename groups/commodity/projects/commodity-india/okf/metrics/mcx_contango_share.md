---
type: Metric
title: MCX Share of Sessions in Contango
description: Contango sessions over all sessions. Group by contract_code.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_contango_share
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_contango_days` / `mcx_session_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md)
* **Dimensions:** `contract_code`, `curve_state`, `ema_9_21_signal`, `is_backwardation`, `is_contango`, `is_flagship`, `mcx_commodity`, `oi_buildup`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_contango_days](/metrics/mcx_contango_days.md), [mcx_session_days](/metrics/mcx_session_days.md)
