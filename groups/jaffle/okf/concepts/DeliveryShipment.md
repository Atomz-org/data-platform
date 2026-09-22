---
type: Concept
title: DeliveryShipment
description: Induced from `raw_delivery_shipments` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `actual_arrival_at` | timestamp | [event_time](/roles/event_time.md) |
| `destination_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `estimated_arrival_at` | timestamp | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `purchase_order_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `shipped_at` | timestamp | [event_time](/roles/event_time.md) |
| `supplier_id` | integer | [foreign_key](/roles/foreign_key.md) |
