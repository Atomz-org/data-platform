---
type: Concept
title: Payroll
description: Induced from `raw_payroll` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `employee_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `pay_date` | date | [event_time](/roles/event_time.md) |
| `pay_period_end` | date | [event_time](/roles/event_time.md) |
| `pay_period_start` | date | [event_time](/roles/event_time.md) |
