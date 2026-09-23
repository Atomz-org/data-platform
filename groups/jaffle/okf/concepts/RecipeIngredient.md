---
type: Concept
title: RecipeIngredient
description: Induced from `raw_recipe_ingredients` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `ingredient_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `recipe_id` | integer | [foreign_key](/roles/foreign_key.md) |
