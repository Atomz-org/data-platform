---
type: Concept
title: IngredientPrice
description: Induced from `raw_ingredient_prices` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `effective_from` | date | [event_time](/roles/event_time.md) |
| `effective_to` | date | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `ingredient_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `supplier_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `unit_cost` | integer | [money_amount](/roles/money_amount.md) |
