---
type: Metric
title: Count Lifetime Orders
description: Count of lifetime orders
okf_x_kind: simple
okf_x_model: customers
okf_x_time_column: first_ordered_at
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(count_lifetime_orders)`
* **Built on:** [customers](/tables/customers.md)
* **Dimensions:** `customer_name`, `customer_type`
