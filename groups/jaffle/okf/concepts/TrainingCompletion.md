---
type: Concept
title: TrainingCompletion
description: Induced from `raw_training_completions` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `completed_at` | timestamp | [event_time](/roles/event_time.md) |
| `course_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `employee_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `started_at` | timestamp | [event_time](/roles/event_time.md) |
