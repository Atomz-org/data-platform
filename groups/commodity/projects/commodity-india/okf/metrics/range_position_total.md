---
type: Metric
title: Range Position (component)
description: Sum of daily range positions. A component of avg_range_position, not
  a figure to read.
okf_x_kind: simple
okf_x_model: fct_commodity_trading_signals_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:range_position_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(pct_of_52w_range)`
* **Built on:** [fct_commodity_trading_signals_daily](/tables/fct_commodity_trading_signals_daily.md)
* **Dimensions:** `commodity_id`, `ma_crossover`, `ma_regime`, `price_basis`, `stance`, `volatility_regime`
* **Derived from it:** [avg_range_position](/metrics/avg_range_position.md)
