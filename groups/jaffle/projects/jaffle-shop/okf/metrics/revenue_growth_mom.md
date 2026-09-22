---
type: Metric
title: Revenue Growth % M/M
description: Percentage growth of revenue compared to 1 month ago. Excluded tax
okf_x_kind: derived
okf_x_model: order_items
okf_x_time_column: ordered_at
okf_x_kg_node: metric:revenue_growth_mom
---

# Definition

* **Kind:** `derived`
* **Expression:** derived
* **Built on:** [order_items](/tables/order_items.md)
* **Dimensions:** `is_drink_item`, `is_food_item`
* **Built from:** [revenue](/metrics/revenue.md)
