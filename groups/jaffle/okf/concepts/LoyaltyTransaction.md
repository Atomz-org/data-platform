---
type: Concept
title: LoyaltyTransaction
description: Induced from `raw_loyalty_transactions` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `loyalty_member_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `order_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `transacted_at` | timestamp | [event_time](/roles/event_time.md) |
