---
type: Metric
title: LTV Pre-tax
description: Customer's lifetime spend before tax
okf_x_kind: simple
okf_x_model: customers
okf_x_time_column: first_ordered_at
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(lifetime_spend_pretax)`
* **Built on:** [customers](/tables/customers.md)
* **Dimensions:** `customer_name`, `customer_type`
