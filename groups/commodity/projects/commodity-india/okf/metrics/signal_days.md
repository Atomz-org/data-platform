---
type: Metric
title: Signal Days
description: Days with a signal reading. The denominator every mean below divides
  by.
okf_x_kind: simple
okf_x_model: fct_commodity_trading_signals_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:signal_days
---

# Definition

* **Kind:** `simple`
* **Expression:** `count(price_id)`
* **Built on:** [fct_commodity_trading_signals_daily](/tables/fct_commodity_trading_signals_daily.md)
* **Dimensions:** `commodity_id`, `ma_crossover`, `ma_regime`, `price_basis`, `stance`, `volatility_regime`
