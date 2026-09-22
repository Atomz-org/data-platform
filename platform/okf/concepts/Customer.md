---
type: Concept
title: Customer
description: A party that buys. May be a person or an organization.
okf_x_tier: platform
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

* [customer_belongs_to_organization](/relations/customer_belongs_to_organization.md) — Customer belongs to Organization
* [customer_holds_subscription](/relations/customer_holds_subscription.md) — Customer holds Subscription
* [customer_located_in_location](/relations/customer_located_in_location.md) — Customer located in Location
* [customer_participates_in_interaction](/relations/customer_participates_in_interaction.md) — Customer participates in Interaction
* [customer_pays_payment](/relations/customer_pays_payment.md) — Customer pays Payment
* [customer_places_order](/relations/customer_places_order.md) — Customer places Order
