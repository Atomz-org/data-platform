---
type: Metric
title: Share of Sessions in Contango — per Commodity
description: ''
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_contango_share
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_commodity_contango_sessions` / `mcx_commodity_sessions` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_commodity_contango_sessions](/metrics/mcx_commodity_contango_sessions.md), [mcx_commodity_sessions](/metrics/mcx_commodity_sessions.md)
