---
title: Average Order Value
queries:
  - metrics/average_order_value.sql
---

LTV pre-tax / number of orders, **unfiltered** — every row in the underlying fact counts, measured over `first_ordered_at` from `customers`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(average_order_value) as average_order_value
from ${metrics_average_order_value} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=average_order_value yFmt=usd0/>

## By customer name

```sql by_dim
select customer_name, sum(average_order_value) as average_order_value
from ${metrics_average_order_value} where customer_name is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=customer_name y=average_order_value swapXY=true xFmt=usd0/>

