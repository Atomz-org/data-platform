---
type: Metric
title: Period Return (flagship) — per Commodity
description: exp(Σ log return) − 1 over the query's window — compounding, not summing,
  daily returns.
okf_x_kind: derived
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_period_return
---

# Definition

* **Kind:** `derived`
* **Expression:** derived
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_commodity_log_return](/metrics/mcx_commodity_log_return.md)
