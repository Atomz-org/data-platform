---
type: Concept
title: EmailEvent
description: Induced from `raw_email_events` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `campaign_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `customer_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `event_at` | timestamp | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
