---
type: Table
title: raw_po_line_items
description: Induced from raw_po_line_items by `pf semantic scan`.
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
| `purchase_order_id` | ? | foreign_key |
| `product_id` | ? | foreign_key |
| `unit_cost` | ? | money_amount |
| `line_total` | ? | money_amount |

# Provenance

Instantiates ontology concept `concept:PoLineItem`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
