---
type: Metric
title: Drink Revenue %
description: The % of order revenue from drinks.
okf_x_kind: ratio
okf_x_model: order_items
okf_x_time_column: ordered_at
okf_x_kg_node: metric:drink_revenue_pct
---

# Definition

* **Kind:** `ratio`
* **Expression:** derived
* **Ratio:** `drink_revenue` / `revenue` — re-divide at the reading grain, never average the ratio
* **Built on:** [order_items](/tables/order_items.md)
* **Dimensions:** `is_drink_item`, `is_food_item`
* **Built from:** [drink_revenue](/metrics/drink_revenue.md), [revenue](/metrics/revenue.md)
