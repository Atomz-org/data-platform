---
type: Metric
title: Median Revenue
description: The median revenue for each order item. Excludes tax.
okf_x_kind: simple
okf_x_model: order_items
okf_x_time_column: ordered_at
---

# Definition

* **Kind:** `simple`
* **Expression:** `percentile_cont(0.5) within group (order by product_price)`
* **Built on:** [order_items](/tables/order_items.md)
