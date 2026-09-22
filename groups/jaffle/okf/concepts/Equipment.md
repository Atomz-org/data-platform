---
type: Concept
title: Equipment
description: Induced from `raw_equipment` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `last_maintenance_date` | date | [event_time](/roles/event_time.md) |
| `purchase_cost` | integer | [money_amount](/roles/money_amount.md) |
| `purchase_date` | date | [event_time](/roles/event_time.md) |
| `store_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `warranty_expiry` | date | [event_time](/roles/event_time.md) |
