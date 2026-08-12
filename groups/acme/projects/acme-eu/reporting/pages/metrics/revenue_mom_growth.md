---
title: Revenue MoM Growth
queries:
  - metrics/revenue_mom_growth.sql
---

Month-over-month change in net revenue, **restricted to `payment_status = 'succeeded'`**, measured over `paid_at` from `fct_payments`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(revenue_mom_growth) as revenue_mom_growth
from ${metrics_revenue_mom_growth} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=revenue_mom_growth yFmt=usd0/>

## By payment status

```sql by_dim
select payment_status, sum(revenue_mom_growth) as revenue_mom_growth
from ${metrics_revenue_mom_growth} where payment_status is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=payment_status y=revenue_mom_growth swapXY=true xFmt=usd0/>

