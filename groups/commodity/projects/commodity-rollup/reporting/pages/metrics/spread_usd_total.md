---
title: Spread Total (component)
queries:
  - metrics/spread_usd_total.sql
---

Building block for avg_spread_to_cheapest_usd, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_market_spreads_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(spread_usd_total) as spread_usd_total
from ${metrics_spread_usd_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=spread_usd_total yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(spread_usd_total) as spread_usd_total
from ${metrics_spread_usd_total} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=spread_usd_total swapXY=true xFmt=num0/>

