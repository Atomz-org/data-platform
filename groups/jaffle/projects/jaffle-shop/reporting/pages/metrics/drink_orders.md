---
title: Drink Orders
queries:
  - metrics/drink_orders.sql
---

Count of orders that contain drink order items, **restricted to `is_drink_order = true`**, measured over `ordered_at` from `orders`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(drink_orders) as drink_orders
from ${metrics_drink_orders} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=drink_orders yFmt=num0/>

## By order total dim

```sql by_dim
select order_total_dim, sum(drink_orders) as drink_orders
from ${metrics_drink_orders} where order_total_dim is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=order_total_dim y=drink_orders swapXY=true xFmt=num0/>

