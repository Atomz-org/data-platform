---
type: Concept
title: Interaction
description: A touchpoint (email, call, session) with a party.
okf_x_tier: platform
okf_x_parent: Event
okf_x_abstract: false
okf_x_identity: interaction_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `channel` | string | [status_enum](/roles/status_enum.md) |
| `interaction_id` | string | [natural_key](/roles/natural_key.md) |
| `occurred_at` | timestamp | [event_time](/roles/event_time.md) |

# Relations

* [customer_participates_in_interaction](/relations/customer_participates_in_interaction.md) — Customer participates in Interaction
