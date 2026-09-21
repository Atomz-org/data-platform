---
type: Table
title: raw_recipe_ingredients
description: Induced from raw_recipe_ingredients by `pf semantic scan`.
tags:
- jaffle-shop
- raw
- graph-sample
status: stable
---

# Schema

| Column | Type | Role |
|---|---|---|
| `id` | ? | natural_key |
| `recipe_id` | ? | foreign_key |
| `ingredient_id` | ? | foreign_key |

# Provenance

Instantiates ontology concept `concept:RecipeIngredient`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
