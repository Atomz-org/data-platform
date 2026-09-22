---
type: Metric
title: Payments
description: Count of succeeded payments.
okf_x_kind: simple
okf_x_model: fct_payments
okf_x_time_column: paid_at
okf_x_kg_node: metric:payment_count
---

# Definition

* **Kind:** `simple`
* **Expression:** `count(payment_id)`
* **Built on:** [fct_payments](/tables/fct_payments.md)
* **Dimensions:** `country_code`, `customer_segment`, `payment_status`, `plan_tier`
* **Filter:** `payment_status = 'succeeded'`
* **Derived from it:** [aov](/metrics/aov.md)
