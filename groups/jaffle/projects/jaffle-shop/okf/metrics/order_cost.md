---
type: Metric
title: Order Cost
description: Sum of cost for each order item.
okf_x_kind: simple
okf_x_model: orders
okf_x_time_column: ordered_at
okf_x_kg_node: metric:order_cost
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(order_cost)`
* **Built on:** [orders](/tables/orders.md)
* **Dimensions:** `customer_order_number`, `is_drink_order`, `is_food_order`, `order_total_dim`
* **Derived from it:** [order_gross_profit](/metrics/order_gross_profit.md)
