---
type: Concept
title: GiftCard
description: Induced from `raw_gift_cards` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `current_balance` | integer | [money_amount](/roles/money_amount.md) |
| `customer_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `expires_at` | timestamp | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `initial_balance` | integer | [money_amount](/roles/money_amount.md) |
| `issued_at` | timestamp | [event_time](/roles/event_time.md) |
