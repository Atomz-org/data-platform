---
title: Average Order Value
queries:
  - metrics/aov.sql
---

Revenue divided by succeeded payment count, **restricted to `payment_status = 'succeeded'`**, measured over `paid_at` from `fct_payments`, and carried as `revenue` / `payment_count` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(revenue) / sum(payment_count)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(revenue) as revenue, sum(payment_count) as payment_count, sum(revenue) / nullif(sum(payment_count), 0) as aov
from ${metrics_aov} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=aov yFmt=usd0/>

## By payment status

```sql by_dim
select payment_status, sum(revenue) / nullif(sum(payment_count), 0) as aov
from ${metrics_aov} where payment_status is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=payment_status y=aov swapXY=true xFmt=usd0/>

