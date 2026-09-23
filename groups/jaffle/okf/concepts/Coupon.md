---
type: Concept
title: Coupon
description: Induced from `raw_coupons` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `campaign_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `created_at` | timestamp | [event_time](/roles/event_time.md) |
| `discount_amount` | integer | [money_amount](/roles/money_amount.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `minimum_order_amount` | integer | [money_amount](/roles/money_amount.md) |
| `valid_from` | date | [event_time](/roles/event_time.md) |
| `valid_until` | date | [event_time](/roles/event_time.md) |
