---
type: Concept
title: Payment
description: Movement of money settling an agreement.
okf_x_tier: platform
okf_x_parent: Event
okf_x_abstract: false
okf_x_identity: payment_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount` | decimal | [money_amount](/roles/money_amount.md) |
| `currency` | string | [currency_code](/roles/currency_code.md) |
| `paid_at` | timestamp | [event_time](/roles/event_time.md) |
| `payment_id` | string | [natural_key](/roles/natural_key.md) |
| `status` | string | [status_enum](/roles/status_enum.md) |

# Relations

* [customer_pays_payment](/relations/customer_pays_payment.md) — Customer pays Payment
* [order_settled_by_payment](/relations/order_settled_by_payment.md) — Order settled by Payment
* [payment_denominated_in_currency](/relations/payment_denominated_in_currency.md) — Payment denominated in Currency
* [payment_reversed_by_refund](/relations/payment_reversed_by_refund.md) — Payment reversed by Refund
* [subscription_settled_by_payment](/relations/subscription_settled_by_payment.md) — Subscription settled by Payment
