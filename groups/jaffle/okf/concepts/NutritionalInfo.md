---
type: Concept
title: NutritionalInfo
description: Induced from `raw_nutritional_info` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `menu_item_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `total_carbs_g` | integer | [money_amount](/roles/money_amount.md) |
| `total_fat_g` | integer | [money_amount](/roles/money_amount.md) |
| `total_sugars_g` | integer | [money_amount](/roles/money_amount.md) |
| `updated_at` | timestamp | [event_time](/roles/event_time.md) |
