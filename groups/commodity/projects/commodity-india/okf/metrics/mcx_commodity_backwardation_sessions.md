---
type: Metric
title: Sessions in Backwardation — per Commodity
description: ''
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_backwardation_sessions
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(is_backwardation_session)`
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Derived from it:** [mcx_commodity_backwardation_share](/metrics/mcx_commodity_backwardation_share.md)
