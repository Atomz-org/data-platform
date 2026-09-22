---
type: Concept
title: Payment
description: Movement of money settling an agreement.
okf_x_defined_in: platform
okf_x_parent: Event
okf_x_identity: payment_id
okf_x_platform_concept: ../../../../../../platform/okf/concepts/Payment.md
---

Defined by the platform ontology: [Payment](../../../../../../platform/okf/concepts/Payment.md).

# Instantiated by

* [dim_customers](/tables/dim_customers.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount` | float | money_amount |
| `created` | timestamp | event_time |
| `currency` | string | currency_code |
| `customer_id` | string | foreign_key |
| `id` | string | natural_key |
| `paid_at` | timestamp | event_time |
| `payment_id` | string | natural_key |
| `receipt_email` | string | pii_email |
| `status` | string | status_enum |
| `subscription_id` | string | foreign_key |

# Relations

* Payment pays Customer — Foreign key resolves to a scanned entity. Rename the relation to the business verb — `places`, `settles`, `holds` — before approving; `refers_to` is a placeholder, not a meaning.
* Customer pays Payment — 
* Order settled by Payment — 
* Payment denominated in Currency — Makes the money/currency pairing explicit rather than a convention.
* Payment reversed by Refund — 
* Subscription settled by Payment — 
* Payment settles Subscription — Foreign key resolves to a scanned entity. Rename the relation to the business verb — `places`, `settles`, `holds` — before approving; `refers_to` is a placeholder, not a meaning.
