---
type: Table
title: raw_equipment
description: Induced from raw_equipment by `pf semantic scan`.
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
| `store_id` | ? | foreign_key |
| `purchase_cost` | ? | money_amount |
| `purchase_date` | ? | event_time |
| `warranty_expiry` | ? | event_time |
| `last_maintenance_date` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Equipment`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
