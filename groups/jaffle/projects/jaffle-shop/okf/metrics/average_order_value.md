---
type: Metric
title: Average Order Value
description: LTV pre-tax / number of orders
okf_x_kind: derived
okf_x_model: customers
okf_x_time_column: first_ordered_at
okf_x_kg_node: metric:average_order_value
---

# Definition

* **Kind:** `derived`
* **Expression:** derived
* **Built on:** [customers](/tables/customers.md)
* **Dimensions:** `customer_name`, `customer_type`
* **Built from:** [count_lifetime_orders](/metrics/count_lifetime_orders.md), [lifetime_spend_pretax](/metrics/lifetime_spend_pretax.md)
