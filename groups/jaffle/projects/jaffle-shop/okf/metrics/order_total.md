---
type: Metric
title: Order Total
description: Sum of total order amonunt. Includes tax + revenue.
okf_x_kind: simple
okf_x_model: orders
okf_x_time_column: ordered_at
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(order_total)`
* **Built on:** [orders](/tables/orders.md)
* **Dimensions:** `order_total_dim`, `is_food_order`, `is_drink_order`, `customer_order_number`
