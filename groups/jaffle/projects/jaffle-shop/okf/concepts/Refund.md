---
type: Concept
title: Refund
description: Negative movement of money against a prior payment.
okf_x_defined_in: platform
okf_x_parent: Event
okf_x_identity: refund_id
okf_x_kg_node: concept:Refund
okf_x_platform_concept: ../../../../../../platform/okf/concepts/Refund.md
---

Defined by the platform ontology: [Refund](../../../../../../platform/okf/concepts/Refund.md).

# Instantiated by

* [fct_refunds](/tables/fct_refunds.md)
* [int_refund_processing_time](/tables/int_refund_processing_time.md)
* [int_refunds_enriched](/tables/int_refunds_enriched.md)
* [stg_derived_refund_with_order](/tables/stg_derived_refund_with_order.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount` | decimal | money_amount |
| `currency` | string | currency_code |
| `id` | integer | natural_key |
| `invoice_id` | integer | foreign_key |
| `order_id` | integer | foreign_key |
| `refund_amount` | integer | money_amount |
| `refund_id` | string | natural_key |
| `refunded_at` | timestamp | event_time |
| `requested_at` | timestamp | event_time |
| `resolved_at` | timestamp | event_time |

# Relations

* Payment reversed by Refund — 

# Raw tables that instantiate it

* `jaffle-seeds.raw_refunds`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
