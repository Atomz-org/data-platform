---
type: Concept
title: SupplierContract
description: Induced from `raw_supplier_contracts` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `created_at` | timestamp | [event_time](/roles/event_time.md) |
| `effective_date` | date | [event_time](/roles/event_time.md) |
| `expiration_date` | date | [event_time](/roles/event_time.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `minimum_order_amount` | integer | [money_amount](/roles/money_amount.md) |
| `supplier_id` | integer | [foreign_key](/roles/foreign_key.md) |
