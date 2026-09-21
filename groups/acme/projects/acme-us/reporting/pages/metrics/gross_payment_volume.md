---
title: Gross Payment Volume
queries:
  - metrics/gross_payment_volume.sql
---

All payment attempts regardless of outcome, **unfiltered** — every row in the underlying fact counts, measured over `paid_at` from `fct_payments`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(gross_payment_volume) as gross_payment_volume
from ${metrics_gross_payment_volume} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=gross_payment_volume yFmt=usd0/>

## By payment status

```sql by_dim
select payment_status, sum(gross_payment_volume) as gross_payment_volume
from ${metrics_gross_payment_volume} where payment_status is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=payment_status y=gross_payment_volume swapXY=true xFmt=usd0/>

