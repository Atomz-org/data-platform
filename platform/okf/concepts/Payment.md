---
type: Concept
title: Payment
description: Movement of money settling an agreement.
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

* Customer pays Payment — 
* Order settled by Payment — 
* Payment denominated in Currency — Makes the money/currency pairing explicit rather than a convention.
* Payment reversed by Refund — 
* Subscription settled by Payment — 
