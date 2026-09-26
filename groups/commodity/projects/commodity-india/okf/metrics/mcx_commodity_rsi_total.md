---
type: Metric
title: RSI (component) — per Commodity
description: ''
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_rsi_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(rsi_14)`
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Derived from it:** [mcx_commodity_avg_rsi](/metrics/mcx_commodity_avg_rsi.md)
