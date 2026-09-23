---
type: Metric
title: Food Orders
description: Count of orders that contain food order items
okf_x_kind: simple
okf_x_model: orders
okf_x_time_column: ordered_at
okf_x_kg_node: metric:food_orders
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(1)`
* **Built on:** [orders](/tables/orders.md)
* **Dimensions:** `customer_order_number`, `is_drink_order`, `is_food_order`, `order_total_dim`
* **Filter:** `is_food_order = true`
