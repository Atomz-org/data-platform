---
type: Metric
title: Avg 20-Day Momentum
description: Mean 20-day rate of change. Group by commodity.
okf_x_kind: ratio
okf_x_model: fct_commodity_trading_signals_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_momentum_20d
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `momentum_20d_total` / `momentum_20d_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_commodity_trading_signals_daily](/tables/fct_commodity_trading_signals_daily.md)
* **Dimensions:** `commodity_id`, `ma_crossover`, `ma_regime`, `price_basis`, `stance`, `volatility_regime`
* **Built from:** [momentum_20d_days](/metrics/momentum_20d_days.md), [momentum_20d_total](/metrics/momentum_20d_total.md)
