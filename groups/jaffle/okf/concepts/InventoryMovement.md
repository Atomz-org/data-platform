---
type: Concept
title: InventoryMovement
description: Induced from `raw_inventory_movements` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `location_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `moved_at` | timestamp | [event_time](/roles/event_time.md) |
| `product_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `reference_id` | integer | [foreign_key](/roles/foreign_key.md) |
