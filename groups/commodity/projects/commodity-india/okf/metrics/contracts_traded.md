---
type: Metric
title: Contracts Traded
description: Front-month futures volume from live feeds. Group by commodity.
okf_x_kind: simple
okf_x_model: fct_commodity_prices_daily
okf_x_time_column: price_date
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(volume)`
* **Built on:** [fct_commodity_prices_daily](/tables/fct_commodity_prices_daily.md)
* **Dimensions:** `commodity_id`, `price_basis`
* **Filter:** `price_basis = 'futures'`
