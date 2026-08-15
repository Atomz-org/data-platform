---
title: Order Cost
queries:
  - metrics/order_cost.sql
---

Sum of cost for each order item, **unfiltered** — every row in the underlying fact counts, measured over `ordered_at` from `orders`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(order_cost) as order_cost
from ${metrics_order_cost} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=order_cost yFmt=num0/>

## By order total dim

```sql by_dim
select order_total_dim, sum(order_cost) as order_cost
from ${metrics_order_cost} where order_total_dim is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=order_total_dim y=order_cost swapXY=true xFmt=num0/>

