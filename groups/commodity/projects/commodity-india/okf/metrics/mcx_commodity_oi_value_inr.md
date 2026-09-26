---
type: Metric
title: Open Interest Value (₹) — per Commodity
description: Notional of open futures positions across every code and expiry, at the
  period's last session. A stock — never summed over days.
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_oi_value_inr
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(open_interest_value_inr)`
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
