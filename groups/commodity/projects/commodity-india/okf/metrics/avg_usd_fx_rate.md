---
type: Metric
title: Avg Applied FX Rate
description: Mean units of this market's currency per US dollar, as applied to landed
  prices; 1 for a USD market.
okf_x_kind: ratio
okf_x_model: fct_landed_prices_daily
okf_x_time_column: price_date
okf_x_kg_node: metric:avg_usd_fx_rate
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `usd_fx_rate_total` / `landed_price_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `currency_code`, `is_duty_rate_confirmed`, `market_code`, `market_unit`, `price_basis`
* **Built from:** [landed_price_days](/metrics/landed_price_days.md), [usd_fx_rate_total](/metrics/usd_fx_rate_total.md)

# Governance

* **Decision** ADR-0005 — commodity-india is one market of many (accepted)
