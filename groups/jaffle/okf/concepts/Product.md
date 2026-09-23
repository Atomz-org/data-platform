---
type: Concept
title: Product
description: A sellable thing. Plans and SKUs are Products.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: product_id
okf_x_platform_concept: ../../../../platform/okf/concepts/Product.md
---

Extends the platform's [Product](../../../../platform/okf/concepts/Product.md); this page is what this family added.

# Properties

| Property | Datatype | Role |
|---|---|---|
| `name` | string | [free_text](/roles/free_text.md) |
| `price` | integer | [money_amount](/roles/money_amount.md) |
| `product_id` | string | [natural_key](/roles/natural_key.md) |
| `sku` | string | [natural_key](/roles/natural_key.md) |

# Relations

* [order_contains_product](/relations/order_contains_product.md) — Order contains Product
* [subscription_for_product](/relations/subscription_for_product.md) — Subscription for product Product
