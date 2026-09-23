---
type: Metric
title: Order Total
description: Sum of total order amonunt. Includes tax + revenue.
okf_x_kind: simple
okf_x_model: orders
okf_x_time_column: ordered_at
okf_x_kg_node: metric:order_total
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(order_total)`
* **Built on:** [orders](/tables/orders.md)
* **Dimensions:** `customer_order_number`, `is_drink_order`, `is_food_order`, `order_total_dim`
