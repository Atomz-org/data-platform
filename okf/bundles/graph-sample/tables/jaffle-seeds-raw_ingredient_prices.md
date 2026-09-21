---
type: Table
title: raw_ingredient_prices
description: Induced from raw_ingredient_prices by `pf semantic scan`.
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
| `ingredient_id` | ? | foreign_key |
| `supplier_id` | ? | foreign_key |
| `unit_cost` | ? | money_amount |
| `effective_from` | ? | event_time |
| `effective_to` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:IngredientPrice`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
