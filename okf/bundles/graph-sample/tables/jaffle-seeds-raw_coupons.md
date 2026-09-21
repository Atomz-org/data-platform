---
type: Table
title: raw_coupons
description: Induced from raw_coupons by `pf semantic scan`.
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
| `campaign_id` | ? | foreign_key |
| `discount_amount` | ? | money_amount |
| `minimum_order_amount` | ? | money_amount |
| `valid_from` | ? | event_time |
| `valid_until` | ? | event_time |
| `created_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Coupon`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
