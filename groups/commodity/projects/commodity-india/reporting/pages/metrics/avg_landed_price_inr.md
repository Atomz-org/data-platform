---
title: Avg India Landed Price (INR)
queries:
  - metrics/avg_landed_price_inr.sql
---

Mean India import landed price, ₹ per Indian market unit (benchmark × USD/INR × (1 + duty)). Group by commodity; filter landed_price__is_duty_rate_confirmed to exclude history priced at a back-applied duty rate, **unfiltered** — every row in the underlying fact counts, measured over `price_date` from `fct_india_landed_prices_daily`, and carried as `landed_price_inr_total` / `landed_price_days` so it re-divides correctly at any grain. Defined once in the dbt semantic layer and compiled to `queries/metrics/` — this page does not restate it.

> **Ratio metric.** Aggregated as `sum(landed_price_inr_total) / sum(landed_price_days)` at whatever grain you group by. Averaging the ratio itself gives a different — and wrong — answer.

```sql series
select metric_time, sum(landed_price_inr_total) as landed_price_inr_total, sum(landed_price_days) as landed_price_days, sum(landed_price_inr_total) / nullif(sum(landed_price_days), 0) as avg_landed_price_inr
from ${metrics_avg_landed_price_inr} group by 1 order by 1
```

<LineChart data={series} x=metric_time y=avg_landed_price_inr yFmt=num0/>

## By commodity id

```sql by_dim
select commodity_id, sum(landed_price_inr_total) / nullif(sum(landed_price_days), 0) as avg_landed_price_inr
from ${metrics_avg_landed_price_inr} where commodity_id is not null group by 1 order by 2 desc
```

<BarChart data={by_dim} x=commodity_id y=avg_landed_price_inr swapXY=true xFmt=num0/>

