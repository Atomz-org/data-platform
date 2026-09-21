---
title: Days Compared
queries:
  - metrics/spread_days.sql
---

Days at least two markets priced the commodity, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_market_spreads_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(spread_days) as spread_days
from ${metrics_spread_days} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=spread_days yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(spread_days) as spread_days
from ${metrics_spread_days} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=spread_days swapXY=true xFmt=num0/>

