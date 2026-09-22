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
* **Expression:** `sum(usd_fx_rate) / nullif(count(landed_price_local), 0)`
* **Ratio:** `usd_fx_rate_total` / `landed_price_days` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* **Dimensions:** `commodity_id`, `market_code`, `currency_code`, `market_unit`, `is_duty_rate_confirmed`, `price_basis`
* **Built from:** [landed_price_days](/metrics/landed_price_days.md), [usd_fx_rate_total](/metrics/usd_fx_rate_total.md)

# Governance

* **Decision** ADR-0005 — commodity-india is one market of many (accepted)
