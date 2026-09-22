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
* **Expression:** `sum(amount) / nullif(count(payment_id), 0)`
* **Ratio:** `revenue` / `payment_count` — re-divide at the reading grain, never average the ratio
* **Built on:** [fct_payments](/tables/fct_payments.md)
* **Dimensions:** `payment_status`, `customer_segment`, `plan_tier`, `country_code`
* **Filter:** `payment_status = 'succeeded'`
