---
type: Metric
title: MCX Futures Turnover (₹)
description: Traded value across every expiry, in rupees. Additive across codes and
  days.
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_turnover_inr
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(turnover_inr)`
* **Built on:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md)
* **Dimensions:** `contract_code`, `curve_state`, `ema_9_21_signal`, `is_backwardation`, `is_contango`, `is_flagship`, `mcx_commodity`, `oi_buildup`, `segment`, `stance`, `trend_regime`, `volatility_regime`
