---
type: Table
title: raw_invoices
description: Induced from raw_invoices by `pf semantic scan`.
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
| `order_id` | ? | foreign_key |
| `customer_id` | ? | foreign_key |
| `subtotal` | ? | money_amount |
| `tax_amount` | ? | money_amount |
| `total_amount` | ? | money_amount |
| `amount_paid` | ? | money_amount |
| `amount_due` | ? | money_amount |
| `issued_at` | ? | event_time |
| `due_at` | ? | event_time |
| `paid_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Invoice`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
