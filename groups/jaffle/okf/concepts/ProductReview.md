---
type: Concept
title: ProductReview
description: Induced from `raw_product_reviews` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `customer_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `order_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `product_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `reviewed_at` | timestamp | [event_time](/roles/event_time.md) |
