---
type: Table
title: raw_po_receipts
description: Induced from raw_po_receipts by `pf semantic scan`.
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
| `po_line_item_id` | ? | foreign_key |
| `received_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:PoReceipt`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
