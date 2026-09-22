---
type: Metric
title: Revenue
description: Net revenue — succeeded payments only. The single definition.
okf_x_kind: simple
okf_x_model: fct_payments
okf_x_time_column: paid_at
okf_x_kg_node: metric:revenue
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(amount)`
* **Built on:** [fct_payments](/tables/fct_payments.md)
* **Dimensions:** `payment_status`, `customer_segment`, `plan_tier`, `country_code`
* **Filter:** `payment_status = 'succeeded'`
