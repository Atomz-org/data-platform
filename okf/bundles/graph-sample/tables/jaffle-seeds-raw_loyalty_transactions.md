---
type: Table
title: raw_loyalty_transactions
description: Induced from raw_loyalty_transactions by `pf semantic scan`.
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
| `loyalty_member_id` | ? | foreign_key |
| `order_id` | ? | foreign_key |
| `transacted_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:LoyaltyTransaction`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
