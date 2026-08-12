---
title: Revenue
queries:
  - metrics/revenue.sql
---

Net revenue — succeeded payments only. The single definition, **restricted to `payment_status = 'succeeded'`**, measured over `paid_at` from `fct_payments`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(revenue) as revenue
from ${metrics_revenue} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=revenue yFmt=usd0/>

## By payment status

```sql by_dim
select payment_status, sum(revenue) as revenue
from ${metrics_revenue} where payment_status is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=payment_status y=revenue swapXY=true xFmt=usd0/>

