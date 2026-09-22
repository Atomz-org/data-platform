---
type: Concept
title: CampaignSpend
description: Induced from `raw_campaign_spend` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `amount` | integer | [money_amount](/roles/money_amount.md) |
| `campaign_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `spend_date` | date | [event_time](/roles/event_time.md) |
