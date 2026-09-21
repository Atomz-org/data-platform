---
type: Table
title: raw_refunds
description: Induced from raw_refunds by `pf semantic scan`.
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
| `invoice_id` | ? | foreign_key |
| `refund_amount` | ? | money_amount |
| `requested_at` | ? | event_time |
| `resolved_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Refund`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
