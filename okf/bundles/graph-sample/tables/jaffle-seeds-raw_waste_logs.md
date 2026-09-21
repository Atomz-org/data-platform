---
type: Table
title: raw_waste_logs
description: Induced from raw_waste_logs by `pf semantic scan`.
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
| `cost_of_waste` | ? | money_amount |
| `wasted_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:WasteLog`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
