---
type: Metric
title: Gross Payment Volume
description: All payment attempts regardless of outcome.
okf_x_kind: simple
okf_x_model: fct_payments
okf_x_time_column: paid_at
okf_x_kg_node: metric:gross_payment_volume
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(amount)`
* **Built on:** [fct_payments](/tables/fct_payments.md)
* **Dimensions:** `country_code`, `customer_segment`, `payment_status`, `plan_tier`
