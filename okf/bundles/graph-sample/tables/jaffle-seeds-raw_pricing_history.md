---
type: Table
title: raw_pricing_history
description: Induced from raw_pricing_history by `pf semantic scan`.
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
| `old_price` | ? | money_amount |
| `new_price` | ? | money_amount |
| `changed_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:PricingHistory`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
