---
type: Relation
title: subscription_settled_by_payment
description: Subscription settled by Payment
okf_x_tier: platform
okf_x_domain: Subscription
okf_x_range: Payment
okf_x_cardinality: ONE_TO_MANY
okf_x_inverse: settles
---

# Reading it

* Subscription settled by Payment
* Reverse: Payment settles Subscription

# Between

* Domain: [Subscription](/concepts/Subscription.md)
* Range: [Payment](/concepts/Payment.md)
