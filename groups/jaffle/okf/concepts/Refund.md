---
type: Concept
title: Refund
description: Negative movement of money against a prior payment.
okf_x_tier: group
okf_x_parent: Event
okf_x_abstract: false
okf_x_identity: refund_id
okf_x_platform_concept: ../../../../platform/okf/concepts/Refund.md
---

Extends the platform's [Refund](../../../../platform/okf/concepts/Refund.md); this page is what this family added.

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount` | decimal | [money_amount](/roles/money_amount.md) |
| `currency` | string | [currency_code](/roles/currency_code.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `invoice_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `order_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `refund_amount` | integer | [money_amount](/roles/money_amount.md) |
| `refund_id` | string | [natural_key](/roles/natural_key.md) |
| `refunded_at` | timestamp | [event_time](/roles/event_time.md) |
| `requested_at` | timestamp | [event_time](/roles/event_time.md) |
| `resolved_at` | timestamp | [event_time](/roles/event_time.md) |

# Relations

* [payment_reversed_by_refund](/relations/payment_reversed_by_refund.md) — Payment reversed by Refund
