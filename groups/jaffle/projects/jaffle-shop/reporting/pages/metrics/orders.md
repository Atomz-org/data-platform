---
title: Orders
queries:
  - metrics/orders.sql
---

Count of orders, **unfiltered** — every row in the underlying fact counts, measured over `ordered_at` from `orders`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(orders) as orders
from ${metrics_orders} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=orders yFmt=num0/>

## By order total dim

```sql by_dim
select order_total_dim, sum(orders) as orders
from ${metrics_orders} where order_total_dim is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=order_total_dim y=orders swapXY=true xFmt=num0/>

