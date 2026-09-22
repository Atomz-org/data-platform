---
type: Concept
title: Expense
description: Induced from `raw_expenses` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount` | integer | [money_amount](/roles/money_amount.md) |
| `category_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `incurred_at` | timestamp | [event_time](/roles/event_time.md) |
| `store_id` | integer | [foreign_key](/roles/foreign_key.md) |
