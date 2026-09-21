---
type: Table
title: raw_loyalty_members
description: Induced from raw_loyalty_members by `pf semantic scan`.
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
| `customer_id` | ? | foreign_key |
| `tier_id` | ? | foreign_key |
| `enrolled_at` | ? | event_time |
| `last_activity_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:LoyaltyMember`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
