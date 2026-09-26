---
type: Metric
title: MCX Futures Volume (lots)
description: Lots traded across every expiry. Additive within a code; a GOLD lot is
  not a GOLDPETAL lot, so compare across codes with turnover instead.
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_volume_lots
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(volume_lots)`
* **Built on:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md)
* **Dimensions:** `contract_code`, `curve_state`, `ema_9_21_signal`, `is_backwardation`, `is_contango`, `is_flagship`, `mcx_commodity`, `oi_buildup`, `segment`, `stance`, `trend_regime`, `volatility_regime`
