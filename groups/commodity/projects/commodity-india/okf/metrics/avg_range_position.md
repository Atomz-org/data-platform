---
type: Metric
title: Avg Position in 52-Week Range
description: 0 at the 52-week low, 1 at the high. Group by commodity — averaging this
  across commodities is a number about the basket, not about anything tradable.
okf_x_kind: ratio
okf_x_model: fct_commodity_trading_signals_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_range_position
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `range_position_total` / `range_position_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_commodity_trading_signals_daily](/tables/fct_commodity_trading_signals_daily.md)
* **Dimensions:** `commodity_id`, `ma_crossover`, `ma_regime`, `price_basis`, `stance`, `volatility_regime`
* **Built from:** [range_position_days](/metrics/range_position_days.md), [range_position_total](/metrics/range_position_total.md)
