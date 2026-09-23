---
type: Concept
title: Refund
description: Negative movement of money against a prior payment.
okf_x_tier: platform
okf_x_parent: Event
okf_x_abstract: false
okf_x_identity: refund_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount` | decimal | [money_amount](/roles/money_amount.md) |
| `currency` | string | [currency_code](/roles/currency_code.md) |
| `refund_id` | string | [natural_key](/roles/natural_key.md) |
| `refunded_at` | timestamp | [event_time](/roles/event_time.md) |

# Relations

* [payment_reversed_by_refund](/relations/payment_reversed_by_refund.md) — Payment reversed by Refund
