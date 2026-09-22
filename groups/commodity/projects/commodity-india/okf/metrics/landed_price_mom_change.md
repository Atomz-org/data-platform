---
type: Metric
title: Landed Price MoM Change
description: Month-over-month change in the mean landed price; moves with both the
  benchmark and the currency.
okf_x_kind: derived
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:landed_price_mom_change
---

# Definition

* **Kind:** `derived`
* **Expression:** derived
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `currency_code`, `is_duty_rate_confirmed`, `market_code`, `market_unit`, `price_basis`
* **Built from:** [avg_landed_price_local](/metrics/avg_landed_price_local.md)

# Governance

* **Decision** ADR-0003 — Mean prices are ratio metrics, not `average` measures (accepted)
