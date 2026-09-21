---
title: Days With a Comparable Landed Price
queries:
  - metrics/landed_usd_days.sql
---

Days a market landed a commodity, restated in USD per quote unit, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_prices_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(landed_usd_days) as landed_usd_days
from ${metrics_landed_usd_days} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=landed_usd_days yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(landed_usd_days) as landed_usd_days
from ${metrics_landed_usd_days} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=landed_usd_days swapXY=true xFmt=num0/>

