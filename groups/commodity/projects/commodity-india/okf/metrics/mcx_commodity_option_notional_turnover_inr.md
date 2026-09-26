---
type: Metric
title: Options Notional Turnover (₹) — per Commodity
description: What MCX reports as option `Value` — (strike + premium) × quantity. Premium
  is the smaller number traders pay; this is the exposure that changed hands.
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_option_notional_turnover_inr
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(option_notional_turnover_inr)`
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
