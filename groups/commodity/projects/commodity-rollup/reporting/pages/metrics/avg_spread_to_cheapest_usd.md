---
title: Avg Spread to Cheapest Market (USD)
queries:
  - metrics/avg_spread_to_cheapest_usd.sql
---

Mean USD per quote unit a market pays over the cheapest market that day. Group by commodity and market, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_market_spreads_daily`, and carried as `spread_usd_total` / `spread_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(spread_usd_total) / sum(spread_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(spread_usd_total) as spread_usd_total, sum(spread_days) as spread_days, sum(spread_usd_total) / nullif(sum(spread_days), 0) as avg_spread_to_cheapest_usd
from ${metrics_avg_spread_to_cheapest_usd} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_spread_to_cheapest_usd yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(spread_usd_total) / nullif(sum(spread_days), 0) as avg_spread_to_cheapest_usd
from ${metrics_avg_spread_to_cheapest_usd} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_spread_to_cheapest_usd swapXY=true xFmt=num0/>

