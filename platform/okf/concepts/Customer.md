---
type: Concept
title: Customer
description: A party that buys. May be a person or an organization.
okf_x_parent: Party
okf_x_abstract: false
okf_x_identity: customer_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `country` | string | [geo_country](/roles/geo_country.md) |
| `created_at` | timestamp | [event_time](/roles/event_time.md) |
| `customer_id` | string | [natural_key](/roles/natural_key.md) |
| `email` | string | [pii_email](/roles/pii_email.md) |
| `name` | string | [pii_name](/roles/pii_name.md) |
| `segment` | string | [status_enum](/roles/status_enum.md) |

# Relations

* Customer belongs to Organization — A customer may sit under a parent organization.
* Customer holds Subscription — The spine of any recurring-revenue model.
* Customer located in Location — 
* Customer participates in Interaction — 
* Customer pays Payment — 
* Customer places Order — 
