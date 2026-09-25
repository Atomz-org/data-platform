---
type: Metric
title: Realised Volatility (component)
description: ''
okf_x_kind: simple
okf_x_model: fct_commodity_trading_signals_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:realised_vol_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(realised_vol_20d)`
* **Built on:** [fct_commodity_trading_signals_daily](/tables/fct_commodity_trading_signals_daily.md)
* **Dimensions:** `commodity_id`, `ma_crossover`, `ma_regime`, `price_basis`, `stance`, `volatility_regime`
* **Derived from it:** [avg_realised_vol](/metrics/avg_realised_vol.md)
