---
type: Table
title: raw_inventory_movements
description: Induced from raw_inventory_movements by `pf semantic scan`.
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
| `reference_id` | ? | foreign_key |
| `moved_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:InventoryMovement`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
