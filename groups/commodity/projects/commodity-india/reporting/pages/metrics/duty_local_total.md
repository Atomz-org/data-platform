---
title: Customs Duty Total (component)
queries:
  - metrics/duty_local_total.sql
---

Building block for avg_duty_local. A sum of per-unit duties means nothing on its own, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_prices_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(duty_local_total) as duty_local_total
from ${metrics_duty_local_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=duty_local_total yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(duty_local_total) as duty_local_total
from ${metrics_duty_local_total} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=duty_local_total swapXY=true xFmt=num0/>

