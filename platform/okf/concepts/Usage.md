---
type: Concept
title: Usage
description: Metered consumption attributable to an agreement.
okf_x_tier: platform
okf_x_parent: Event
okf_x_abstract: false
okf_x_identity: usage_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `measured_at` | timestamp | [event_time](/roles/event_time.md) |
| `quantity` | integer | [quantity](/roles/quantity.md) |
| `usage_id` | string | [natural_key](/roles/natural_key.md) |

# Relations

* [subscription_metered_by_usage](/relations/subscription_metered_by_usage.md) — Subscription metered by Usage
