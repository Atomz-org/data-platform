---
type: Metric
title: Futures Turnover (₹) — per Commodity
description: Traded value of every code and expiry of the commodity, in rupees. Additive
  across commodities and days.
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_turnover_inr
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(turnover_inr)`
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Derived from it:** [mcx_commodity_mini_turnover_share](/metrics/mcx_commodity_mini_turnover_share.md), [mcx_commodity_turnover_mom](/metrics/mcx_commodity_turnover_mom.md)
