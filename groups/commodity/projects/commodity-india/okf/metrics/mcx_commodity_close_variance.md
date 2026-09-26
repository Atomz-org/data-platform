---
type: Metric
title: Realised Variance, Close-to-Close (annualised) — per Commodity
description: Zero-mean realised variance of the flagship's daily log returns, × 252.
  Its square root is realised volatility over whatever window the query asks for.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_close_variance
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_commodity_close_var_total` / `mcx_commodity_close_var_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_commodity_close_var_days](/metrics/mcx_commodity_close_var_days.md), [mcx_commodity_close_var_total](/metrics/mcx_commodity_close_var_total.md)
* **Derived from it:** [mcx_commodity_realised_vol](/metrics/mcx_commodity_realised_vol.md)
