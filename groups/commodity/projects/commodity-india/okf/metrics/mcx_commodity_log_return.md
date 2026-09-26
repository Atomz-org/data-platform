---
type: Metric
title: Period Log Return (flagship) — per Commodity
description: Sum of the flagship's roll-free daily log returns — additive over time;
  exp(x) − 1 is the period return.
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_log_return
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(log_return_1d)`
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Derived from it:** [mcx_commodity_period_return](/metrics/mcx_commodity_period_return.md)
