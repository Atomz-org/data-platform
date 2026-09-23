---
type: Concept
title: PoReceipt
description: Induced from `raw_po_receipts` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `po_line_item_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `purchase_order_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `received_at` | timestamp | [event_time](/roles/event_time.md) |
