---
type: Metric
title: Cumulative Revenue (All Time)
description: The cumulative revenue for all orders.
okf_x_kind: cumulative
okf_x_model: order_items
okf_x_time_column: ordered_at
okf_x_kg_node: metric:cumulative_revenue
---

# Definition

* **Kind:** `cumulative`
* **Expression:** `sum(product_price)`
* **Built on:** [order_items](/tables/order_items.md)
* **Dimensions:** `is_drink_item`, `is_food_item`
