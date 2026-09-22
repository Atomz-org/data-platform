---
type: Concept
title: Product
description: A sellable thing. Plans and SKUs are Products.
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

* Order contains Product — Needs a line-item bridge in any physical model.
* Subscription for product Product — 
