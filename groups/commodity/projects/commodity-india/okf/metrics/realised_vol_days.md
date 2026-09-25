---
type: Metric
title: Days With a Volatility Reading
description: ''
okf_x_kind: simple
okf_x_model: fct_commodity_trading_signals_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:realised_vol_days
---

# Definition

* **Kind:** `simple`
* **Expression:** `count(realised_vol_20d)`
* **Built on:** [fct_commodity_trading_signals_daily](/tables/fct_commodity_trading_signals_daily.md)
* **Dimensions:** `commodity_id`, `ma_crossover`, `ma_regime`, `price_basis`, `stance`, `volatility_regime`
* **Derived from it:** [avg_realised_vol](/metrics/avg_realised_vol.md)
