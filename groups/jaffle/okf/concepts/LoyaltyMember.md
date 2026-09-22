---
type: Concept
title: LoyaltyMember
description: Induced from `raw_loyalty_members` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `customer_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `enrolled_at` | timestamp | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `last_activity_at` | timestamp | [event_time](/roles/event_time.md) |
| `tier_id` | integer | [foreign_key](/roles/foreign_key.md) |
