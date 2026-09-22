---
type: Concept
title: PurchaseOrder
description: Induced from `raw_purchase_orders` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `created_at` | timestamp | [event_time](/roles/event_time.md) |
| `expected_delivery_at` | timestamp | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `ordered_at` | timestamp | [event_time](/roles/event_time.md) |
| `supplier_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `total_amount` | integer | [money_amount](/roles/money_amount.md) |
| `warehouse_id` | integer | [foreign_key](/roles/foreign_key.md) |
