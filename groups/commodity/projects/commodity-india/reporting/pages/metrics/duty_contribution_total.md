---
title: Duty Contribution (component)
queries:
  - metrics/duty_contribution_total.sql
---

The `duty_contribution_total` metric, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_price_attribution_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(duty_contribution_total) as duty_contribution_total
from ${metrics_duty_contribution_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=duty_contribution_total yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(duty_contribution_total) as duty_contribution_total
from ${metrics_duty_contribution_total} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=duty_contribution_total swapXY=true xFmt=num0/>

