---
title: Cheapest Landed Total (component)
queries:
  - metrics/cheapest_usd_total.sql
---

Building block for avg_spread_to_cheapest_ratio, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_market_spreads_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(cheapest_usd_total) as cheapest_usd_total
from ${metrics_cheapest_usd_total} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=cheapest_usd_total yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(cheapest_usd_total) as cheapest_usd_total
from ${metrics_cheapest_usd_total} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=cheapest_usd_total swapXY=true xFmt=num0/>

