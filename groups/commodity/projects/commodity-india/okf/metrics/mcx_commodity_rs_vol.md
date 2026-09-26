---
type: Metric
title: Rogers–Satchell Volatility (annualised) — per Commodity
description: ''
okf_x_kind: derived
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_rs_vol
---

# Definition

* **Kind:** `derived`
* **Expression:** derived
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_commodity_rs_variance](/metrics/mcx_commodity_rs_variance.md)
