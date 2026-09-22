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
* **Dimensions:** `is_drink_item`, `is_food_item`
* **Derived from it:** [drink_revenue_pct](/metrics/drink_revenue_pct.md), [food_revenue_pct](/metrics/food_revenue_pct.md), [order_gross_profit](/metrics/order_gross_profit.md), [revenue_growth_mom](/metrics/revenue_growth_mom.md)
