---
type: Metric
title: MCX Sessions in Contango
description: ''
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_contango_days
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(case when is_contango then 1 else 0 end)`
* **Built on:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md)
* **Dimensions:** `contract_code`, `curve_state`, `ema_9_21_signal`, `is_backwardation`, `is_contango`, `is_flagship`, `mcx_commodity`, `oi_buildup`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Derived from it:** [mcx_contango_share](/metrics/mcx_contango_share.md)
