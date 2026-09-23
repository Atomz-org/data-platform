---
type: Relation
title: customer_belongs_to_organization
description: A customer may sit under a parent organization.
okf_x_tier: platform
okf_x_domain: Customer
okf_x_range: Organization
okf_x_cardinality: MANY_TO_ONE
okf_x_inverse: has customer
---

# Reading it

* Customer belongs to Organization
* Reverse: Organization has customer Customer

# Between

* Domain: [Customer](/concepts/Customer.md)
* Range: [Organization](/concepts/Organization.md)
