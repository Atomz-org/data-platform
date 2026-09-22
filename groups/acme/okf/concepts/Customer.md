---
type: Concept
title: Customer
description: A party that buys. May be a person or an organization.
okf_x_tier: group
okf_x_parent: Party
okf_x_abstract: false
okf_x_identity: id
okf_x_platform_concept: ../../../../platform/okf/concepts/Customer.md
---

Extends the platform's [Customer](../../../../platform/okf/concepts/Customer.md); this page is what this family added.

# Properties

| Property | Datatype | Role |
|---|---|---|
| `country` | string | [geo_country](/roles/geo_country.md) |
| `created` | timestamp | [event_time](/roles/event_time.md) |
| `created_at` | timestamp | [event_time](/roles/event_time.md) |
| `customer_id` | string | [natural_key](/roles/natural_key.md) |
| `email` | string | [pii_email](/roles/pii_email.md) |
| `id` | string | [natural_key](/roles/natural_key.md) |
| `name` | string | [pii_name](/roles/pii_name.md) |
| `organization_id` | string | [foreign_key](/roles/foreign_key.md) |
| `segment` | string | [status_enum](/roles/status_enum.md) |

# Relations

* [customer_belongs_to_organization](/relations/customer_belongs_to_organization.md) — Customer belongs to Organization
* [customer_holds_charge_subscription](/relations/customer_holds_charge_subscription.md) — Subscription holds Customer
* [customer_holds_subscription](/relations/customer_holds_subscription.md) — Customer holds Subscription
* [customer_located_in_location](/relations/customer_located_in_location.md) — Customer located in Location
* [customer_participates_in_interaction](/relations/customer_participates_in_interaction.md) — Customer participates in Interaction
* [customer_pays_charge](/relations/customer_pays_charge.md) — Payment pays Customer
* [customer_pays_payment](/relations/customer_pays_payment.md) — Customer pays Payment
* [customer_places_order](/relations/customer_places_order.md) — Customer places Order
