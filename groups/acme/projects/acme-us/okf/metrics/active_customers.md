---
type: Metric
title: Active Customers
description: Customers with at least one active subscription.
okf_x_kind: simple
okf_x_model: dim_customers
okf_x_time_column: created_at
okf_x_kg_node: metric:active_customers
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(case when is_active then 1 else 0 end)`
* **Built on:** [dim_customers](/tables/dim_customers.md)
* **Dimensions:** `customer_segment`, `country_code`
