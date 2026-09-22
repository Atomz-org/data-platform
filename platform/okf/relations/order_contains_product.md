---
type: Relation
title: order_contains_product
description: Needs a line-item bridge in any physical model.
okf_x_tier: platform
okf_x_domain: Order
okf_x_range: Product
okf_x_cardinality: MANY_TO_MANY
okf_x_inverse: appears in
---

# Reading it

* Order contains Product
* Reverse: Product appears in Order

# Between

* Domain: [Order](/concepts/Order.md)
* Range: [Product](/concepts/Product.md)
