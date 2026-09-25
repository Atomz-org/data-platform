---
type: Metric
title: Avg Realised Volatility (annualised)
description: 20-day dispersion annualised on 252 trading days. Group by commodity.
okf_x_kind: ratio
okf_x_model: fct_commodity_trading_signals_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_realised_vol
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `realised_vol_total` / `realised_vol_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_commodity_trading_signals_daily](/tables/fct_commodity_trading_signals_daily.md)
* **Dimensions:** `commodity_id`, `ma_crossover`, `ma_regime`, `price_basis`, `stance`, `volatility_regime`
* **Built from:** [realised_vol_days](/metrics/realised_vol_days.md), [realised_vol_total](/metrics/realised_vol_total.md)
