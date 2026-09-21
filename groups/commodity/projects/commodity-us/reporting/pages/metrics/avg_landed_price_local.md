---
title: Avg Landed Price (market currency)
queries:
  - metrics/avg_landed_price_local.sql
---

Mean import landed price in this market's currency per its market unit (benchmark × USD/local × (1 + duty)). Group by commodity; filter landed_price__is_duty_rate_confirmed to exclude history priced at a back-applied duty rate, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_landed_prices_daily`, and carried as `landed_price_local_total` / `landed_price_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(landed_price_local_total) / sum(landed_price_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(landed_price_local_total) as landed_price_local_total, sum(landed_price_days) as landed_price_days, sum(landed_price_local_total) / nullif(sum(landed_price_days), 0) as avg_landed_price_local
from ${metrics_avg_landed_price_local} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_landed_price_local yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(landed_price_local_total) / nullif(sum(landed_price_days), 0) as avg_landed_price_local
from ${metrics_avg_landed_price_local} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_landed_price_local swapXY=true xFmt=num0/>

