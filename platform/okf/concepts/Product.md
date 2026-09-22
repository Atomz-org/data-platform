---
type: Concept
title: Product
description: A sellable thing. Plans and SKUs are Products.
okf_x_tier: platform
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: product_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `name` | string | [free_text](/roles/free_text.md) |
| `product_id` | string | [natural_key](/roles/natural_key.md) |

# Relations

* [order_contains_product](/relations/order_contains_product.md) — Order contains Product
* [subscription_for_product](/relations/subscription_for_product.md) — Subscription for product Product
