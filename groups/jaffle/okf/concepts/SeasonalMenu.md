---
type: Concept
title: SeasonalMenu
description: Induced from `raw_seasonal_menus` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `end_date` | date | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `menu_item_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `start_date` | date | [event_time](/roles/event_time.md) |
