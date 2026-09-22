---
type: Concept
title: Payment
description: Movement of money settling an agreement.
okf_x_tier: group
okf_x_parent: Event
okf_x_abstract: false
okf_x_identity: payment_id
okf_x_platform_concept: ../../../../platform/okf/concepts/Payment.md
---

Extends the platform's [Payment](../../../../platform/okf/concepts/Payment.md); this page is what this family added.

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount` | float | [money_amount](/roles/money_amount.md) |
| `created` | timestamp | [event_time](/roles/event_time.md) |
| `currency` | string | [currency_code](/roles/currency_code.md) |
| `customer_id` | string | [foreign_key](/roles/foreign_key.md) |
| `id` | string | [natural_key](/roles/natural_key.md) |
| `paid_at` | timestamp | [event_time](/roles/event_time.md) |
| `payment_id` | string | [natural_key](/roles/natural_key.md) |
| `receipt_email` | string | [pii_email](/roles/pii_email.md) |
| `status` | string | [status_enum](/roles/status_enum.md) |
| `subscription_id` | string | [foreign_key](/roles/foreign_key.md) |

# Relations

* [customer_pays_charge](/relations/customer_pays_charge.md) — Payment pays Customer
* [customer_pays_payment](/relations/customer_pays_payment.md) — Customer pays Payment
* [order_settled_by_payment](/relations/order_settled_by_payment.md) — Order settled by Payment
* [payment_denominated_in_currency](/relations/payment_denominated_in_currency.md) — Payment denominated in Currency
* [payment_reversed_by_refund](/relations/payment_reversed_by_refund.md) — Payment reversed by Refund
* [subscription_settled_by_payment](/relations/subscription_settled_by_payment.md) — Subscription settled by Payment
* [subscription_settles_charge](/relations/subscription_settles_charge.md) — Payment settles Subscription
