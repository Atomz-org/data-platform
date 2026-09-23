---
type: Concept
title: AccountReceivable
description: Induced from `raw_accounts_receivable` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount_due` | integer | [money_amount](/roles/money_amount.md) |
| `amount_outstanding` | integer | [money_amount](/roles/money_amount.md) |
| `amount_paid` | integer | [money_amount](/roles/money_amount.md) |
| `created_at` | timestamp | [event_time](/roles/event_time.md) |
| `customer_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `due_at` | timestamp | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `invoice_id` | integer | [foreign_key](/roles/foreign_key.md) |
