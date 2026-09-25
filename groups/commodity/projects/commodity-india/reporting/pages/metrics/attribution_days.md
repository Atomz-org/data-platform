---
title: Attribution Days
queries:
  - metrics/attribution_days.sql
---

The `attribution_days` metric, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_price_attribution_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(attribution_days) as attribution_days
from ${metrics_attribution_days} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=attribution_days yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(attribution_days) as attribution_days
from ${metrics_attribution_days} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=attribution_days swapXY=true xFmt=num0/>

