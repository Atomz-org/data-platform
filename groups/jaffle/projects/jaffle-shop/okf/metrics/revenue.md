---
type: Metric
title: Revenue
description: Sum of the product revenue for each order item. Excludes tax.
okf_x_kind: simple
okf_x_model: order_items
okf_x_time_column: ordered_at
okf_x_kg_node: metric:revenue
---

# Definition

* **Kind:** `simple`
* **Expression:** `sum(product_price)`
* **Built on:** [order_items](/tables/order_items.md)
* **Dimensions:** `is_food_item`, `is_drink_item`
