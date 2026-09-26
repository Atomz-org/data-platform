---
type: Metric
title: Avg RSI(14) (flagship) — per Commodity
description: ''
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_avg_rsi
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_commodity_rsi_total` / `mcx_commodity_rsi_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_commodity_rsi_days](/metrics/mcx_commodity_rsi_days.md), [mcx_commodity_rsi_total](/metrics/mcx_commodity_rsi_total.md)
