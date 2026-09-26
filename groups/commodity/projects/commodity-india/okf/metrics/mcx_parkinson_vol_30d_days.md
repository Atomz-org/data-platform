---
type: Metric
title: MCX Days With a Parkinson Reading
description: ''
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_parkinson_vol_30d_days
---

# Definition

* **Kind:** `simple`
* **Expression:** `count(parkinson_vol_30d)`
* **Built on:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md)
* **Dimensions:** `contract_code`, `curve_state`, `ema_9_21_signal`, `is_backwardation`, `is_contango`, `is_flagship`, `mcx_commodity`, `oi_buildup`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Derived from it:** [avg_mcx_parkinson_vol_30d](/metrics/avg_mcx_parkinson_vol_30d.md)
