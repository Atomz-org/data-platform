---
type: Concept
title: PricingHistory
description: Induced from `raw_pricing_history` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `changed_at` | timestamp | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `new_price` | integer | [money_amount](/roles/money_amount.md) |
| `old_price` | integer | [money_amount](/roles/money_amount.md) |
| `product_id` | integer | [foreign_key](/roles/foreign_key.md) |
