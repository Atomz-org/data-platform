---
type: Table
title: raw_payment_transactions
description: Induced from raw_payment_transactions by `pf semantic scan`.
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
| `gift_card_id` | ? | foreign_key |
| `amount` | ? | money_amount |
| `processed_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:PaymentTransaction`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
