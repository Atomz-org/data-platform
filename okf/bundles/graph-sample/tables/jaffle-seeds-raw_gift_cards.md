---
type: Table
title: raw_gift_cards
description: Induced from raw_gift_cards by `pf semantic scan`.
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
| `initial_balance` | ? | money_amount |
| `current_balance` | ? | money_amount |
| `issued_at` | ? | event_time |
| `expires_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:GiftCard`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
