---
title: Large Orders
queries:
  - metrics/large_orders.sql
---

Count of orders with order total over 20, **restricted to `order_total_dim >= 20`**, measured over `ordered_at` from `orders`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(large_orders) as large_orders
from ${metrics_large_orders} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=large_orders yFmt=num0/>

## By order total dim

```sql by_dim
select order_total_dim, sum(large_orders) as large_orders
from ${metrics_large_orders} where order_total_dim is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=order_total_dim y=large_orders swapXY=true xFmt=num0/>

