---
type: Metric
title: Avg MCX Premium to Landed Parity — per Commodity
description: MCX settlement over benchmark × USD/INR × (1 + duty) for the same quote
  basis, minus one. Only commodities the family prices.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_avg_premium_to_landed
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_commodity_premium_total` / `mcx_commodity_premium_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_commodity_premium_days](/metrics/mcx_commodity_premium_days.md), [mcx_commodity_premium_total](/metrics/mcx_commodity_premium_total.md)
