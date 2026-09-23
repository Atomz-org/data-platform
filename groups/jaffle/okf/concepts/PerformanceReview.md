---
type: Concept
title: PerformanceReview
description: Induced from `raw_performance_reviews` and approved by onboarding-ladder.
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
| `review_date` | date | [event_time](/roles/event_time.md) |
| `reviewer_id` | integer | [foreign_key](/roles/foreign_key.md) |
