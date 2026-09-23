---
type: Metric
title: Benchmark Price MoM Change
description: Month-over-month change in the mean benchmark price. Group by commodity.
okf_x_kind: derived
okf_x_model: fct_commodity_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:benchmark_price_mom_change
---

# Definition

* **Kind:** `derived`
* **Expression:** derived
* **Built on:** [fct_commodity_prices_daily](/tables/fct_commodity_prices_daily.md)
* **Dimensions:** `commodity_id`, `price_basis`
* **Built from:** [avg_benchmark_price_usd](/metrics/avg_benchmark_price_usd.md)

# Governance

* **Decision** ADR-0003 — Mean prices are ratio metrics, not `average` measures (accepted)
