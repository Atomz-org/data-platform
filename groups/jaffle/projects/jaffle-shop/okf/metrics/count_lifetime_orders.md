---
type: Metric
title: Count Lifetime Orders
description: Count of lifetime orders
okf_x_kind: simple
okf_x_model: customers
okf_x_time_column: first_ordered_at
okf_x_kg_node: metric:count_lifetime_orders
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(count_lifetime_orders)`
* **Built on:** [customers](/tables/customers.md)
* **Dimensions:** `customer_name`, `customer_type`
* **Derived from it:** [average_order_value](/metrics/average_order_value.md)
