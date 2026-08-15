---
title: Count Lifetime Orders
queries:
  - metrics/count_lifetime_orders.sql
---

Count of lifetime orders, **unfiltered** — every row in the underlying fact counts, measured over `first_ordered_at` from `customers`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(count_lifetime_orders) as count_lifetime_orders
from ${metrics_count_lifetime_orders} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=count_lifetime_orders yFmt=num0/>

## By customer name

```sql by_dim
select customer_name, sum(count_lifetime_orders) as count_lifetime_orders
from ${metrics_count_lifetime_orders} where customer_name is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=customer_name y=count_lifetime_orders swapXY=true xFmt=num0/>

