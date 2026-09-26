---
type: Metric
title: Rogers–Satchell Variance (annualised) — per Commodity
description: Rogers–Satchell (1991) drift-robust OHLC variance per session, × 252.
  Prefer it to Garman–Klass in a trending market.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_rs_variance
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_commodity_rs_var_total` / `mcx_commodity_rs_var_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_commodity_rs_var_days](/metrics/mcx_commodity_rs_var_days.md), [mcx_commodity_rs_var_total](/metrics/mcx_commodity_rs_var_total.md)
* **Derived from it:** [mcx_commodity_rs_vol](/metrics/mcx_commodity_rs_vol.md)
