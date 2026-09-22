---
type: Metric
title: Gross Payment Volume
description: All payment attempts regardless of outcome.
okf_x_kind: simple
okf_x_model: fct_payments
okf_x_time_column: paid_at
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(amount)`
* **Built on:** [fct_payments](/tables/fct_payments.md)
* **Dimensions:** `payment_status`, `customer_segment`, `plan_tier`, `country_code`
