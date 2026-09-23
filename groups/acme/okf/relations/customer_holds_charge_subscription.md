---
type: Relation
title: customer_holds_charge_subscription
description: Foreign key resolves to a scanned entity. Rename the relation to the
  business verb — `places`, `settles`, `holds` — before approving; `refers_to` is
  a placeholder, not a meaning.
okf_x_tier: group
okf_x_domain: Subscription
okf_x_range: Customer
okf_x_cardinality: MANY_TO_ONE
okf_x_inverse: held by
---

# Reading it

* Subscription holds Customer
* Reverse: Customer held by Subscription

# Between

* Domain: [Subscription](/concepts/Subscription.md)
* Range: [Customer](/concepts/Customer.md)
