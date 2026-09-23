---
type: Concept
title: PoLineItem
description: Induced from `raw_po_line_items` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `line_total` | integer | [money_amount](/roles/money_amount.md) |
| `product_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `purchase_order_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `unit_cost` | integer | [money_amount](/roles/money_amount.md) |
