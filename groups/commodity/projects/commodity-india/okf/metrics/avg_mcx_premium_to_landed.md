---
type: Metric
title: Avg MCX Premium to Landed Parity
description: MCX settlement over the landed import-parity price of the same quote
  basis, minus one. Only codes the family prices. Group by contract_code.
okf_x_kind: ratio
okf_x_model: fct_mcx_commodity_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:avg_mcx_premium_to_landed
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `mcx_premium_total` / `mcx_premium_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md)
* **Dimensions:** `contract_code`, `curve_state`, `ema_9_21_signal`, `is_backwardation`, `is_contango`, `is_flagship`, `mcx_commodity`, `oi_buildup`, `segment`, `stance`, `trend_regime`, `volatility_regime`
* **Built from:** [mcx_premium_days](/metrics/mcx_premium_days.md), [mcx_premium_total](/metrics/mcx_premium_total.md)
