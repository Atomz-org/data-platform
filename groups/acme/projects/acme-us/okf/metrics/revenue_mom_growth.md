---
type: Metric
title: Revenue MoM Growth
description: Month-over-month change in net revenue.
okf_x_kind: derived
okf_x_model: fct_payments
okf_x_time_column: paid_at
okf_x_kg_node: metric:revenue_mom_growth
---

# Definition

* **Kind:** `derived`
* **Expression:** derived
* **Built on:** [fct_payments](/tables/fct_payments.md)
* **Dimensions:** `country_code`, `customer_segment`, `payment_status`, `plan_tier`
* **Built from:** [revenue](/metrics/revenue.md)
