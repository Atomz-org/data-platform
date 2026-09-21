---
type: Table
title: raw_delivery_shipments
description: Induced from raw_delivery_shipments by `pf semantic scan`.
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
| `purchase_order_id` | ? | foreign_key |
| `supplier_id` | ? | foreign_key |
| `destination_id` | ? | foreign_key |
| `shipped_at` | ? | event_time |
| `estimated_arrival_at` | ? | event_time |
| `actual_arrival_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:DeliveryShipment`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
