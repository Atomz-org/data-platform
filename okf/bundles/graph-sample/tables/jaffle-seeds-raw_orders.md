---
type: Table
title: raw_orders
description: Induced from raw_orders by `pf semantic scan`.
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
| `ordered_at` | ? | event_time |
| `store_id` | ? | foreign_key |
| `subtotal` | ? | money_amount |
| `order_total` | ? | money_amount |

# Provenance

Instantiates ontology concept `concept:Order`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
