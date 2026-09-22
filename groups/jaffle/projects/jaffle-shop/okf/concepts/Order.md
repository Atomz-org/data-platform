---
type: Concept
title: Order
description: A one-off purchase commitment.
okf_x_defined_in: platform
okf_x_parent: Agreement
okf_x_identity: order_id
okf_x_kg_node: concept:Order
okf_x_platform_concept: ../../../../../../platform/okf/concepts/Order.md
---

Defined by the platform ontology: [Order](../../../../../../platform/okf/concepts/Order.md).

# Instantiated by

* [adv_above_store_average](/tables/adv_above_store_average.md)
* [adv_customer_order_pairs](/tables/adv_customer_order_pairs.md)
* [dq_missing_invoices](/tables/dq_missing_invoices.md)
* [dq_orphan_orders](/tables/dq_orphan_orders.md)
* [inc_fct_orders](/tables/inc_fct_orders.md)
* [int_payment_method_mix](/tables/int_payment_method_mix.md)
* [ml_feature_basket_size](/tables/ml_feature_basket_size.md)
* [narrow_recent_orders](/tables/narrow_recent_orders.md)
* [orders](/tables/orders.md)
* [stg_derived_order_complete](/tables/stg_derived_order_complete.md)
* [stg_derived_order_with_customer](/tables/stg_derived_order_with_customer.md)
* [stg_derived_order_with_location](/tables/stg_derived_order_with_location.md)
* [wide_order_detail](/tables/wide_order_detail.md)
* [wide_order_with_customer](/tables/wide_order_with_customer.md)
* [wide_order_with_products](/tables/wide_order_with_products.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount` | decimal | money_amount |
| `currency` | string | currency_code |
| `id` | string | natural_key |
| `order_id` | string | natural_key |
| `order_total` | integer | money_amount |
| `ordered_at` | timestamp | event_time |
| `placed_at` | timestamp | event_time |
| `status` | string | status_enum |
| `store_id` | string | foreign_key |
| `subtotal` | integer | money_amount |

# Relations

* Customer places Order — 
* Order contains Product — Needs a line-item bridge in any physical model.
* Order settled by Payment — 

# Raw tables that instantiate it

* `jaffle-seeds.raw_orders`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
