---
type: Concept
title: MenuItem
description: Induced from `raw_menu_items` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `category_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `price` | integer | [money_amount](/roles/money_amount.md) |
| `product_id` | integer | [foreign_key](/roles/foreign_key.md) |
