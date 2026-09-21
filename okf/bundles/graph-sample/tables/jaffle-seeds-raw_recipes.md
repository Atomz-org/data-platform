---
type: Table
title: raw_recipes
description: Induced from raw_recipes by `pf semantic scan`.
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
| `menu_item_id` | ? | foreign_key |
| `created_at` | ? | event_time |
| `updated_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Recipe`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
