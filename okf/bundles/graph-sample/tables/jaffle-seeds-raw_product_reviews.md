---
type: Table
title: raw_product_reviews
description: Induced from raw_product_reviews by `pf semantic scan`.
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
| `customer_id` | ? | foreign_key |
| `order_id` | ? | foreign_key |
| `reviewed_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:ProductReview`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
