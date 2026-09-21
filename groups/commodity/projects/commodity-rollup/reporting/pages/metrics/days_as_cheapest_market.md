---
title: Days as Cheapest Market
queries:
  - metrics/days_as_cheapest_market.sql
---

Days a market was the cheapest place to land a commodity. Group by commodity and market, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_market_spreads_daily`. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

```sql series
select metric_time, sum(days_as_cheapest_market) as days_as_cheapest_market
from ${metrics_days_as_cheapest_market} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=days_as_cheapest_market yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(days_as_cheapest_market) as days_as_cheapest_market
from ${metrics_days_as_cheapest_market} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=days_as_cheapest_market swapXY=true xFmt=num0/>

