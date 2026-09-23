---
type: Concept
title: WasteLog
description: Induced from `raw_waste_logs` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `cost_of_waste` | integer | [money_amount](/roles/money_amount.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `location_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `product_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `wasted_at` | timestamp | [event_time](/roles/event_time.md) |
