---
type: Table
title: raw_purchase_orders
description: Induced from raw_purchase_orders by `pf semantic scan`.
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
| `supplier_id` | ? | foreign_key |
| `warehouse_id` | ? | foreign_key |
| `total_amount` | ? | money_amount |
| `ordered_at` | ? | event_time |
| `expected_delivery_at` | ? | event_time |
| `created_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:PurchaseOrder`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
