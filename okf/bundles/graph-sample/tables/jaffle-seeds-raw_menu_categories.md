---
type: Table
title: raw_menu_categories
description: Induced from raw_menu_categories by `pf semantic scan`.
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
| `parent_category_id` | ? | foreign_key |

# Provenance

Instantiates ontology concept `concept:MenuCategory`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
