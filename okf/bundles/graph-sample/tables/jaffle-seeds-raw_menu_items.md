---
type: Table
title: raw_menu_items
description: Induced from raw_menu_items by `pf semantic scan`.
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
| `product_id` | ? | foreign_key |
| `category_id` | ? | foreign_key |
| `price` | ? | money_amount |

# Provenance

Instantiates ontology concept `concept:MenuItem`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
