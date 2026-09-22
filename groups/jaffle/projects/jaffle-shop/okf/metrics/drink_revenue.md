---
type: Metric
title: Drink Revenue
description: The revenue from drinks in each order
okf_x_kind: simple
okf_x_model: order_items
okf_x_time_column: ordered_at
okf_x_kg_node: metric:drink_revenue
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(case when is_drink_item then product_price else 0 end)`
* **Built on:** [order_items](/tables/order_items.md)
* **Dimensions:** `is_food_item`, `is_drink_item`
* **Derived from it:** [drink_revenue_pct](/metrics/drink_revenue_pct.md)
