---
type: Metric
title: LTV Pre-tax
description: Customer's lifetime spend before tax
okf_x_kind: simple
okf_x_model: customers
okf_x_time_column: first_ordered_at
okf_x_kg_node: metric:lifetime_spend_pretax
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(lifetime_spend_pretax)`
* **Built on:** [customers](/tables/customers.md)
* **Dimensions:** `customer_name`, `customer_type`
