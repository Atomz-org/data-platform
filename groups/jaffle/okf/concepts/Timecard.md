---
type: Concept
title: Timecard
description: Induced from `raw_timecards` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `clock_in` | timestamp | [event_time](/roles/event_time.md) |
| `clock_out` | timestamp | [event_time](/roles/event_time.md) |
| `employee_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `store_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `work_date` | date | [event_time](/roles/event_time.md) |
