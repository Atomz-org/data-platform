---
type: Concept
title: Shift
description: Induced from `raw_shifts` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `actual_end` | timestamp | [event_time](/roles/event_time.md) |
| `actual_start` | timestamp | [event_time](/roles/event_time.md) |
| `employee_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `scheduled_end` | timestamp | [event_time](/roles/event_time.md) |
| `scheduled_start` | timestamp | [event_time](/roles/event_time.md) |
| `shift_date` | date | [event_time](/roles/event_time.md) |
| `store_id` | integer | [foreign_key](/roles/foreign_key.md) |
