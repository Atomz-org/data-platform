---
type: Table
title: raw_coupon_redemptions
description: Induced from raw_coupon_redemptions by `pf semantic scan`.
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
| `coupon_id` | ? | foreign_key |
| `order_id` | ? | foreign_key |
| `customer_id` | ? | foreign_key |
| `redeemed_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:CouponRedemption`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
