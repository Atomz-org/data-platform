---
type: Table
title: raw_nutritional_info
description: Induced from raw_nutritional_info by `pf semantic scan`.
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
| `total_fat_g` | ? | money_amount |
| `total_carbs_g` | ? | money_amount |
| `total_sugars_g` | ? | money_amount |
| `updated_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:NutritionalInfo`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
