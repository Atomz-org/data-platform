---
title: Avg Landed Price (USD per quote unit)
queries:
  - metrics/avg_landed_price_usd.sql
---

Mean landed price on the benchmark's footing. Group by commodity and market; this is the number that compares, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_prices_daily`, and carried as `landed_usd_total` / `landed_usd_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(landed_usd_total) / sum(landed_usd_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(landed_usd_total) as landed_usd_total, sum(landed_usd_days) as landed_usd_days, sum(landed_usd_total) / nullif(sum(landed_usd_days), 0) as avg_landed_price_usd
from ${metrics_avg_landed_price_usd} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_landed_price_usd yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(landed_usd_total) / nullif(sum(landed_usd_days), 0) as avg_landed_price_usd
from ${metrics_avg_landed_price_usd} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_landed_price_usd swapXY=true xFmt=num0/>

