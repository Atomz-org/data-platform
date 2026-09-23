---
type: Relation
title: order_settled_by_payment
description: Order settled by Payment
okf_x_tier: platform
okf_x_domain: Order
okf_x_range: Payment
okf_x_cardinality: ONE_TO_MANY
okf_x_inverse: settles
---

# Reading it

* Order settled by Payment
* Reverse: Payment settles Order

# Between

* Domain: [Order](/concepts/Order.md)
* Range: [Payment](/concepts/Payment.md)
