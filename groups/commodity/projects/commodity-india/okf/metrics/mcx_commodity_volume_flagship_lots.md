---
type: Metric
title: Volume (flagship-lot equivalents) — per Commodity
description: Turnover restated in lots of the flagship contract, so GOLD, GOLDM and
  GOLDPETAL add up. Group by mcx_commodity — a gold lot is not a crude lot.
okf_x_kind: simple
okf_x_model: fct_mcx_commodity_rollup_daily
okf_x_time_column: trade_date
okf_x_kg_node: metric:mcx_commodity_volume_flagship_lots
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(volume_flagship_lots)`
* **Built on:** [fct_mcx_commodity_rollup_daily](/tables/fct_mcx_commodity_rollup_daily.md)
* **Dimensions:** `flagship_contract_code`, `is_liquid`, `mcx_commodity`, `segment`, `stance`, `trend_regime`, `volatility_regime`
