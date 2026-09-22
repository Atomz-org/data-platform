---
type: Metric
title: Drink Orders
description: Count of orders that contain drink order items
okf_x_kind: simple
okf_x_model: orders
okf_x_time_column: ordered_at
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(1)`
* **Built on:** [orders](/tables/orders.md)
* **Dimensions:** `order_total_dim`, `is_food_order`, `is_drink_order`, `customer_order_number`
* **Filter:** `is_drink_order = true`
