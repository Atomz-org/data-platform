---
type: Concept
title: Invoice
description: Induced from `raw_invoices` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount_due` | integer | [money_amount](/roles/money_amount.md) |
| `amount_paid` | integer | [money_amount](/roles/money_amount.md) |
| `customer_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `due_at` | timestamp | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `issued_at` | timestamp | [event_time](/roles/event_time.md) |
| `order_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `paid_at` | timestamp | [event_time](/roles/event_time.md) |
| `subtotal` | integer | [money_amount](/roles/money_amount.md) |
| `tax_amount` | integer | [money_amount](/roles/money_amount.md) |
| `total_amount` | integer | [money_amount](/roles/money_amount.md) |
