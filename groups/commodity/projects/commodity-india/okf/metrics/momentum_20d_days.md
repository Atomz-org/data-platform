---
type: Metric
title: Days With a Momentum Reading
description: ''
okf_x_kind: simple
okf_x_model: fct_commodity_trading_signals_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:momentum_20d_days
---

# Definition

* **Kind:** `simple`
* **Expression:** `count(momentum_20d_pct)`
* **Built on:** [fct_commodity_trading_signals_daily](/tables/fct_commodity_trading_signals_daily.md)
* **Dimensions:** `commodity_id`, `ma_crossover`, `ma_regime`, `price_basis`, `stance`, `volatility_regime`
* **Derived from it:** [avg_momentum_20d](/metrics/avg_momentum_20d.md)
