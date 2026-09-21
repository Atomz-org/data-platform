---
title: Order Total
queries:
  - metrics/order_total.sql
---

Sum of total order amonunt. Includes tax + revenue, **unfiltered** — every row in the underlying fact counts, measured over `ordered_at` from `orders`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(order_total) as order_total
from ${metrics_order_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=order_total yFmt=num0/>

## By order total dim

```sql by_dim
select order_total_dim, sum(order_total) as order_total
from ${metrics_order_total} where order_total_dim is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=order_total_dim y=order_total swapXY=true xFmt=num0/>

