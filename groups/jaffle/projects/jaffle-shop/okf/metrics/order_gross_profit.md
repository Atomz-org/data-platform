---
type: Metric
title: Order Gross Profit
description: Gross profit from each order.
okf_x_kind: derived
okf_x_model: orders
okf_x_time_column: ordered_at
okf_x_kg_node: metric:order_gross_profit
---

# Definition

* **Kind:** `derived`
* **Expression:** derived
* **Built on:** [orders](/tables/orders.md)
* **Dimensions:** `customer_order_number`, `is_drink_order`, `is_food_order`, `order_total_dim`
* **Built from:** [order_cost](/metrics/order_cost.md), [revenue](/metrics/revenue.md)
