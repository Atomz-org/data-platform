---
type: Metric
title: Food Revenue %
description: The % of order revenue from food.
okf_x_kind: ratio
okf_x_model: order_items
okf_x_time_column: ordered_at
okf_x_kg_node: metric:food_revenue_pct
---

# Definition

* **Kind:** `ratio`
* **Expression:** `sum(case when is_food_item then product_price else 0 end) / nullif(sum(product_price), 0)`
* **Ratio:** `food_revenue` / `revenue` — re-divide at the reading grain, never average the ratio
* **Built on:** [order_items](/tables/order_items.md)
* **Dimensions:** `is_food_item`, `is_drink_item`
