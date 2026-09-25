---
type: Metric
title: 20-Day Momentum (component)
description: ''
okf_x_kind: simple
okf_x_model: fct_commodity_trading_signals_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:momentum_20d_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(momentum_20d_pct)`
* **Built on:** [fct_commodity_trading_signals_daily](/tables/fct_commodity_trading_signals_daily.md)
* **Dimensions:** `commodity_id`, `ma_crossover`, `ma_regime`, `price_basis`, `stance`, `volatility_regime`
* **Derived from it:** [avg_momentum_20d](/metrics/avg_momentum_20d.md)
