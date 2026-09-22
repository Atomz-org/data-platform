---
type: Metric
title: Average Order Value
description: Revenue divided by succeeded payment count.
okf_x_kind: ratio
okf_x_model: fct_payments
okf_x_time_column: paid_at
okf_x_kg_node: metric:aov
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `revenue` / `payment_count` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_payments](/tables/fct_payments.md)
* **Dimensions:** `country_code`, `customer_segment`, `payment_status`, `plan_tier`
* **Built from:** [payment_count](/metrics/payment_count.md), [revenue](/metrics/revenue.md)
