---
title: Avg Spread to Cheapest Market (ratio)
queries:
  - metrics/avg_spread_to_cheapest_ratio.sql
---

Mean spread as a share of the cheapest landed price, re-divided at query grain. Group by commodity and market, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_market_spreads_daily`, and carried as `spread_usd_total` / `cheapest_usd_total` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(spread_usd_total) / sum(cheapest_usd_total)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(spread_usd_total) as spread_usd_total, sum(cheapest_usd_total) as cheapest_usd_total, sum(spread_usd_total) / nullif(sum(cheapest_usd_total), 0) as avg_spread_to_cheapest_ratio
from ${metrics_avg_spread_to_cheapest_ratio} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_spread_to_cheapest_ratio yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(spread_usd_total) / nullif(sum(cheapest_usd_total), 0) as avg_spread_to_cheapest_ratio
from ${metrics_avg_spread_to_cheapest_ratio} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_spread_to_cheapest_ratio swapXY=true xFmt=num0/>

