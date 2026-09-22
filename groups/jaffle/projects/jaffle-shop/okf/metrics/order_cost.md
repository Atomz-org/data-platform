---
type: Metric
title: Order Cost
description: Sum of cost for each order item.
okf_x_kind: simple
okf_x_model: orders
okf_x_time_column: ordered_at
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(order_cost)`
* **Built on:** [orders](/tables/orders.md)
* **Dimensions:** `order_total_dim`, `is_food_order`, `is_drink_order`, `customer_order_number`
