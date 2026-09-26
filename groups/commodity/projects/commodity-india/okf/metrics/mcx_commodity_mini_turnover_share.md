---
type: Metric
title: Mini-Contract Share of Turnover — per Commodity
description: Turnover in the non-flagship codes (GOLDM, SILVERMIC, CRUDEOILM, ...)
  over all turnover — how retail the commodity's book is.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_mini_turnover_share
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_commodity_mini_turnover_inr` / `mcx_commodity_turnover_inr` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_commodity_mini_turnover_inr](/metrics/mcx_commodity_mini_turnover_inr.md), [mcx_commodity_turnover_inr](/metrics/mcx_commodity_turnover_inr.md)
