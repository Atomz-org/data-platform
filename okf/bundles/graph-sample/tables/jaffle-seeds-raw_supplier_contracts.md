---
type: Table
title: raw_supplier_contracts
description: Induced from raw_supplier_contracts by `pf semantic scan`.
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
| `minimum_order_amount` | ? | money_amount |
| `effective_date` | ? | event_time |
| `expiration_date` | ? | event_time |
| `created_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:SupplierContract`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
