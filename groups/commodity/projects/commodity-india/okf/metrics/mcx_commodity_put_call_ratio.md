---
type: Metric
title: Put/Call Ratio (notional OI) — per Commodity
description: Put open interest over call, each weighted by its underlying's notional
  per lot so every code of the commodity counts at its size. Above ~1.3 put-heavy,
  below ~0.7 call-heavy.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_put_call_ratio
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_commodity_put_oi_notional_inr` / `mcx_commodity_call_oi_notional_inr` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_commodity_call_oi_notional_inr](/metrics/mcx_commodity_call_oi_notional_inr.md), [mcx_commodity_put_oi_notional_inr](/metrics/mcx_commodity_put_oi_notional_inr.md)
