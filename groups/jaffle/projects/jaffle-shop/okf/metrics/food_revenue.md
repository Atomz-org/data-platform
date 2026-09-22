---
type: Metric
title: Food Revenue
description: The revenue from food in each order
okf_x_kind: simple
okf_x_model: order_items
okf_x_time_column: ordered_at
okf_x_kg_node: metric:food_revenue
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(case when is_food_item then product_price else 0 end)`
* **Built on:** [order_items](/tables/order_items.md)
* **Dimensions:** `is_food_item`, `is_drink_item`
