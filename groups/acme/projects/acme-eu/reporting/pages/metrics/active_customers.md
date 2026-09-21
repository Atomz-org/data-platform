---
title: Active Customers
queries:
  - metrics/active_customers.sql
---

Customers with at least one active subscription, **unfiltered** — every row in the underlying fact counts, measured over `created_at` from `dim_customers`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(active_customers) as active_customers
from ${metrics_active_customers} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=active_customers yFmt=num0/>

## By customer segment

```sql by_dim
select customer_segment, sum(active_customers) as active_customers
from ${metrics_active_customers} where customer_segment is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=customer_segment y=active_customers swapXY=true xFmt=num0/>

