---
type: Concept
title: Product
description: A sellable thing. Plans and SKUs are Products.
okf_x_defined_in: platform
okf_x_parent: null
okf_x_identity: product_id
okf_x_kg_node: concept:Product
okf_x_platform_concept: ../../../../../../platform/okf/concepts/Product.md
---

Defined by the platform ontology: [Product](../../../../../../platform/okf/concepts/Product.md).

# Instantiated by

* [products](/tables/products.md)
* [rpt_stock_alerts](/tables/rpt_stock_alerts.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `name` | string | free_text |
| `price` | integer | money_amount |
| `product_id` | string | natural_key |
| `sku` | string | natural_key |

# Relations

* Order contains Product — Needs a line-item bridge in any physical model.
* Subscription for product Product — 

# Raw tables that instantiate it

* `jaffle-seeds.raw_products`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
