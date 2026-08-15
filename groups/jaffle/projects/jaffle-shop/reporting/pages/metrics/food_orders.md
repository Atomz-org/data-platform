---
title: Food Orders
queries:
  - metrics/food_orders.sql
---

Count of orders that contain food order items, **restricted to `is_food_order = true`**, measured over `ordered_at` from `orders`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(food_orders) as food_orders
from ${metrics_food_orders} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=food_orders yFmt=num0/>

## By order total dim

```sql by_dim
select order_total_dim, sum(food_orders) as food_orders
from ${metrics_food_orders} where order_total_dim is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=order_total_dim y=food_orders swapXY=true xFmt=num0/>

