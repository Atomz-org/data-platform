---
type: Concept
title: Contract
description: A negotiated agreement, usually with custom terms.
okf_x_tier: platform
okf_x_parent: Agreement
okf_x_abstract: false
okf_x_identity: contract_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `contract_id` | string | [natural_key](/roles/natural_key.md) |
| `signed_at` | timestamp | [event_time](/roles/event_time.md) |

# Relations

* [contract_signed_by_organization](/relations/contract_signed_by_organization.md) — Contract signed by Organization
