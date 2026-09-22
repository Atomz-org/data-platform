---
type: Relation
title: customer_holds_subscription
description: The spine of any recurring-revenue model.
okf_x_tier: platform
okf_x_domain: Customer
okf_x_range: Subscription
okf_x_cardinality: ONE_TO_MANY
okf_x_inverse: held by
---

# Reading it

* Customer holds Subscription
* Reverse: Subscription held by Customer

# Between

* Domain: [Customer](/concepts/Customer.md)
* Range: [Subscription](/concepts/Subscription.md)
