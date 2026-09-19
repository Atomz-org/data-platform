---
title: Days With a Landed Price
queries:
  - metrics/landed_price_days.sql
---

Days a landed price exists — never for commodities India prohibits importing, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_india_landed_prices_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(landed_price_days) as landed_price_days
from ${metrics_landed_price_days} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=landed_price_days yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(landed_price_days) as landed_price_days
from ${metrics_landed_price_days} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=landed_price_days swapXY=true xFmt=num0/>

