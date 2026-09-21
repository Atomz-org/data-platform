---
type: Table
title: raw_inventory_counts
description: Induced from raw_inventory_counts by `pf semantic scan`.
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
| `location_id` | ? | foreign_key |
| `counted_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:InventoryCount`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
