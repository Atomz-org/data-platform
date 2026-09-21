---
type: Table
title: raw_expenses
description: Induced from raw_expenses by `pf semantic scan`.
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
| `category_id` | ? | foreign_key |
| `amount` | ? | money_amount |
| `incurred_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Expense`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
