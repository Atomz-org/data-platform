---
type: Relation
title: subscription_settles_charge
description: Foreign key resolves to a scanned entity. Rename the relation to the
  business verb — `places`, `settles`, `holds` — before approving; `refers_to` is
  a placeholder, not a meaning.
okf_x_tier: group
okf_x_domain: Payment
okf_x_range: Subscription
okf_x_cardinality: MANY_TO_ONE
okf_x_inverse: settled by
---

# Reading it

* Payment settles Subscription
* Reverse: Subscription settled by Payment

# Between

* Domain: [Payment](/concepts/Payment.md)
* Range: [Subscription](/concepts/Subscription.md)
