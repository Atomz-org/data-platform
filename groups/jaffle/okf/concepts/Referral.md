---
type: Concept
title: Referral
description: Induced from `raw_referrals` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `campaign_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `converted_at` | timestamp | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `referee_customer_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `referred_at` | timestamp | [event_time](/roles/event_time.md) |
| `referrer_customer_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `reward_amount` | integer | [money_amount](/roles/money_amount.md) |
