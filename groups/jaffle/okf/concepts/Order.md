---
type: Concept
title: Order
description: A one-off purchase commitment.
okf_x_tier: group
okf_x_parent: Agreement
okf_x_abstract: false
okf_x_identity: order_id
okf_x_platform_concept: ../../../../platform/okf/concepts/Order.md
---

Extends the platform's [Order](../../../../platform/okf/concepts/Order.md); this page is what this family added.

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount` | decimal | [money_amount](/roles/money_amount.md) |
| `currency` | string | [currency_code](/roles/currency_code.md) |
| `id` | string | [natural_key](/roles/natural_key.md) |
| `order_id` | string | [natural_key](/roles/natural_key.md) |
| `order_total` | integer | [money_amount](/roles/money_amount.md) |
| `ordered_at` | timestamp | [event_time](/roles/event_time.md) |
| `placed_at` | timestamp | [event_time](/roles/event_time.md) |
| `status` | string | [status_enum](/roles/status_enum.md) |
| `store_id` | string | [foreign_key](/roles/foreign_key.md) |
| `subtotal` | integer | [money_amount](/roles/money_amount.md) |

# Relations

* [customer_places_order](/relations/customer_places_order.md) — Customer places Order
* [order_contains_product](/relations/order_contains_product.md) — Order contains Product
* [order_settled_by_payment](/relations/order_settled_by_payment.md) — Order settled by Payment
