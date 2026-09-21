---
type: Table
title: raw_budgets
description: Induced from raw_budgets by `pf semantic scan`.
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
| `budgeted_amount` | ? | money_amount |
| `month_start` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Budget`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
