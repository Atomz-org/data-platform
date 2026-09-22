---
type: Concept
title: Customer
description: A party that buys. May be a person or an organization.
okf_x_defined_in: platform
okf_x_parent: Party
okf_x_identity: id
okf_x_platform_concept: ../../../../../../platform/okf/concepts/Customer.md
---

Defined by the platform ontology: [Customer](../../../../../../platform/okf/concepts/Customer.md).

# Instantiated by

* [fct_payments](/tables/fct_payments.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `country` | string | geo_country |
| `created` | timestamp | event_time |
| `created_at` | timestamp | event_time |
| `customer_id` | string | natural_key |
| `email` | string | pii_email |
| `id` | string | natural_key |
| `name` | string | pii_name |
| `organization_id` | string | foreign_key |
| `segment` | string | status_enum |

# Relations

* Customer belongs to Organization — A customer may sit under a parent organization.
* Subscription holds Customer — Foreign key resolves to a scanned entity. Rename the relation to the business verb — `places`, `settles`, `holds` — before approving; `refers_to` is a placeholder, not a meaning.
* Customer holds Subscription — The spine of any recurring-revenue model.
* Customer located in Location — 
* Customer participates in Interaction — 
* Payment pays Customer — Foreign key resolves to a scanned entity. Rename the relation to the business verb — `places`, `settles`, `holds` — before approving; `refers_to` is a placeholder, not a meaning.
* Customer pays Payment — 
* Customer places Order — 
