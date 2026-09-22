---
type: Concept
title: Organization
description: A legal entity. Customers may belong to one.
okf_x_parent: Party
okf_x_abstract: false
okf_x_identity: organization_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `country` | string | [geo_country](/roles/geo_country.md) |
| `name` | string | [free_text](/roles/free_text.md) |
| `organization_id` | string | [natural_key](/roles/natural_key.md) |

# Relations

* Contract signed by Organization — 
* Customer belongs to Organization — A customer may sit under a parent organization.
